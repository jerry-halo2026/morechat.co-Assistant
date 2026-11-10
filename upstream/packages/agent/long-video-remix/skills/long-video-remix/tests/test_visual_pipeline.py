"""Production gates, motion end states and an optional actual Blender/FFmpeg run."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / 'scripts'))
import visual_pipeline as vp
from _composition_smoke import build
from _synthetic_project import install_test_catalog
import workflow_control as wc
from blender_composite_worker import sample, world_pose
from compile_render_manifest import compile_manifest
from render_blender_composition import render
from finish_ffmpeg import finish
from prepare_execution_authorization import prepare
from validate_project import validate
from execution_integrity import project_inputs_digest


class MotionContractTests(unittest.TestCase):
    def test_curve_starts_ends_and_holds_without_reset(self):
        keys = [{'frame': 0, 'values': {'scale': 1}},
                {'frame': 20, 'values': {'scale': 1.1}, 'easing': 'smoothstep'}]
        values = [sample({}, keys, frame)['scale'] for frame in range(50)]
        self.assertEqual(values[0], 1)
        self.assertAlmostEqual(values[20], 1.1)
        self.assertTrue(all(a <= b for a, b in zip(values, values[1:])))
        self.assertTrue(all(value == 1.1 for value in values[20:]))
        self.assertLess(values[20] - values[19], values[11] - values[10])

    def test_parent_group_keeps_relative_layout(self):
        groups = {'common': {'transform': {'x': 10, 'scale': 2, 'rotation': 90}}}
        pose = world_pose({'parent': 'common', 'transform': {'x': 20, 'scale': .5}}, groups, 5)
        self.assertAlmostEqual(pose['x'], 10)
        self.assertAlmostEqual(pose['y'], 40)
        self.assertAlmostEqual(pose['scale'], 1)

    def test_invalid_easing_nonfinite_and_duplicate_keys_rejected(self):
        for keys in [[{'frame': 1, 'values': {}, 'easing': 'invented'}],
                     [{'frame': 0, 'values': {'scale': float('nan')}}],
                     [{'frame': 1, 'values': {}}, {'frame': 1, 'values': {}}]]:
            with self.assertRaises(ValueError):
                sample({}, keys, 0)

    def test_cyclic_or_missing_parent_rejected(self):
        for groups in [{}, {'A': {'parent': 'B'}, 'B': {'parent': 'A'}}]:
            with self.assertRaises(ValueError):
                world_pose({'parent': 'A'}, groups, 0)


@unittest.skipUnless(importlib.util.find_spec('PIL') is not None, 'Synthetic graphics generator requires Pillow')
class ProductionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'project'
        self.addCleanup(self.temp.cleanup)
        self.test_package = Path(self.temp.name) / 'package'
        install_test_catalog(self, self.test_package)
        build(self.root)
        self.quote = 'SIMULATED FIXTURE DECISION: approve the displayed test version only.'
        (self.root / 'test-decisions.md').write_text('# Simulated test decisions\n\n' + self.quote + '\n')

    def project(self):
        return vp.read(self.root / 'project.json')

    def approve(self, keys):
        shown = []
        for key in keys:
            for ref in wc.required_shown_refs(self.root, self.project(), key):
                if ref not in shown:
                    shown.append(ref)
        return wc.confirm(self.root, keys, 'test_fixture_user', 'test-decisions.md', self.quote, shown)

    def approve_preparation(self):
        self.approve(('direction', 'audio', 'mockup', 'method'))

    def test_new_template_and_fixture_have_no_automatic_confirmations(self):
        self.assertEqual(self.project()['schema_version'], '1.9')
        self.assertEqual(self.project()['workflow_control']['confirmations'], {})
        methods = vp.read(self.root / 'visual-methods.json')['methods']
        self.assertEqual(methods[0]['method_id'], 'PM001')
        self.assertEqual(methods[0]['library_refs'], ['M13'])
        self.assertEqual(methods[0]['fallback_refs'], ['F09'])
        self.assertEqual(vp.read(self.root / 'composition-plan.json')['compositions'][0]['method_ids'], ['PM001'])
        self.assertFalse(wc.report(self.root, 'build_composition')['action_allowed'])
        self.assertFalse(wc.report(self.root, 'render')['action_allowed'])

    def test_v2_proof_is_proof_only_and_budgeted(self):
        plan = vp.read(self.root / 'composition-plan.json')
        plan['proof_scope_policy'] = 'representative_risk_based_v2'
        plan['compositions'][0]['delivery_role'] = 'proof_only'
        vp.write(self.root / 'composition-plan.json', plan)
        with self.assertRaisesRegex(ValueError, '3-second budget'):
            vp.composition_plan(self.root, self.project())
        plan['compositions'][0]['full_length_proof_exception'] = {
            'kind': 'full_length_required_for_unmodeled_dynamic_risk',
            'reason': 'Synthetic test: exercise an internal join that spans the existing fixture.'
        }
        vp.write(self.root / 'composition-plan.json', plan)
        self.assertEqual(vp.composition_plan(self.root, self.project())['compositions'][0]['delivery_role'], 'proof_only')

    def test_proof_waiver_is_explicit_and_not_fake_confirmation(self):
        result = wc.waive_proof(self.root, 'test_fixture_user', 'test-decisions.md', self.quote,
                                'User explicitly requested direct production without representative Proof.')
        project = self.project()
        self.assertEqual(project['visual_gate_status'], 'proof_waived')
        self.assertNotIn('proof', project['workflow_control']['confirmations'])
        self.assertEqual(project['workflow_control']['proof_waiver']['scope'], 'skip_proof_generation_and_review')
        self.assertEqual(next(row for row in result['gates'] if row['id'] == 'proof')['status'], 'satisfied')

    def test_method_is_required_at_the_actual_build_entry(self):
        self.approve(('direction', 'audio', 'mockup'))
        with self.assertRaisesRegex(ValueError, 'method'):
            render(self.root, 'C01', blender='nonexistent-test-blender')
        self.assertFalse((self.root / 'compositions').exists())

    def test_incomplete_method_cannot_be_confirmed(self):
        data = vp.read(self.root / 'visual-methods.json')
        del data['methods'][0]['selection_reason']
        vp.write(self.root / 'visual-methods.json', data)
        with self.assertRaises(ValueError):
            self.approve(('method',))

    def test_visual_library_refs_are_optional_metadata_without_new_gate(self):
        data = vp.read(self.root / 'visual-methods.json')
        method = data['methods'][0]
        method['visual_problem'] = 'Keep the reaction readable while strengthening the visual emphasis.'
        method['library_refs'] = ['M01', 'M13']
        method['fallback_refs'] = ['F09']
        method['candidate_treatments'] = [
            {'candidate_id': 'A', 'treatment': 'subtle push-in', 'tradeoff': 'keeps both reactions'},
            {'candidate_id': 'B', 'treatment': 'static hold', 'tradeoff': 'safer but less emphasis'},
        ]
        vp.write(self.root / 'visual-methods.json', data)
        self.approve_preparation()
        self.assertEqual(wc.evaluate(self.root)['method']['status'], 'satisfied')
        self.assertNotIn('visual_methods', wc.evaluate(self.root))

    def test_method_change_invalidates_confirmation(self):
        self.approve_preparation()
        data = vp.read(self.root / 'visual-methods.json')
        data['methods'][0]['parameters']['scale_end'] = 1.5
        vp.write(self.root / 'visual-methods.json', data)
        self.assertEqual(wc.evaluate(self.root)['method']['status'], 'stale')
        self.assertFalse(wc.report(self.root, 'build_composition')['action_allowed'])

    def test_reference_routing_is_required_before_mockup(self):
        self.approve(('direction',))
        data = vp.read(self.root / 'visual-methods.json')
        data['methods'][0]['visual_reference_status'] = 'pending'
        data['methods'][0]['visual_reference_refs'] = []
        data['methods'][0]['viewed_reference_assets'] = []
        vp.write(self.root / 'visual-methods.json', data)
        result = wc.report(self.root, 'make_mockup')
        self.assertFalse(result['action_allowed'])
        self.assertIn('reference_routing', [row['id'] for row in result['pending_gates']])

    def test_reference_routing_binds_the_actual_bundled_asset_hash(self):
        data = vp.read(self.root / 'visual-methods.json')
        data['methods'][0]['viewed_reference_assets'][0]['sha256'] = '0' * 64
        vp.write(self.root / 'visual-methods.json', data)
        with self.assertRaisesRegex(ValueError, 'sha256'):
            vp.reference_routing_inputs(self.root, self.project())

    def test_viewed_reference_without_implementation_trace_cannot_pass_method_gate(self):
        lock = vp.read(self.root / 'implementation-lock.json')
        lock['reference_trace'] = []
        vp.write(self.root / 'implementation-lock.json', lock)
        with self.assertRaisesRegex(ValueError, 'Every selected Visual Reference'):
            self.approve(('method',))

    def test_reference_trace_must_reach_real_implementation_parameters(self):
        lock = vp.read(self.root / 'implementation-lock.json')
        lock['reference_trace'][0]['parameter_paths'] = ['elements.PANEL_PUSH.parameters.DOES_NOT_EXIST']
        vp.write(self.root / 'implementation-lock.json', lock)
        with self.assertRaisesRegex(ValueError, 'parameter path is missing'):
            self.approve(('method',))

    def test_composition_cannot_switch_renderer_away_from_implementation_lock(self):
        plan = vp.read(self.root / 'composition-plan.json')
        plan['compositions'][0]['mode'] = 'native_blend'
        plan['compositions'][0]['native_scene_ref'] = 'media/a.png'
        plan['compositions'][0].pop('layers', None)
        vp.write(self.root / 'composition-plan.json', plan)
        with self.assertRaisesRegex(ValueError, 'cannot replace an Implementation Lock renderer'):
            vp.composition_plan(self.root, self.project())

    def test_runtime_text_policy_blocks_undersized_creator_text(self):
        timeline = vp.read(self.root / 'timeline.json')
        timeline['text_tracks'] = [{
            'text_id': 'TXT-RUNTIME', 'kind': 'explanation', 'text_role': 'creator_text',
            'text': 'Synthetic creator text', 'anchor_event_id': 'E001',
            'local_in_frame': 0, 'local_out_frame': 100,
            'stable_hold_frames': 100, 'fade_in_frames': 0, 'fade_out_frames': 0,
            'glyph_height_px': 5, 'canvas_height_px': 180
        }]
        vp.write(self.root / 'timeline.json', timeline)
        errors = validate(self.root, render_checks=False)['errors']
        self.assertTrue(any('glyph height ratio' in row for row in errors), errors)

    def test_runtime_voiceover_policy_forbids_undeclared_voiceover(self):
        timeline = vp.read(self.root / 'timeline.json')
        timeline['audio_tracks'].append({
            'track_id': 'VO-RUNTIME', 'kind': 'voiceover', 'asset_ref': 'media/audio.wav',
            'anchor_event_id': 'E001', 'local_in_frame': 0, 'local_out_frame': 100,
            'gain_db': 0, 'fade_in_ms': 0, 'fade_out_ms': 0,
            'narrative_role': 'other', 'treatment_reason': 'synthetic runtime policy test'
        })
        vp.write(self.root / 'timeline.json', timeline)
        errors = validate(self.root, render_checks=False)['errors']
        self.assertTrue(any('voiceover is forbidden' in row for row in errors), errors)

    def _add_covered_production_composition(self):
        plan = vp.read(self.root / 'composition-plan.json')
        proof = plan['compositions'][0]
        covered = copy.deepcopy(proof)
        covered['composition_id'] = 'C02'
        covered['proof_covered_by'] = vp.proof_composition_ids(plan)[0]
        covered['proof_coverage_reason'] = 'Same locked Blender implementation; production-only window.'
        covered.pop('preview_audio_ref', None)
        covered.pop('silent_demo', None)
        covered.pop('silent_reason', None)
        for key in ('scene_ref', 'video_ref', 'receipt_ref', 'readback_ref'):
            covered[key] = proof[key].replace('C01', 'C02')
        # Non-proof production windows do not need pre-Execute demo/proof/review paths.
        for key in ('demo_ref', 'proof_ref', 'review_ref'):
            covered.pop(key, None)
        plan['compositions'].append(covered)
        vp.write(self.root / 'composition-plan.json', plan)
        return covered

    def _write_simulated_composition_artifacts(self):
        plan = vp.read(self.root / 'composition-plan.json')
        job = plan['compositions'][0]
        for key in ('scene_ref', 'video_ref', 'demo_ref', 'proof_ref', 'readback_ref'):
            path = vp.path_at(self.root, job[key])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(('synthetic-' + key).encode())
        receipt = {
            'schema_version': '1.0', 'status': 'rendered_not_reviewed', 'backend': 'blender',
            'backend_version': 'synthetic-test', 'project_id': self.project()['project_id'],
            'composition_id': job['composition_id'],
            'input_digest': vp.digest(vp.job_input(self.root, self.project(), plan, job)),
            'artifacts': [vp.binding(self.root, job[key]) for key in ('scene_ref','video_ref','demo_ref','proof_ref','readback_ref')],
            'technical': {'frames': job['frame_count'], 'full_decode': 'pass'}
        }
        vp.write(vp.path_at(self.root, job['receipt_ref']), receipt)
        review = {
            'composition_id': job['composition_id'],
            'demo_sha256': vp.binding(self.root, job['demo_ref'])['sha256'],
            'engineering_sha256': vp.binding(self.root, job['scene_ref'])['sha256'],
            'render_input_digest': receipt['input_digest'], 'reviewer': 'synthetic_fixture_reviewer',
            'playback_verified': True, 'blocking_issues': [],
            'checks': []
        }
        selected_refs = sorted({rid for method in vp.methods(self.root, self.project())['methods']
                                if method.get('visual_reference_status') == 'used'
                                for rid in method.get('visual_reference_refs', [])})
        for name in vp.REVIEW_CHECKS:
            row = {'name': name, 'status': 'pass', 'method': 'synthetic gate test',
                   'evidence': [job['demo_ref']], 'finding': 'synthetic gate record'}
            if name == 'ReferenceCompliance':
                row.update(
                    evidence=[self.project()['visual_mockup_ref'], job['proof_ref'],
                              self.project()['visual_pipeline']['implementation_lock_ref']],
                    reference_ref_ids=selected_refs,
                    implementation_lock_sha256=vp.binding(
                        self.root, self.project()['visual_pipeline']['implementation_lock_ref'])['sha256'],
                    mockup_sha256=vp.binding(self.root, self.project()['visual_mockup_ref'])['sha256'],
                    proof_sha256=vp.binding(self.root, job['proof_ref'])['sha256'])
            review['checks'].append(row)
        vp.write(vp.path_at(self.root, job['review_ref']), review)
        return job

    def test_pre_execute_composition_gate_only_requires_representative_proof(self):
        covered = self._add_covered_production_composition()
        self._write_simulated_composition_artifacts()
        project = self.project()
        project['visual_proof_ref'] = 'compositions/C01/v1-proof.png'
        vp.write(self.root / 'project.json', project)
        inputs = vp.composition_inputs(self.root, self.project())
        self.assertEqual(inputs['proof_composition_ids'], ['C01'])
        self.assertFalse(vp.path_at(self.root, covered['video_ref']).exists())
        shown = wc.required_shown_refs(self.root, self.project(), 'composition')
        self.assertEqual(shown, ['compositions/C01/v1-proof.png', 'compositions/C01/v1-demo.mp4'])
        # Production Lock binds the full plan but does not require C02 to be pre-rendered.
        self.assertIn('composition', vp.production_lock_inputs(self.root, self.project()))

    def test_production_only_receipt_does_not_require_demo_or_review(self):
        covered = self._add_covered_production_composition()
        plan = vp.composition_plan(self.root, self.project())
        for key in ('scene_ref', 'video_ref', 'readback_ref'):
            path = vp.path_at(self.root, covered[key])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(('synthetic-production-' + key).encode())
        receipt = {
            'schema_version': '1.0', 'status': 'rendered_not_reviewed', 'backend': 'blender',
            'purpose': 'production', 'backend_version': 'synthetic-test',
            'project_id': self.project()['project_id'], 'composition_id': covered['composition_id'],
            'input_digest': vp.digest(vp.job_input(self.root, self.project(), plan, covered)),
            'artifacts': [vp.binding(self.root, covered[key]) for key in ('scene_ref', 'video_ref', 'readback_ref')],
            'technical': {'frames': covered['frame_count'], 'full_decode': 'pass'}
        }
        vp.write(vp.path_at(self.root, covered['receipt_ref']), receipt)
        actual = vp.validate_job_receipt(self.root, self.project(), plan, covered)
        self.assertEqual(actual['purpose'], 'production')
        self.assertFalse((self.root / 'compositions/C02/v1-demo.mp4').exists())

    def test_nonproof_composition_cannot_be_rendered_as_pre_execute_proof(self):
        self._add_covered_production_composition()
        self.approve_preparation()
        with self.assertRaisesRegex(ValueError, 'Only proof_composition_ids'):
            render(self.root, 'C02', blender='nonexistent-test-blender', purpose='proof')

    def test_nonproof_default_render_is_deferred_until_execute_authorization(self):
        self._add_covered_production_composition()
        self.approve_preparation()
        with self.assertRaisesRegex(ValueError, 'Workflow gate blocks render'):
            render(self.root, 'C02', blender='nonexistent-test-blender')

    def test_pre_render_digest_excludes_deferred_production_outputs(self):
        covered = self._add_covered_production_composition()
        refs = set(vp.tracked_refs(self.root, self.project()))
        for key in ('scene_ref', 'video_ref', 'receipt_ref', 'readback_ref'):
            self.assertNotIn(covered[key], refs)
        self.assertIn('media/a.png', refs)

    def test_project_inputs_digest_is_stable_when_deferred_outputs_appear(self):
        covered = self._add_covered_production_composition()
        before = project_inputs_digest(self.root)
        for key in ('scene_ref', 'video_ref', 'receipt_ref', 'readback_ref'):
            path = vp.path_at(self.root, covered[key])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(('deferred-generated-' + key).encode())
        after = project_inputs_digest(self.root)
        self.assertEqual(before, after)

    def test_nonproof_coverage_requires_explicit_reason_even_without_policy(self):
        covered = self._add_covered_production_composition()
        plan = vp.read(self.root / 'composition-plan.json')
        plan.pop('proof_scope_policy', None)
        plan['compositions'][1].pop('proof_coverage_reason', None)
        vp.write(self.root / 'composition-plan.json', plan)
        with self.assertRaisesRegex(ValueError, 'proof_coverage_reason'):
            vp.composition_plan(self.root, self.project())

    def test_nonproof_cannot_claim_coverage_for_new_lock_element(self):
        self._add_covered_production_composition()
        lock = vp.read(self.root / 'implementation-lock.json')
        lock['elements']['NEW_EFFECT'] = {
            'role': 'Synthetic distinct implementation risk', 'renderer': 'blender_layers',
            'implementation_method': 'distinct_effect', 'event_ids': ['E001'],
            'parameters': {'amount': 1}}
        vp.write(self.root / 'implementation-lock.json', lock)
        plan = vp.read(self.root / 'composition-plan.json')
        plan['compositions'][1]['implementation_element_ids'].append('NEW_EFFECT')
        vp.write(self.root / 'composition-plan.json', plan)
        with self.assertRaisesRegex(ValueError, 'Implementation Lock elements not covered'):
            vp.composition_plan(self.root, self.project())

    def test_nonproof_cannot_claim_coverage_for_new_method(self):
        self._add_covered_production_composition()
        methods = vp.read(self.root / 'visual-methods.json')
        second = copy.deepcopy(methods['methods'][0])
        second['method_id'] = 'PM002'
        second['selection_reason'] = 'Synthetic distinct method for coverage validation.'
        methods['methods'].append(second)
        vp.write(self.root / 'visual-methods.json', methods)
        lock = vp.read(self.root / 'implementation-lock.json')
        trace = copy.deepcopy(lock['reference_trace'][0])
        trace['method_id'] = 'PM002'
        lock['reference_trace'].append(trace)
        vp.write(self.root / 'implementation-lock.json', lock)
        plan = vp.read(self.root / 'composition-plan.json')
        plan['compositions'][1]['method_ids'].append('PM002')
        vp.write(self.root / 'composition-plan.json', plan)
        with self.assertRaisesRegex(ValueError, 'methods not covered by its Proof'):
            vp.composition_plan(self.root, self.project())

    def test_nonproof_join_requires_a_join_exercising_proof(self):
        self._add_covered_production_composition()
        plan = vp.read(self.root / 'composition-plan.json')
        proof = plan['compositions'][0]
        proof['joins'] = []
        proof['no_join_reason'] = 'Synthetic proof deliberately has no join for coverage test.'
        vp.write(self.root / 'composition-plan.json', plan)
        with self.assertRaisesRegex(ValueError, 'join not exercised by its Proof'):
            vp.composition_plan(self.root, self.project())

    def test_redundant_representative_proof_is_blocked(self):
        plan = vp.read(self.root / 'composition-plan.json')
        first = plan['compositions'][0]
        second = copy.deepcopy(first)
        second['composition_id'] = 'C02'
        for key in ('scene_ref', 'video_ref', 'demo_ref', 'proof_ref', 'receipt_ref', 'readback_ref', 'review_ref'):
            second[key] = first[key].replace('C01', 'C02')
        plan['proof_composition_ids'] = ['C01', 'C02']
        plan['compositions'].append(second)
        vp.write(self.root / 'composition-plan.json', plan)
        with self.assertRaisesRegex(ValueError, 'Redundant Proof is blocked'):
            vp.composition_plan(self.root, self.project())

    def test_redundant_narrow_proof_before_broader_proof_is_blocked(self):
        plan = vp.read(self.root / 'composition-plan.json')
        broader = plan['compositions'][0]
        narrow = copy.deepcopy(broader)
        narrow['composition_id'] = 'C02'
        narrow['implementation_element_ids'] = broader['implementation_element_ids'][:-1]
        for key in ('scene_ref', 'video_ref', 'demo_ref', 'proof_ref', 'receipt_ref', 'readback_ref', 'review_ref'):
            narrow[key] = broader[key].replace('C01', 'C02')
        plan['proof_composition_ids'] = ['C02', 'C01']
        plan['compositions'].append(narrow)
        vp.write(self.root / 'composition-plan.json', plan)
        with self.assertRaisesRegex(ValueError, 'Redundant Proof is blocked'):
            vp.composition_plan(self.root, self.project())

    def test_redundant_proof_material_exception_is_explicit_and_shown(self):
        evidence_ref = 'proof-exceptions/C02-material-risk.md'
        evidence = self.root / evidence_ref
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text('Synthetic evidence: C02 has a material-specific occlusion risk not represented in plan metadata.\n')
        plan = vp.read(self.root / 'composition-plan.json')
        first = plan['compositions'][0]
        second = copy.deepcopy(first)
        second['composition_id'] = 'C02'
        second['additional_proof_exception'] = {
            'kind': 'material_specific_unmodeled_risk',
            'reason': 'Material-specific occlusion risk requires a second reviewed Proof.',
            'evidence_refs': [evidence_ref]}
        for key in ('scene_ref', 'video_ref', 'demo_ref', 'proof_ref', 'receipt_ref', 'readback_ref', 'review_ref'):
            second[key] = first[key].replace('C01', 'C02')
        plan['proof_composition_ids'] = ['C01', 'C02']
        plan['compositions'].append(second)
        vp.write(self.root / 'composition-plan.json', plan)
        parsed = vp.composition_plan(self.root, self.project())
        self.assertEqual(vp.proof_composition_ids(parsed), ['C01', 'C02'])
        shown = vp.proof_display_refs(self.root, {**self.project(),
            'visual_proof_ref': first['proof_ref'], 'visual_proof_refs': [first['proof_ref'], second['proof_ref']]})
        self.assertIn(evidence_ref, shown)

    def test_multiple_representative_proofs_are_supported_when_risks_are_distinct(self):
        lock = vp.read(self.root / 'implementation-lock.json')
        lock['elements']['SECOND_PROOF_EFFECT'] = {
            'role': 'Synthetic distinct implementation risk for second Proof',
            'renderer': 'blender_layers', 'implementation_method': 'distinct_effect',
            'event_ids': ['E001'], 'parameters': {'amount': 1}}
        vp.write(self.root / 'implementation-lock.json', lock)
        plan = vp.read(self.root / 'composition-plan.json')
        first = plan['compositions'][0]
        second = copy.deepcopy(first)
        second['composition_id'] = 'C02'
        # Make the two Proofs genuinely incomparable: C01 covers PANEL_PUSH + PANEL_CUT,
        # while C02 covers PANEL_CUT + SECOND_PROOF_EFFECT. Neither mechanically covers the other.
        second['implementation_element_ids'] = [first['implementation_element_ids'][-1], 'SECOND_PROOF_EFFECT']
        for key in ('scene_ref', 'video_ref', 'demo_ref', 'proof_ref', 'receipt_ref', 'readback_ref', 'review_ref'):
            second[key] = first[key].replace('C01', 'C02')
        plan['proof_composition_ids'] = ['C01', 'C02']
        plan['compositions'].append(second)
        vp.write(self.root / 'composition-plan.json', plan)
        for job in (first, second):
            for key in ('scene_ref', 'video_ref', 'demo_ref', 'proof_ref', 'readback_ref'):
                path = vp.path_at(self.root, job[key])
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((job['composition_id'] + '-' + key).encode())
            current_plan = vp.composition_plan(self.root, self.project())
            current_job = next(row for row in current_plan['compositions'] if row['composition_id'] == job['composition_id'])
            receipt = {
                'schema_version': '1.0', 'status': 'rendered_not_reviewed', 'backend': 'blender',
                'purpose': 'proof', 'backend_version': 'synthetic-test',
                'project_id': self.project()['project_id'], 'composition_id': job['composition_id'],
                'input_digest': vp.digest(vp.job_input(self.root, self.project(), current_plan, current_job)),
                'artifacts': [vp.binding(self.root, current_job[key]) for key in ('scene_ref','video_ref','demo_ref','proof_ref','readback_ref')],
                'technical': {'frames': current_job['frame_count'], 'full_decode': 'pass'}
            }
            vp.write(vp.path_at(self.root, current_job['receipt_ref']), receipt)
            review = {
                'composition_id': job['composition_id'],
                'demo_sha256': vp.binding(self.root, current_job['demo_ref'])['sha256'],
                'engineering_sha256': vp.binding(self.root, current_job['scene_ref'])['sha256'],
                'render_input_digest': receipt['input_digest'], 'reviewer': 'synthetic_fixture_reviewer',
                'playback_verified': True, 'blocking_issues': [], 'checks': []}
            selected_refs = sorted({rid for method in vp.methods(self.root, self.project())['methods']
                                    if method.get('visual_reference_status') == 'used'
                                    for rid in method.get('visual_reference_refs', [])})
            for name in vp.REVIEW_CHECKS:
                row = {'name': name, 'status': 'pass', 'method': 'synthetic multi-proof gate test',
                       'evidence': [current_job['demo_ref']], 'finding': 'synthetic gate record'}
                if name == 'ReferenceCompliance':
                    row.update(evidence=[self.project()['visual_mockup_ref'], current_job['proof_ref'],
                                         self.project()['visual_pipeline']['implementation_lock_ref']],
                               reference_ref_ids=selected_refs,
                               implementation_lock_sha256=vp.binding(self.root, self.project()['visual_pipeline']['implementation_lock_ref'])['sha256'],
                               mockup_sha256=vp.binding(self.root, self.project()['visual_mockup_ref'])['sha256'],
                               proof_sha256=vp.binding(self.root, current_job['proof_ref'])['sha256'])
                review['checks'].append(row)
            vp.write(vp.path_at(self.root, current_job['review_ref']), review)
        project = self.project()
        project['visual_proof_ref'] = first['proof_ref']
        project['visual_proof_refs'] = [first['proof_ref'], second['proof_ref']]
        vp.write(self.root / 'project.json', project)
        inputs = vp.composition_inputs(self.root, self.project())
        self.assertEqual(inputs['proof_composition_ids'], ['C01', 'C02'])
        self.assertEqual(len(inputs['proof_receipts']), 2)
        self.assertEqual(inputs['additional_proof_exceptions'], [])
        self.assertEqual(wc.required_shown_refs(self.root, self.project(), 'composition'),
                         [first['proof_ref'], first['demo_ref'], second['proof_ref'], second['demo_ref']])

    def test_final_composition_qa_requires_per_window_conclusion_and_join_finding(self):
        self._add_covered_production_composition()
        render_dir = self.root / 'render'
        render_dir.mkdir(exist_ok=True)
        refs = []
        rows = []
        for index, cid in enumerate(('C01', 'C02')):
            ref = 'render/' + cid + '.mp4'
            (self.root / ref).write_bytes(('video-' + cid).encode())
            token = vp.binding(self.root, ref)
            refs.append(ref)
            rows.append({'composition_id': cid, 'start_frame': index * 50, 'end_frame': (index + 1) * 50,
                         'video': token})
        vp.write(self.root / 'render-manifest.json', {'compositions': rows})
        expected = [{'composition_id': row['composition_id'], 'start_frame': row['start_frame'],
                     'end_frame': row['end_frame'], 'video_sha256': row['video']['sha256'],
                     'status': 'pass', 'finding': 'Window playback checked against the production render.',
                     'join_finding': 'Declared internal join was watched continuously and is acceptable.'}
                    for row in rows]
        checks = [{'name': 'CompositionCompliance', 'status': 'pass',
                   'evidence': ['render-manifest.json'] + refs, 'composition_windows': expected}]
        vp.validate_final_composition_qa(self.root, self.project(), checks)
        missing = copy.deepcopy(checks)
        missing[0]['composition_windows'][1].pop('finding')
        with self.assertRaisesRegex(ValueError, 'C02: final composition window requires a nonblank finding'):
            vp.validate_final_composition_qa(self.root, self.project(), missing)
        bad_join = copy.deepcopy(checks)
        bad_join[0]['composition_windows'][0].pop('join_finding')
        with self.assertRaisesRegex(ValueError, 'C01: join-containing composition requires a nonblank join_finding'):
            vp.validate_final_composition_qa(self.root, self.project(), bad_join)
        wrong_window = copy.deepcopy(checks)
        wrong_window[0]['composition_windows'][0]['start_frame'] = 99
        with self.assertRaisesRegex(ValueError, 'match render-manifest IDs'):
            vp.validate_final_composition_qa(self.root, self.project(), wrong_window)

    def test_qa_gate_surfaces_specific_composition_validator_error(self):
        plan = vp.composition_plan(self.root, self.project())
        job = plan['compositions'][0]
        proof_path = vp.path_at(self.root, job['proof_ref'])
        proof_path.parent.mkdir(parents=True, exist_ok=True)
        proof_path.write_bytes(b'SYNTHETIC-PROOF-FOR-QA-GATE')
        project = self.project()
        project['visual_proof_ref'] = job['proof_ref']
        vp.write(self.root / 'project.json', project)
        video_ref = 'render/C01.mp4'
        video_path = self.root / video_ref
        video_path.parent.mkdir(parents=True, exist_ok=True)
        video_path.write_bytes(b'SYNTHETIC-PRODUCTION-WINDOW')
        video = vp.binding(self.root, video_ref)
        vp.write(self.root / 'render-manifest.json', {'compositions': [{
            'composition_id': 'C01', 'start_frame': 0, 'end_frame': 125, 'video': video}]})
        check_names = sorted(wc.QA_NAMES | set(vp.FINAL_CHECKS))
        checks = [{'name': name, 'status': 'pass', 'method': 'synthetic QA gate error propagation test',
                   'evidence': [video_ref], 'finding': 'Synthetic check record.'} for name in check_names]
        selected_refs = sorted({rid for method in vp.methods(self.root, self.project())['methods']
                                if method.get('visual_reference_status') == 'used'
                                for rid in method.get('visual_reference_refs', [])})
        lock_ref = self.project()['visual_pipeline']['implementation_lock_ref']
        for check in checks:
            if check['name'] == 'ReferenceCompliance':
                check.update(evidence=[self.project()['visual_mockup_ref'], job['proof_ref'], lock_ref],
                             reference_ref_ids=selected_refs,
                             implementation_lock_sha256=vp.binding(self.root, lock_ref)['sha256'],
                             mockup_sha256=vp.binding(self.root, self.project()['visual_mockup_ref'])['sha256'],
                             proof_sha256=vp.binding(self.root, job['proof_ref'])['sha256'])
            elif check['name'] == 'CompositionCompliance':
                check.update(evidence=['render-manifest.json', video_ref], composition_windows=[{
                    'composition_id': 'C01', 'start_frame': 99, 'end_frame': 125,
                    'video_sha256': video['sha256'], 'status': 'pass',
                    'finding': 'Synthetic window check.', 'join_finding': 'Synthetic join check.'}])
        vp.write(self.root / 'qa.json', {'project_id': self.project()['project_id'],
            'artifact_sha256': '0' * 64, 'final_playback_verified': True, 'blocking_issues': [], 'checks': checks})
        qa_gate = wc.evaluate(self.root)['qa']
        self.assertEqual(qa_gate['status'], 'pending')
        self.assertIn('match render-manifest IDs', qa_gate['reason'])

    def test_native_blend_coverage_requires_same_source_scene_and_dependencies(self):
        (self.root / 'native-a.blend').write_bytes(b'NATIVE-A')
        (self.root / 'native-b.blend').write_bytes(b'NATIVE-B')
        lock = vp.read(self.root / 'implementation-lock.json')
        for element in lock['elements'].values():
            element['renderer'] = 'blender_native_blend'
        vp.write(self.root / 'implementation-lock.json', lock)
        plan = vp.read(self.root / 'composition-plan.json')
        proof = plan['compositions'][0]
        proof['mode'] = 'native_blend'
        proof['native_scene_ref'] = 'native-a.blend'
        proof['native_dependency_refs'] = ['media/a.png', 'media/b.png']
        proof.pop('layers', None)
        proof.pop('groups', None)
        covered = copy.deepcopy(proof)
        covered['composition_id'] = 'C02'
        covered['native_scene_ref'] = 'native-b.blend'
        covered['proof_covered_by'] = 'C01'
        covered['proof_coverage_reason'] = 'Claims same native implementation but points at another .blend.'
        for key in ('scene_ref', 'video_ref', 'receipt_ref', 'readback_ref'):
            covered[key] = proof[key].replace('C01', 'C02')
        for key in ('demo_ref', 'proof_ref', 'review_ref', 'preview_audio_ref', 'silent_demo', 'silent_reason'):
            covered.pop(key, None)
        plan['compositions'].append(covered)
        vp.write(self.root / 'composition-plan.json', plan)
        with self.assertRaisesRegex(ValueError, 'different native_scene_ref or native_dependency_refs'):
            vp.composition_plan(self.root, self.project())

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),
                         'FFmpeg/ffprobe required for fake-Blender production render test')
    def test_authorized_nonproof_production_render_uses_no_demo_or_review(self):
        covered = self._add_covered_production_composition()
        self.approve_preparation()
        proof_job = self._write_simulated_composition_artifacts()
        project = self.project()
        project['visual_proof_ref'] = proof_job['proof_ref']
        if proof_job['proof_ref'] not in project['execution_reference_asset_refs']:
            project['execution_reference_asset_refs'].append(proof_job['proof_ref'])
        vp.write(self.root / 'project.json', project)
        caps = vp.read(self.root / 'capability-map.json')
        caps['capabilities'].append({
            'capability': 'compose_layers', 'composition_id': 'C01', 'status': 'available',
            'actual_tool': 'synthetic-test', 'entrypoint': 'synthetic-test-proof',
            'output_mapping': {'proof': proof_job['proof_ref']}, 'limits': {'synthetic_only': True}})
        vp.write(self.root / 'capability-map.json', caps)
        self.approve(('proof', 'composition', 'plan'))
        authorization = prepare(self.root)
        authorization.update(status='confirmed', authorization_id='SIMULATED-PRODUCTION-AUTH',
                             confirmed_by='simulated_fixture_user')
        vp.write(self.root / 'execution-authorization.json', authorization)
        from execution_integrity import digest
        project = self.project()
        project['execution_authorization_digest'] = digest(authorization)
        project['render_authorized'] = True
        vp.write(self.root / 'project.json', project)
        timeline = vp.read(self.root / 'timeline.json')
        timeline['status'] = 'ready_for_render'
        vp.write(self.root / 'timeline.json', timeline)
        self.assertTrue(wc.report(self.root, 'render')['action_allowed'])

        fake = self.root / 'fake_blender.py'
        fake.write_text("""#!/usr/bin/env python3
import json, sys
from pathlib import Path
from PIL import Image
job_path = Path(sys.argv[-1])
payload = json.loads(job_path.read_text())
frames = Path(payload['frames_directory'])
frames.mkdir(parents=True, exist_ok=True)
first = 1
width = payload['output']['width']; height = payload['output']['height']
for index in range(payload['job']['frame_count']):
    Image.new('RGB', (width, height), (40, 50, 60)).save(frames / ('frame_%06d.png' % (first + index)))
Path(payload['scene_output']).write_bytes(b'FAKE-BLENDER-SCENE')
Path(payload['readback_output']).write_text(json.dumps({'backend_version':'fake-blender-1.0','first_native_frame':first}))
""")
        fake.chmod(0o755)
        receipt = render(self.root, covered['composition_id'], blender=str(fake), purpose='production')
        self.assertEqual(receipt['purpose'], 'production')
        self.assertEqual(receipt['composition_id'], 'C02')
        for key in ('scene_ref', 'video_ref', 'readback_ref', 'receipt_ref'):
            self.assertTrue(vp.path_at(self.root, covered[key]).is_file(), key)
        self.assertNotIn('demo_ref', covered)
        self.assertNotIn('proof_ref', covered)
        self.assertNotIn('review_ref', covered)
        self.assertTrue(wc.report(self.root, 'render')['action_allowed'])

    def test_production_lock_digest_changes_when_text_policy_changes(self):
        self._write_simulated_composition_artifacts()
        first = vp.digest(vp.production_lock_inputs(self.root, self.project()))
        project = self.project()
        project['text_policy']['min_glyph_height_ratio']['creator_text'] = 0.06
        vp.write(self.root / 'project.json', project)
        second = vp.digest(vp.production_lock_inputs(self.root, self.project()))
        self.assertNotEqual(first, second)

    def test_invented_source_evidence_cannot_pass_method_gate(self):
        data = vp.read(self.root / 'visual-methods.json')
        data['methods'][0]['source_evidence_refs'] = ['INVENTED-EVIDENCE']
        vp.write(self.root / 'visual-methods.json', data)
        with self.assertRaisesRegex(ValueError, 'unknown source evidence'):
            self.approve(('method',))

    def test_invalid_delivery_spec_is_rejected_before_formal_compile(self):
        data = vp.read(self.root / 'delivery-spec.json')
        for changes in ({'crf': 99}, {'output_ref': 'render/final.mov'}, {'output_ref': 'render/clean-video.mp4'}):
            invalid = dict(data, **changes)
            vp.write(self.root / 'delivery-spec.json', invalid)
            with self.assertRaises(ValueError):
                vp.delivery_spec(self.root, self.project())

    def test_engineering_file_without_motion_receipt_and_review_is_blocked(self):
        self.approve_preparation()
        job = vp.read(self.root / 'composition-plan.json')['compositions'][0]
        target = vp.path_at(self.root, job['scene_ref'])
        target.parent.mkdir(parents=True)
        target.write_bytes(b'not-a-real-engineering-file')
        with self.assertRaises(ValueError):
            self.approve(('composition',))
        with self.assertRaises(ValueError):
            prepare(self.root)
        self.assertFalse(wc.report(self.root, 'execute_handoff')['action_allowed'])

    def test_deleting_new_policy_does_not_downgrade_schema_19(self):
        project = self.project()
        del project['visual_pipeline']
        vp.write(self.root / 'project.json', project)
        self.assertTrue(any('visual_pipeline' in row for row in validate(self.root, render_checks=False)['errors']))
        with self.assertRaises(ValueError):
            wc.require_action(self.root, 'build_composition')

    def test_deleting_workflow_control_does_not_waive_pipeline(self):
        project = self.project()
        del project['workflow_control']
        del project['execution_policy']['workflow_gate_control']
        vp.write(self.root / 'project.json', project)
        self.assertTrue(validate(self.root, render_checks=False)['errors'])

    def test_join_must_include_both_sides_and_outgoing_incoming_states(self):
        data = vp.read(self.root / 'composition-plan.json')
        data['compositions'][0]['joins'][0]['after_frames'] = 1000
        vp.write(self.root / 'composition-plan.json', data)
        with self.assertRaisesRegex(ValueError, 'both sides'):
            vp.composition_plan(self.root, self.project())

    def test_unknown_effect_backend_is_not_a_silent_fallback(self):
        data = vp.read(self.root / 'composition-plan.json')
        data['compositions'][0]['backend'] = 'pretend_blender'
        vp.write(self.root / 'composition-plan.json', data)
        with self.assertRaises(ValueError):
            vp.composition_plan(self.root, self.project())

    def test_asset_path_escape_rejected(self):
        with self.assertRaises(ValueError):
            vp.path_at(self.root, '../outside.png')

    def test_compiler_rejects_missing_current_production_decisions(self):
        project = self.project()
        project['render_authorized'] = True
        vp.write(self.root / 'project.json', project)
        with self.assertRaises(ValueError):
            compile_manifest(self.root)

    def test_handoff_surfaces_new_gates_without_advancing(self):
        wc.handoff(self.root, 'new-handoff.md')
        text = (self.root / 'new-handoff.md').read_text()
        self.assertIn('视觉制作方法确认', text)
        self.assertIn('代表性 Blender Proof 与动态样片确认', text)
        self.assertEqual(self.project()['current_stage'], 'D2')
        self.assertEqual(self.project()['workflow_control']['confirmations'], {})

    @unittest.skipUnless(os.environ.get('BLENDER_EXECUTABLE') and shutil.which('ffmpeg') and shutil.which('ffprobe'),
                         'Set BLENDER_EXECUTABLE for actual video and native-scene integration')
    def test_video_text_layers_and_native_scene_adapter_reproduce_actual_frames(self):
        vp.run([vp.tool('ffmpeg'), '-v', 'error', '-n', '-loop', '1', '-i', str(self.root / 'media/a.png'),
                '-r', '25', '-frames:v', '125', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(self.root / 'media/input.mp4')])
        plan = vp.read(self.root / 'composition-plan.json')
        original = plan['compositions'][0]
        original['layers'][0].update(kind='video', asset_ref='media/input.mp4', source_in_frame=5)
        original['layers'].append({'layer_id': 'label', 'kind': 'text', 'text': 'ENGINEERING TEST',
                                   'font_size': 16, 'start_frame': 0, 'end_frame': 125,
                                   'transform': {'y': -60}, 'color': [1, 1, 1, 1]})
        vp.write(self.root / 'composition-plan.json', plan)
        self.approve_preparation()
        first = render(self.root, 'C01', os.environ['BLENDER_EXECUTABLE'])
        native = copy.deepcopy(original)
        native.update(composition_id='C02', mode='native_blend', native_scene_ref=original['scene_ref'],
                      native_start_frame=1, native_dependency_refs=['media/input.mp4', 'media/b.png'])
        native.pop('layers')
        native.pop('groups')
        for key in ('scene_ref', 'video_ref', 'demo_ref', 'proof_ref', 'receipt_ref', 'readback_ref', 'review_ref'):
            native[key] = original[key].replace('C01', 'C02')
        plan.pop('proof_composition_id', None)
        plan.update(proof_composition_ids=['C02'], compositions=[native])
        layers_root = self.root
        self.root = layers_root.with_name('native-project')
        build(self.root)
        shutil.copy2(layers_root / 'media/input.mp4', self.root / 'media/input.mp4')
        scene = self.root / original['scene_ref']
        scene.parent.mkdir(parents=True)
        shutil.copy2(layers_root / original['scene_ref'], scene)
        (self.root / 'test-decisions.md').write_text('# Simulated test decisions\n\n' + self.quote + '\n')
        vp.write(self.root / 'composition-plan.json', plan)
        lock_file = self.root / 'implementation-lock.json'
        lock = vp.read(lock_file)
        lock['parameter_bindings'] = []
        lock['safe_adaptation']['allowed'] = []
        for element in lock['elements'].values():
            element['renderer'] = 'blender_native_blend'
        vp.write(lock_file, lock)
        self.approve_preparation()
        second = render(self.root, 'C02', os.environ['BLENDER_EXECUTABLE'])
        self.assertEqual(first['technical'], second['technical'])
        from PIL import Image, ImageChops
        with Image.open(vp.path_at(layers_root, original['proof_ref'])) as left, Image.open(vp.path_at(self.root, native['proof_ref'])) as right:
            self.assertIsNone(ImageChops.difference(left.convert('RGB'), right.convert('RGB')).getbbox())
        self.assertFalse(vp.read(vp.path_at(self.root, native['review_ref']))['playback_verified'])
        self.assertFalse(wc.report(self.root, 'render')['action_allowed'])

    @unittest.skipUnless(os.environ.get('BLENDER_EXECUTABLE') and shutil.which('ffmpeg') and shutil.which('ffprobe'),
                         'Set BLENDER_EXECUTABLE for actual native render integration')
    def test_real_blender_render_review_gates_ffmpeg_finish_and_final_qa(self):
        self.approve_preparation()
        receipt = render(self.root, 'C01', os.environ['BLENDER_EXECUTABLE'])
        self.assertEqual(receipt['backend'], 'blender')
        self.assertEqual(receipt['technical']['frames'], 125)
        self.assertEqual(self.project()['visual_gate_status'], 'awaiting_proof')
        self.assertFalse(self.project()['render_authorized'])
        self.assertFalse(wc.report(self.root, 'render')['action_allowed'])
        with self.assertRaises(ValueError):
            self.approve(('composition',))
        job = vp.read(self.root / 'composition-plan.json')['compositions'][0]
        original_reference = (self.root / 'demo-spec.md').read_text()
        (self.root / 'demo-spec.md').write_text(original_reference.replace('Synthetic stereo test tone only.', 'Changed audio treatment.'))
        with self.assertRaisesRegex(ValueError, 'inputs changed'):
            vp.validate_job_receipt(self.root, self.project(), vp.read(self.root / 'composition-plan.json'), job)
        (self.root / 'demo-spec.md').write_text(original_reference)
        reopened = self.root / 'reopened.png'
        code = ('import bpy,sys; from pathlib import Path; '
                's=bpy.context.scene; s.frame_set(75); '
                'e=s.sequence_editor; strips=getattr(e,"strips",getattr(e,"sequences",[])); '
                'a=next(x for x in strips if x.name=="panel-a"); '
                'assert abs(a.transform.scale_x-1.08)<0.001; '
                's.render.filepath=sys.argv[-1]; bpy.ops.render.render(write_still=True)')
        vp.run([os.environ['BLENDER_EXECUTABLE'], '--background', '--disable-autoexec',
                str(vp.path_at(self.root, job['scene_ref'])), '--python-exit-code', '1',
                '--python-expr', code, '--', str(reopened)], timeout=120)
        from PIL import Image, ImageChops
        with Image.open(reopened) as actual, Image.open(vp.path_at(self.root, job['proof_ref'])) as expected:
            self.assertIsNone(ImageChops.difference(actual.convert('RGB'), expected.convert('RGB')).getbbox(),
                              'Reopened native engineering must reproduce the held end-state proof')
        review = vp.read(vp.path_at(self.root, job['review_ref']))
        # Simulate the approval surface in an isolated test. These records are
        # never distributed as user approvals or aesthetic acceptance evidence.
        review.update(reviewer='simulated_fixture_reviewer', playback_verified=True, blocking_issues=[])
        selected_refs = sorted({rid for method in vp.methods(self.root, self.project())['methods']
                                if method.get('visual_reference_status') == 'used'
                                for rid in method.get('visual_reference_refs', [])})
        for check in review['checks']:
            check.update(status='pass', method='simulated review record for gate mechanics',
                         evidence=[job['demo_ref']], finding='Fixture record only; not aesthetic acceptance')
            if check['name'] == 'ReferenceCompliance':
                check.update(
                    evidence=[self.project()['visual_mockup_ref'], job['proof_ref'],
                              self.project()['visual_pipeline']['implementation_lock_ref']],
                    reference_ref_ids=selected_refs,
                    implementation_lock_sha256=vp.binding(
                        self.root, self.project()['visual_pipeline']['implementation_lock_ref'])['sha256'],
                    mockup_sha256=vp.binding(self.root, self.project()['visual_mockup_ref'])['sha256'],
                    proof_sha256=vp.binding(self.root, job['proof_ref'])['sha256'])
        vp.write(vp.path_at(self.root, job['review_ref']), review)
        self.approve(('proof', 'composition', 'plan'))
        self.assertTrue(wc.report(self.root, 'authorize')['action_allowed'])
        authorization = prepare(self.root)
        authorization.update(status='confirmed', authorization_id='SIMULATED-COMPOSITION-AUTH', confirmed_by='simulated_fixture_user')
        vp.write(self.root / 'execution-authorization.json', authorization)
        from execution_integrity import digest
        project = self.project()
        project['execution_authorization_digest'] = digest(authorization)
        project['render_authorized'] = True
        vp.write(self.root / 'project.json', project)
        timeline = vp.read(self.root / 'timeline.json')
        timeline['status'] = 'ready_for_render'
        vp.write(self.root / 'timeline.json', timeline)
        manifest = compile_manifest(self.root)
        vp.write(self.root / 'render-manifest.json', manifest)
        (self.root / 'render').mkdir()
        vp.run([vp.tool('ffmpeg'), '-v', 'error', '-n', '-loop', '1', '-i', str(self.root / 'media/a.png'),
                '-r', '25', '-frames:v', '125', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(self.root / 'render/clean-video.mp4')])
        final = finish(self.root)
        self.assertEqual(final['technical']['frames'], 125)
        self.assertEqual(final['technical']['audio_streams'], 1)
        self.assertFalse(wc.report(self.root, 'deliver_complete')['action_allowed'])
        self.assertEqual(vp.verify_delivery_receipt(self.root, self.project())['artifact'], final['artifact'])
        qa = {'project_id': self.project()['project_id'], 'artifact_sha256': final['artifact']['sha256'],
              'final_playback_verified': True, 'blocking_issues': [],
              'checks': [{'name': name, 'status': 'pass', 'method': 'simulated fixture QA record',
                          'evidence': [final['output_ref']], 'finding': 'Tests the gate only'}
                         for name in sorted(wc.QA_NAMES | set(vp.FINAL_CHECKS))]}
        selected_refs = sorted({rid for method in vp.methods(self.root, self.project())['methods']
                                if method.get('visual_reference_status') == 'used'
                                for rid in method.get('visual_reference_refs', [])})
        lock_ref = self.project()['visual_pipeline']['implementation_lock_ref']
        for check in qa['checks']:
            if check['name'] == 'ReferenceCompliance':
                check.update(
                    evidence=[self.project()['visual_mockup_ref'], self.project()['visual_proof_ref'], lock_ref],
                    reference_ref_ids=selected_refs,
                    implementation_lock_sha256=vp.binding(self.root, lock_ref)['sha256'],
                    mockup_sha256=vp.binding(self.root, self.project()['visual_mockup_ref'])['sha256'],
                    proof_sha256=vp.binding(self.root, self.project()['visual_proof_ref'])['sha256'])
            elif check['name'] == 'CompositionCompliance':
                check.update(
                    evidence=['render-manifest.json'] + [row['video']['ref'] for row in manifest['compositions']],
                    composition_windows=[{'composition_id': row['composition_id'],
                                          'start_frame': row['start_frame'], 'end_frame': row['end_frame'],
                                          'video_sha256': row['video']['sha256'], 'status': 'pass',
                                          'finding': 'Synthetic fixture watched this production composition window.',
                                          **({'join_finding': 'Synthetic fixture checked the declared join continuously.'}
                                             if next(job for job in vp.composition_plan(self.root, self.project())['compositions']
                                                     if job['composition_id'] == row['composition_id']).get('joins') else {})}
                                         for row in manifest['compositions']])
        vp.write(self.root / 'qa.json', qa)
        self.assertTrue(wc.report(self.root, 'deliver_complete')['action_allowed'])
        qa['checks'] = [row for row in qa['checks'] if row['name'] != 'MotionContinuity']
        vp.write(self.root / 'qa.json', qa)
        self.assertFalse(wc.report(self.root, 'deliver_complete')['action_allowed'])
        original_plan = vp.read(self.root / 'composition-plan.json')
        changed = copy.deepcopy(original_plan)
        changed['compositions'][0]['groups']['push']['keyframes'][1]['values']['scale'] = 1.5
        vp.write(self.root / 'composition-plan.json', changed)
        self.assertEqual(wc.evaluate(self.root)['composition']['status'], 'stale')
        self.assertFalse(wc.report(self.root, 'render')['action_allowed'])
        vp.write(self.root / 'composition-plan.json', original_plan)
        current = self.project()
        current['workflow_control']['qa_ref'] = 'new-qa.json'
        # qa_ref must be declared before compiling; mutating project after
        # delivery deliberately invalidates its receipt/manifest.
        vp.write(self.root / 'project.json', current)
        self.assertFalse(wc.report(self.root, 'qa_start')['action_allowed'])
