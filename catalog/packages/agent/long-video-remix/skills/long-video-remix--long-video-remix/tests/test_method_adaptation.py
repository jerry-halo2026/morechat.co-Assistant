"""Narrative revisions inherit confirmed methods and apply exact parameter patches."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import visual_pipeline as vp
from _composition_smoke import build
from _synthetic_project import install_test_catalog, SYNTHETIC_REFERENCE
import workflow_control as wc
from prepare_execution_authorization import prepare
from render_blender_composition import render
from compile_render_manifest import compile_manifest


@unittest.skipUnless(importlib.util.find_spec('PIL'), 'Synthetic fixture requires Pillow')
class MethodAdaptationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'project'
        self.addCleanup(self.temp.cleanup)
        self.test_package = Path(self.temp.name) / 'package'
        install_test_catalog(self, self.test_package)
        build(self.root)
        self.quote = 'SYNTHETIC FIXTURE: approve this displayed method and its declared adaptation bounds.'
        (self.root / 'decisions.md').write_text(self.quote + '\n', encoding='utf-8')

    def project(self):
        return vp.read(self.root / 'project.json')

    def approve(self, keys=('direction', 'audio', 'mockup', 'method')):
        shown = []
        for key in keys:
            shown += [ref for ref in wc.required_shown_refs(self.root, self.project(), key) if ref not in shown]
        return wc.confirm(self.root, keys, 'synthetic_fixture_user', 'decisions.md', self.quote, shown)

    def patch(self, value=1.1, slot='push_scale_end', old=1.08):
        path = self.root / self.project()['narrative_direction_ref']
        basis = 'SYNTHETIC NARRATIVE: adapt only the requested parameter, preserving the approved method.'
        if basis not in path.read_text():
            path.write_text(path.read_text() + '\n' + basis + '\n', encoding='utf-8')
        return {'schema_version': '1.0', 'base_sha256': self.project()['workflow_control']['method_preservation']['baseline']['sha256'],
                'narrative_sha256': vp.sha(path), 'instruction_ref': self.project()['narrative_direction_ref'],
                'quote': basis, 'changes': [{'slot': slot, 'old': old, 'value': value, 'narrative_basis': basis}]}

    def hashes(self):
        return {p.relative_to(self.root).as_posix(): vp.sha(p) for p in self.root.rglob('*') if p.is_file()}

    def text_slot(self):
        timeline = vp.read(self.root / 'timeline.json')
        row = timeline['text_tracks'][0]
        identity = 'text_id' if 'text_id' in row else 'track_id'
        slot = {'slot': 'creator_copy', 'artifact': 'timeline',
                'path': '/text_tracks/@' + identity + '=' + row[identity] + '/text', 'type': 'string', 'max_length': 100}
        old = row['text']
        for filename in ('execution-plan.md', 'execution-reference.md'):
            path = self.root / filename
            path.write_text(path.read_text() + '\n<!-- lvr:param creator_copy -->' + old + '<!-- /lvr:param creator_copy -->\n', encoding='utf-8')
        lock = vp.read(self.root / 'implementation-lock.json')
        lock['safe_adaptation']['allowed'].append(slot)
        lock['parameter_bindings'].append({'source': {'artifact': 'timeline', 'path': slot['path']},
            'targets': [{'artifact': name, 'path': 'block:creator_copy'} for name in ('execution-plan', 'execution-reference')]})
        vp.write(self.root / 'implementation-lock.json', lock)
        return old

    def independent_second_job(self):
        methods = vp.read(self.root / 'visual-methods.json')
        second = copy.deepcopy(methods['methods'][0]); second['method_id'] = 'PM002'
        second['selected_treatment'] = 'Independent synthetic push slot for a second composition.'
        methods['methods'].append(second); vp.write(self.root / 'visual-methods.json', methods)
        lock = vp.read(self.root / 'implementation-lock.json')
        for old, new in [('PANEL_PUSH', 'SECOND_PUSH'), ('PANEL_CUT', 'SECOND_CUT')]:
            lock['elements'][new] = copy.deepcopy(lock['elements'][old])
        trace = copy.deepcopy(lock['reference_trace'][0]); trace['method_id'] = 'PM002'; trace['target_element_ids'] = ['SECOND_PUSH']
        trace['parameter_paths'] = [x.replace('PANEL_PUSH', 'SECOND_PUSH') for x in trace['parameter_paths']]
        lock['reference_trace'].append(trace)
        rule = copy.deepcopy(lock['safe_adaptation']['allowed'][0]); rule['slot'] = 'second_push_scale_end'; rule['path'] = rule['path'].replace('PANEL_PUSH', 'SECOND_PUSH')
        lock['safe_adaptation']['allowed'].append(rule)
        binding = copy.deepcopy(lock['parameter_bindings'][0]); binding['source']['path'] = rule['path']
        for target in binding['targets']:
            target['path'] = target['path'].replace('PM001', 'PM002').replace('C01', 'C02')
        lock['parameter_bindings'].append(binding); vp.write(self.root / 'implementation-lock.json', lock)
        plan = vp.read(self.root / 'composition-plan.json')
        job = copy.deepcopy(plan['compositions'][0]); job['composition_id'] = 'C02'; job['method_ids'] = ['PM002']; job['implementation_element_ids'] = ['SECOND_PUSH', 'SECOND_CUT']
        for key in wc.JOB_OUTPUT_KEYS:
            job[key] = job[key].replace('C01', 'C02')
        plan['compositions'].append(job); plan['proof_composition_ids'].append('C02'); vp.write(self.root / 'composition-plan.json', plan)

    def test_method_confirmation_captures_one_portable_baseline(self):
        self.approve()
        self.assertIsNotNone(wc.method_guard(self.root, self.project()))
        baseline = self.project()['workflow_control']['method_preservation']['baseline']
        self.assertEqual(baseline['ref'], 'method-baseline.json')
        self.assertEqual(vp.sha(self.root / baseline['ref']), baseline['sha256'])
        self.assertIn('method-baseline.json', wc.portable_artifact_refs(self.root, self.project()))
        self.assertEqual(len(list(self.root.glob('method-baseline*.json'))), 1)

    def test_legal_patch_synchronizes_parameters_and_preserves_method_confirmation(self):
        self.approve(); before = copy.deepcopy(self.project()['workflow_control']['confirmations'])
        result = wc.adapt_method(self.root, self.patch())
        self.assertEqual(result['affected_compositions'], ['C01'])
        self.assertEqual(vp.read(self.root / 'implementation-lock.json')['elements']['PANEL_PUSH']['parameters']['scale_end'], 1.1)
        self.assertEqual(vp.read(self.root / 'visual-methods.json')['methods'][0]['parameters']['scale_end'], 1.1)
        self.assertEqual(vp.read(self.root / 'composition-plan.json')['compositions'][0]['groups']['push']['keyframes'][1]['values']['scale'], 1.1)
        self.assertEqual(vp.read(self.root / 'composition-plan.json')['compositions'][0]['joins'][0]['outgoing_state'], 'Hold the 1.1 scale; no reset')
        self.assertEqual(self.project()['workflow_control']['confirmations'], before)
        states = wc.evaluate(self.root)
        self.assertEqual(states['method']['status'], 'satisfied')
        self.assertEqual(states['audio']['status'], 'satisfied')
        self.assertEqual(states['direction']['status'], 'stale')
        self.assertFalse(self.project()['render_authorized'])

    def test_current_narrative_must_be_applied_before_dependent_actions(self):
        self.approve(); self.patch()
        self.assertIn('Narrative changed', wc.report(self.root, 'build_composition')['lineage_error'])
        with self.assertRaisesRegex(ValueError, 'LINEAGE_VIOLATION'):
            prepare(self.root)

    def test_cli_applies_a_patch_with_no_automatic_approval(self):
        self.approve(); patch = self.patch(); file = self.root / 'requested-patch.json'; vp.write(file, patch)
        shutil.copytree(ROOT / 'scripts', self.test_package / 'scripts')
        result = subprocess.run([sys.executable, str(self.test_package / 'scripts/workflow_control.py'), 'adapt', str(self.root), '--patch', str(file)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'applied')
        self.assertTrue(json.loads(result.stdout)['method_preserved'])
        self.assertFalse(self.project()['render_authorized'])

    def test_same_element_id_cannot_hide_motion_grammar_drift(self):
        self.approve(); plan = vp.read(self.root / 'composition-plan.json')
        plan['compositions'][0]['groups']['push']['keyframes'][1]['easing'] = 'linear'; vp.write(self.root / 'composition-plan.json', plan)
        self.assertIn('untracked edit', wc.report(self.root, 'build_composition')['lineage_error'])
        with self.assertRaisesRegex(ValueError, 'LINEAGE_VIOLATION'):
            render(self.root, 'C01', blender='not-invoked')
        with self.assertRaisesRegex(ValueError, 'LINEAGE_VIOLATION'):
            self.approve(('method',))

    def test_regular_confirm_and_init_cannot_rebaseline_manual_changes(self):
        self.approve(); baseline = (self.root / 'method-baseline.json').read_bytes()
        for filename, field in [('implementation-lock.json', 'method'), ('visual-methods.json', 'plan')]:
            with self.subTest(artifact=filename):
                path = self.root / filename; original = path.read_bytes(); data = vp.read(path)
                data['unrequested'] = 'drift'; vp.write(path, data)
                with self.assertRaisesRegex(ValueError, 'LINEAGE_VIOLATION'):
                    self.approve((field,))
                wc.initialize(self.root)
                self.assertEqual((self.root / 'method-baseline.json').read_bytes(), baseline)
                self.assertIsNotNone(wc.report(self.root)['lineage_error'])
                path.write_bytes(original)

    def test_invalid_values_are_rejected_without_mutating_any_artifact(self):
        self.approve()
        for value in (1.5, True, '1.1', float('nan')):
            with self.subTest(value=str(value)):
                patch = self.patch(value); before = self.hashes()
                with self.assertRaises((ValueError, TypeError)):
                    wc.adapt_method(self.root, patch)
                self.assertEqual(self.hashes(), before)

    def test_wrong_base_value_narrative_and_slot_are_rejected(self):
        self.approve()
        for key, value in [('base_sha256', '0' * 64), ('narrative_sha256', '0' * 64), ('old', 1.09), ('slot', 'unknown'), ('narrative_basis', 'not in current narrative')]:
            with self.subTest(field=key):
                patch = self.patch()
                (patch['changes'][0] if key in ('old', 'slot', 'narrative_basis') else patch)[key] = value
                before = self.hashes()
                with self.assertRaisesRegex(ValueError, 'LINEAGE_VIOLATION'):
                    wc.adapt_method(self.root, patch)
                self.assertEqual(self.hashes(), before)

    def test_undeclared_extra_patch_changes_are_not_silently_accepted(self):
        self.approve(); patch = self.patch(); patch['changes'][0]['artifact'] = 'execution-plan'
        with self.assertRaisesRegex(ValueError, 'exact slot'):
            wc.adapt_method(self.root, patch)

    def test_binding_mismatch_is_rejected_before_method_confirmation(self):
        plan = vp.read(self.root / 'composition-plan.json'); plan['compositions'][0]['groups']['push']['keyframes'][1]['values']['scale'] = 1.09
        vp.write(self.root / 'composition-plan.json', plan)
        with self.assertRaisesRegex(ValueError, 'bound parameter differs'):
            self.approve()
        self.assertFalse((self.root / 'method-baseline.json').exists())

    def test_structural_fields_cannot_be_declared_as_parameter_slots(self):
        for artifact, path in [('composition-plan', '/compositions/@composition_id=C01/groups/push/keyframes/@key_id=push_end/easing'),
                               ('implementation-lock', '/elements/PANEL_PUSH/implementation_method')]:
            with self.subTest(path=path):
                with self.assertRaisesRegex(ValueError, 'method/identity'):
                    wc._method_safe_locator({'artifact': artifact, 'path': path})

    def test_array_indices_and_duplicate_ids_fail_closed(self):
        doc = {'rows': [{'id': 'x', 'value': 1}, {'id': 'x', 'value': 2}]}
        for path in ('/rows/0/value', '/rows/@id=x/value'):
            with self.assertRaisesRegex(ValueError, 'LINEAGE_VIOLATION'):
                wc._method_location(doc, path)

    def test_markdown_copy_changes_only_explicit_blocks(self):
        old = self.text_slot(); self.approve(); self.approve(('plan',))
        before = {name: (self.root / name).read_text() for name in ('execution-plan.md', 'execution-reference.md')}
        result = wc.adapt_method(self.root, self.patch(value='Updated narrative copy', slot='creator_copy', old=old))
        self.assertEqual(result['affected_compositions'], [])
        for name, content in before.items():
            self.assertEqual((self.root / name).read_text(), content.replace('<!-- lvr:param creator_copy -->' + old,
                                                                          '<!-- lvr:param creator_copy -->Updated narrative copy'))
        self.assertEqual(wc.evaluate(self.root)['method']['status'], 'satisfied')
        self.assertEqual(wc.evaluate(self.root)['plan']['status'], 'satisfied')
        self.assertIn('adaptation', self.project()['workflow_control']['confirmations']['plan'])

    def test_unrelated_plan_wording_is_blocked_even_when_the_method_is_unchanged(self):
        self.approve(); self.approve(('plan',))
        path = self.root / 'execution-plan.md'; path.write_text(path.read_text() + '\nUNREQUESTED REWRITE\n')
        with self.assertRaisesRegex(ValueError, 'untracked edit in execution-plan'):
            self.approve(('plan',))
        with self.assertRaisesRegex(ValueError, 'LINEAGE_VIOLATION'):
            compile_manifest(self.root)

    def test_missing_or_ambiguous_markdown_blocks_do_not_expand_scope(self):
        for text in ('no markers', '<!-- lvr:param x -->one<!-- /lvr:param x --><!-- lvr:param x -->two<!-- /lvr:param x -->'):
            with self.assertRaisesRegex(ValueError, 'Markdown parameter block'):
                wc._method_block(text, 'block:x')

    def test_unrelated_composition_input_digest_remains_valid(self):
        self.independent_second_job(); self.approve(); p = self.project(); plan = vp.composition_plan(self.root, p)
        before = {j['composition_id']: vp.digest(vp.job_input(self.root, p, plan, j)) for j in plan['compositions']}
        result = wc.adapt_method(self.root, self.patch(slot='second_push_scale_end'))
        p = self.project(); plan = vp.composition_plan(self.root, p)
        after = {j['composition_id']: vp.digest(vp.job_input(self.root, p, plan, j)) for j in plan['compositions']}
        self.assertEqual(result['affected_compositions'], ['C02'])
        self.assertEqual(before['C01'], after['C01'])
        self.assertNotEqual(before['C02'], after['C02'])
        self.assertEqual(plan['compositions'][0]['scene_ref'], 'compositions/C01/v1.blend')

    def test_transitive_shared_method_parameter_requires_all_render_targets(self):
        self.independent_second_job()
        methods = vp.read(self.root / 'visual-methods.json'); methods['methods'] = methods['methods'][:1]
        vp.write(self.root / 'visual-methods.json', methods)
        lock = vp.read(self.root / 'implementation-lock.json'); lock['reference_trace'] = lock['reference_trace'][:1]
        lock['parameter_bindings'] = lock['parameter_bindings'][:1]; lock['safe_adaptation']['allowed'] = lock['safe_adaptation']['allowed'][:1]
        vp.write(self.root / 'implementation-lock.json', lock)
        plan = vp.read(self.root / 'composition-plan.json'); plan['compositions'][1]['method_ids'] = ['PM001']; vp.write(self.root / 'composition-plan.json', plan)
        self.approve(); patch = self.patch(); before = self.hashes()
        with self.assertRaisesRegex(ValueError, 'shared parameter lacks bindings.*C02'):
            wc.adapt_method(self.root, patch)
        self.assertEqual(before, self.hashes())

    def test_unrelated_review_is_reused_without_rewriting_its_findings(self):
        self.independent_second_job(); self.approve(); project = self.project(); plan = vp.composition_plan(self.root, project)
        job = plan['compositions'][0]
        for key in ('scene_ref', 'video_ref', 'demo_ref', 'proof_ref', 'readback_ref'):
            file = self.root / job[key]; file.parent.mkdir(parents=True, exist_ok=True); file.write_bytes(('SYNTHETIC-REVIEW-CONTRACT-' + key).encode())
        receipt = {'schema_version':'1.0', 'status':'rendered_not_reviewed', 'backend':'blender', 'backend_version':'synthetic-fixture',
            'project_id':project['project_id'], 'composition_id':'C01', 'input_digest':vp.digest(vp.job_input(self.root, project, plan, job)),
            'artifacts':[vp.binding(self.root, job[key]) for key in ('scene_ref','video_ref','demo_ref','proof_ref','readback_ref')],
            'technical':{'frames':job['frame_count'],'full_decode':'pass'}}
        vp.write(self.root / job['receipt_ref'], receipt)
        checks=[]
        for name in vp.REVIEW_CHECKS:
            check={'name':name,'status':'pass','method':'synthetic protocol check only','finding':'Synthetic fixture; no real viewing claim.', 'evidence':[job['demo_ref']]}
            if name=='ReferenceCompliance':
                check['evidence'] = [project['visual_mockup_ref'], job['proof_ref'], 'implementation-lock.json']
                check.update(reference_ref_ids=[SYNTHETIC_REFERENCE], implementation_lock_sha256=vp.sha(self.root / 'implementation-lock.json'),
                    mockup_sha256=vp.sha(self.root / project['visual_mockup_ref']),proof_sha256=vp.sha(self.root / job['proof_ref']))
            checks.append(check)
        review={'composition_id':'C01','demo_sha256':vp.sha(self.root/job['demo_ref']), 'engineering_sha256':vp.sha(self.root/job['scene_ref']),
            'render_input_digest':receipt['input_digest'], 'reviewer':'synthetic_fixture_reviewer','playback_verified':True,'blocking_issues':[],'checks':checks}
        vp.write(self.root/job['review_ref'],review); original=(self.root/job['review_ref']).read_bytes()
        for old,value in ((1.08,1.10),(1.10,1.11)):
            wc.adapt_method(self.root,self.patch(value=value,slot='second_push_scale_end',old=old))
            project=self.project(); plan=vp.composition_plan(self.root,project); job=plan['compositions'][0]
            receipt=vp.validate_job_receipt(self.root,project,plan,job,require_proof=True)
            vp.validate_review(self.root,project,job,receipt)
            self.assertEqual((self.root/job['review_ref']).read_bytes(),original)

    def test_shared_parameter_without_complete_mapping_is_rejected(self):
        plan = vp.read(self.root / 'composition-plan.json'); job = copy.deepcopy(plan['compositions'][0]); job['composition_id'] = 'C02'
        for key in wc.JOB_OUTPUT_KEYS:
            job[key] = job[key].replace('C01', 'C02')
        job['proof_covered_by'] = 'C01'; job['proof_coverage_reason'] = 'Synthetic same-method covered job.'
        plan['compositions'].append(job); vp.write(self.root / 'composition-plan.json', plan)
        self.approve()
        with self.assertRaisesRegex(ValueError, 'shared parameter lacks bindings'):
            wc.adapt_method(self.root, self.patch())

    def test_noop_narrative_revision_does_not_force_a_new_composition(self):
        self.approve(); result = wc.adapt_method(self.root, self.patch(value=1.08))
        self.assertEqual(result['affected_compositions'], [])
        self.assertEqual(vp.read(self.root / 'composition-plan.json')['compositions'][0]['scene_ref'], 'compositions/C01/v1.blend')

    def test_revision_uses_new_output_names_and_preserves_existing_outputs(self):
        self.approve(); old = self.root / 'compositions/C01/v1.blend'; old.parent.mkdir(parents=True); old.write_bytes(b'OLD ENGINEERING OUTPUT')
        wc.adapt_method(self.root, self.patch())
        self.assertEqual(old.read_bytes(), b'OLD ENGINEERING OUTPUT')
        self.assertNotEqual(vp.read(self.root / 'composition-plan.json')['compositions'][0]['scene_ref'], 'compositions/C01/v1.blend')

    def test_baseline_and_policy_cannot_be_deleted_to_waive_control(self):
        self.approve(); original_project = (self.root / 'project.json').read_bytes(); original_base = (self.root / 'method-baseline.json').read_bytes()
        for what in ('state', 'policy', 'file'):
            with self.subTest(deleted=what):
                p = self.project()
                if what == 'state': p['workflow_control'].pop('method_preservation'); vp.write(self.root / 'project.json', p)
                elif what == 'policy': p['execution_policy'].pop('method_preservation'); vp.write(self.root / 'project.json', p)
                else: (self.root / 'method-baseline.json').unlink()
                with self.assertRaisesRegex(ValueError, 'LINEAGE_VIOLATION'):
                    wc.method_guard(self.root, self.project())
                (self.root / 'project.json').write_bytes(original_project); (self.root / 'method-baseline.json').write_bytes(original_base)

    def test_rehashed_baseline_cannot_replace_confirmed_method_anchor(self):
        self.approve(); path = self.root / 'method-baseline.json'; b = vp.read(path)
        b['artifacts']['composition-plan']['data']['compositions'][0]['groups']['push']['keyframes'][1]['easing'] = 'linear'
        b['grammar_catalog'] = wc._method_projection(b['artifacts'])[1]
        b['method_digest'] = wc.method_contract_digest(b['artifacts'], b['context']); vp.write(path, b)
        p = self.project(); p['workflow_control']['method_preservation']['baseline']['sha256'] = vp.sha(path); vp.write(self.root / 'project.json', p)
        with self.assertRaisesRegex(ValueError, 'not anchored'):
            wc.method_guard(self.root, self.project())

    def test_interrupted_patch_is_blocked_and_recovery_restores_exact_bytes(self):
        self.approve(); patch = self.patch(); before = self.hashes()
        with mock.patch.object(wc, '_method_write_checkpoint', side_effect=OSError('simulated interruption')):
            with self.assertRaisesRegex(OSError, 'simulated interruption'):
                wc.adapt_method(self.root, patch)
        with self.assertRaisesRegex(ValueError, 'interrupted'):
            wc.method_guard(self.root, self.project())
        self.assertEqual(wc.recover_method_patch(self.root)['result'], 'restored_previous_baseline')
        self.assertEqual(self.hashes(), before)
        self.assertEqual(wc.adapt_method(self.root, patch)['status'], 'applied')

    def test_recovery_preserves_independently_edited_artifacts(self):
        self.approve(); patch = self.patch()
        with mock.patch.object(wc, '_method_write_checkpoint', side_effect=OSError('interruption')):
            with self.assertRaises(OSError): wc.adapt_method(self.root, patch)
        path = self.root / 'visual-methods.json'; path.write_text(path.read_text() + 'INDEPENDENT CHANGE')
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'independently'):
            wc.recover_method_patch(self.root)
        self.assertEqual(path.read_bytes(), before)

    def test_returning_to_plan_does_not_reset_the_method(self):
        self.approve(); before = self.project()['workflow_control']['method_preservation']['baseline']
        wc.advance(self.root, 'E', reason='Synthetic content verification correction.')
        wc.advance(self.root, 'D1', reason='Synthetic Narrative correction.')
        self.assertEqual(self.project()['workflow_control']['method_preservation']['baseline'], before)
        wc.method_guard(self.root, self.project())

    def test_explicit_method_change_uses_the_existing_d2_decision(self):
        self.approve(); wc.confirm(self.root, ('plan',), 'synthetic_fixture_user', 'decisions.md', self.quote, [])
        old = self.project()['workflow_control']['method_preservation']['baseline']['sha256']
        new_quote = 'SYNTHETIC FIXTURE: explicitly change the motion easing to linear for this method revision.'
        (self.root / 'decisions.md').write_text((self.root / 'decisions.md').read_text() + '\n## 修订指令\n' + new_quote + '\n')
        wc.revise(self.root, {'schema_version':'1.0','kind':'method','base_sha256':old,
            'narrative_sha256':vp.sha(self.root/self.project()['narrative_direction_ref']), 'instruction_ref':'decisions.md#修订指令','quote':new_quote,
            'scope':[{'artifact':'composition-plan','path':'/compositions/@composition_id=C01/groups/push/keyframes/@key_id=push_end/easing','op':'replace'}]})
        data = vp.read(self.root / 'composition-plan.json'); data['compositions'][0]['groups']['push']['keyframes'][1]['easing'] = 'linear'; vp.write(self.root / 'composition-plan.json', data)
        approval='SYNTHETIC REVIEW: inspected the easing diff and approve this method revision.'
        (self.root/'revision-decisions.md').write_text('## 本轮确认\n'+approval+'\n')
        wc.confirm(self.root, ('method','plan'), 'synthetic_fixture_user', 'revision-decisions.md#本轮确认', approval, [], True, old, wc.revision_preview(self.root)['diff_sha256'])
        self.assertNotEqual(self.project()['workflow_control']['method_preservation']['baseline']['sha256'], old)
        self.assertEqual(wc.evaluate(self.root)['method']['status'], 'satisfied')

    def test_old_approval_quote_cannot_unlock_a_different_method(self):
        self.approve(); old = self.project()['workflow_control']['method_preservation']['baseline']['sha256']
        with self.assertRaisesRegex(ValueError, 'scoped revise'):
            wc.confirm(self.root, ('method',), 'synthetic_fixture_user', 'decisions.md', self.quote, [], True, old)

    def test_explicit_narrative_only_revision_preserves_all_execution_parameters(self):
        self.approve(); patch = self.patch(); patch['changes'] = []
        patch['unchanged_execution_reason'] = patch['quote']
        result = wc.adapt_method(self.root, patch)
        self.assertEqual(result['affected_compositions'], [])
        self.assertEqual(result['changed_artifacts'], [])
        self.assertEqual(wc.evaluate(self.root)['method']['status'], 'satisfied')

    def test_method_change_flag_requires_d2_and_the_correct_parent(self):
        self.approve(); p = self.project(); p['current_stage'] = 'F'; vp.write(self.root / 'project.json', p)
        with self.assertRaisesRegex(ValueError, 'existing D2'):
            wc.confirm(self.root, ('method',), 'synthetic_fixture_user', 'decisions.md', self.quote, [], True, '0' * 64)

    def test_init_persists_new_control_for_existing_v11_projects(self):
        p = self.project(); p['execution_policy'].pop('method_preservation'); p['workflow_control'].pop('method_preservation')
        p['workflow_control']['schema_version']='1.1'; p['execution_policy']['workflow_gate_control']='required_v2'
        vp.write(self.root / 'project.json', p)
        wc.initialize(self.root)
        self.assertEqual(self.project()['execution_policy']['method_preservation'], wc.METHOD_POLICY)
        self.assertIn('method_preservation', self.project()['workflow_control'])
        self.assertEqual(self.project()['workflow_control']['schema_version'],'1.3')
        self.assertEqual(self.project()['execution_policy']['workflow_gate_control'],'required_v4')

    def test_shared_output_directory_remains_unique_after_two_job_revision(self):
        self.independent_second_job(); plan = vp.read(self.root / 'composition-plan.json')
        for job in plan['compositions']:
            for key in wc.JOB_OUTPUT_KEYS:
                job[key] = 'compositions/' + job['composition_id'] + '-' + Path(job[key]).name
        vp.write(self.root / 'composition-plan.json', plan); self.approve()
        patch = self.patch(); second = copy.deepcopy(patch['changes'][0]); second['slot'] = 'second_push_scale_end'; patch['changes'].append(second)
        result = wc.adapt_method(self.root, patch)
        self.assertEqual(result['affected_compositions'], ['C01', 'C02'])
        plan = vp.composition_plan(self.root, self.project())
        refs = [job[key] for job in plan['compositions'] for key in wc.JOB_OUTPUT_KEYS]
        self.assertEqual(len(refs), len(set(refs)))

    def test_project_commit_interruption_recovers_its_own_temporary_file(self):
        self.approve(); patch = self.patch(); replace = Path.replace
        def interrupted(path, destination):
            if path.name == 'project.json.workflow-tmp':
                raise OSError('simulated project commit interruption')
            return replace(path, destination)
        with mock.patch.object(Path, 'replace', interrupted):
            with self.assertRaises(OSError): wc.adapt_method(self.root, patch)
        self.assertTrue((self.root / 'project.json.workflow-tmp').exists())
        wc.recover_method_patch(self.root)
        self.assertFalse((self.root / 'project.json.workflow-tmp').exists())
        self.assertEqual(wc.adapt_method(self.root, patch)['status'], 'applied')

    def step0_setup(self):
        timeline = vp.read(self.root / 'timeline.json'); event = timeline['events'][0]
        event.update(source_in_ms=1100, source_out_ms=6100)
        event['d2_selection_snapshot'].update(planned_source_in_ms=1100, planned_source_out_ms=6100,
            allowed_adjustments=['add_transition_handle', 'trim_inside_safe_window'])
        timeline['audio_tracks'][0].update(source_in_ms=1100, source_out_ms=6100)
        vp.write(self.root / 'timeline.json', timeline)
        path = self.root / 'execution-plan.md'; path.write_text(path.read_text() + '\n## Execute Step 0\n\nPending calibration inside the approved safe windows.\n')
        self.approve(); self.approve(('plan',)); return timeline

    def test_authorized_step0_calibration_and_status_do_not_unlock_method(self):
        timeline = self.step0_setup(); before = self.project()['workflow_control']['confirmations']['method']
        timeline['events'][0].update(source_in_ms=1000, source_out_ms=6000)
        timeline['audio_tracks'][0].update(source_in_ms=1000, source_out_ms=6000)
        vp.write(self.root / 'timeline.json', timeline)
        path = self.root / 'execution-plan.md'; path.write_text(path.read_text().replace('Pending calibration', 'Completed calibration'))
        wc.method_guard(self.root, self.project())
        self.assertEqual(wc.evaluate(self.root)['method']['status'], 'satisfied')
        self.assertEqual(self.project()['workflow_control']['confirmations']['method'], before)

    def test_step0_does_not_allow_copy_policy_identity_or_out_of_window_drift(self):
        original = self.step0_setup()
        for change in ('copy', 'identity', 'gain', 'out_of_window', 'snapshot'):
            with self.subTest(change=change):
                timeline = copy.deepcopy(original)
                if change == 'copy': timeline['text_tracks'][0]['text'] += ' UNREQUESTED'
                elif change == 'identity': timeline['events'][0]['unit_id'] = 'UNREQUESTED'
                elif change == 'gain': timeline['audio_tracks'][0]['gain_db'] = -10
                elif change == 'snapshot': timeline['events'][0]['d2_selection_snapshot']['safe_in_start_ms'] = 0
                else: timeline['events'][0]['source_in_ms'] = 1
                vp.write(self.root / 'timeline.json', timeline)
                with self.assertRaisesRegex(ValueError, 'untracked edit in timeline'):
                    wc.method_guard(self.root, self.project())

    def test_step0_refreshes_output_paths_without_a_new_narrative(self):
        timeline = self.step0_setup()
        timeline['events'][0].update(source_in_ms=1000, source_out_ms=6000)
        timeline['audio_tracks'][0].update(source_in_ms=1000, source_out_ms=6000); vp.write(self.root / 'timeline.json', timeline)
        reason = 'SYNTHETIC FIXTURE: preserve the execution method for the already authorized Step 0 calibration.'
        (self.root / 'decisions.md').write_text(self.quote + '\n' + reason + '\n')
        p = self.project(); patch = {'schema_version':'1.0', 'base_sha256':p['workflow_control']['method_preservation']['baseline']['sha256'],
            'narrative_sha256':vp.sha(self.root / p['narrative_direction_ref']), 'instruction_ref':'decisions.md', 'quote':reason,
            'changes':[], 'unchanged_execution_reason':reason}
        result = wc.adapt_method(self.root, patch)
        self.assertEqual(result['affected_compositions'], ['C01'])
        wc.method_guard(self.root, self.project())

    def visual_stage_fixture(self):
        p = self.project(); p['visual_pipeline']['visual_stage_dir'] = 'visual'
        p['visual_mockup_ref'] = 'visual/mockup.svg'; directory = self.root / 'visual'; directory.mkdir()
        (directory / 'mockup.svg').write_bytes((self.root / 'mockup.svg').read_bytes())
        records = {'V0-intake':{}, 'V1-visual-problems':{}, 'V2-reference-selection':{'selections':[]},
            'V3-candidates':{'candidates':[{'id':'A','style':{'font_family':'synthetic-fixed'}}]},
            'V4-mockups':{},'V5-design-review':{},
            'V6-user-decision':{'status':'confirmed','chosen_candidate':'A','confirmed_artifacts':[{'candidate':'A','file':'mockup.svg','sha256':vp.sha(directory/'mockup.svg')}]},
            'V7-lock':{'chosen_candidate':'A','renderer':'synthetic','canvas':[320,180], 'style':{'font_family':'synthetic-fixed'},
                'elements':[{'id':'E1','role':'creator_text','text':'old copy','rect':[10,10,200,40],'t_in':0,'t_out':4}], 'reference_trace':[]}}
        for name,value in records.items():vp.write(directory/(name+'.json'),value)
        vp.write(self.root/'project.json',p)
        lock = vp.read(self.root/'implementation-lock.json'); lock['selected_mockup_ref']=p['visual_mockup_ref'];lock['selected_mockup_sha256']=vp.sha(directory/'mockup.svg')
        lock['confirmed_mockups']=[vp.binding(self.root,p['visual_mockup_ref'])];lock['reference_trace']=[]
        lock['visual_stage_binding']={'v7_ref':'visual/V7-lock.json','v7_sha256':vp.sha(directory/'V7-lock.json'),'chosen_candidate':'A'}
        vp.write(self.root/'implementation-lock.json',lock)
        def report(root,project,stage=None):
            return {'dir':'visual','statuses':{name:'PASS' for name in vp.VISUAL_STAGE_ORDER},
                'artifacts':{name:vp.binding(root,'visual/'+name+'.json') for name in vp.VISUAL_STAGE_ORDER}}
        return mock.patch.object(vp,'visual_stage_report',side_effect=report)

    def test_visual_content_binding_sync_preserves_the_method_and_pending_narrative(self):
        with self.visual_stage_fixture():
            self.approve(); before=self.project()['workflow_control']['confirmations']['method']; baseline=vp.read(self.root/'method-baseline.json')
            frame=self.root/'visual/mockup.svg';frame.write_bytes(frame.read_bytes()+b'<!-- synthetic revised copy -->')
            v6=vp.read(self.root/'visual/V6-user-decision.json');v6['confirmed_artifacts'][0]['sha256']=vp.sha(frame);vp.write(self.root/'visual/V6-user-decision.json',v6)
            v7=vp.read(self.root/'visual/V7-lock.json');v7['elements'][0]['text']='new Narrative copy';vp.write(self.root/'visual/V7-lock.json',v7)
            narrative=self.root/self.project()['narrative_direction_ref'];narrative.write_text(narrative.read_text()+'\nSynthetic Narrative updated for the new copy.\n')
            spec=importlib.util.spec_from_file_location('method_visual_sync',ROOT/'scripts/sync_visual_stage.py');sync=importlib.util.module_from_spec(spec);spec.loader.exec_module(sync)
            sync.sync_lock(self.root,self.project())
            self.assertEqual(self.project()['workflow_control']['confirmations']['method'],before)
            self.assertEqual(wc.evaluate(self.root)['method']['status'],'satisfied')
            self.assertEqual(vp.read(self.root/'method-baseline.json')['narrative'],baseline['narrative'])
            self.assertEqual(vp.read(self.root/'implementation-lock.json')['visual_stage_binding']['v7_sha256'],vp.sha(self.root/'visual/V7-lock.json'))
            self.assertIn('Narrative changed',wc.report(self.root)['lineage_error'])

    def test_visual_sync_does_not_accept_a_new_visual_method(self):
        with self.visual_stage_fixture():
            self.approve(); lock_before=(self.root/'implementation-lock.json').read_bytes()
            v7=vp.read(self.root/'visual/V7-lock.json');v7['style']['font_family']='unrequested redesign';vp.write(self.root/'visual/V7-lock.json',v7)
            spec=importlib.util.spec_from_file_location('method_visual_sync_reject',ROOT/'scripts/sync_visual_stage.py');sync=importlib.util.module_from_spec(spec);spec.loader.exec_module(sync)
            with self.assertRaisesRegex(ValueError,'visual grammar changed'):
                sync.sync_lock(self.root,self.project())
            self.assertEqual((self.root/'implementation-lock.json').read_bytes(),lock_before)

    def test_legacy_prose_adaptation_never_grants_parameter_permission(self):
        lock = vp.read(self.root / 'implementation-lock.json'); lock['safe_adaptation']['allowed'] = ['Adjust as needed.']; vp.write(self.root / 'implementation-lock.json', lock)
        self.approve()
        with self.assertRaisesRegex(ValueError, 'unknown/duplicate parameter slot'):
            wc.adapt_method(self.root, self.patch())

    def test_unchanged_legacy_method_can_be_adopted_without_inventing_a_decision(self):
        p = self.project(); p['workflow_control']['confirmations']['method'] = {
            'actor': 'synthetic_fixture_user', 'confirmation_ref': 'decisions.md', 'quote': self.quote,
            'input_digest': vp.digest(vp.legacy_method_inputs(self.root, p))}
        vp.write(self.root / 'project.json', p)
        result = wc.adopt_confirmed_method(self.root)
        self.assertEqual(result['status'], 'adopted')
        self.assertEqual(wc.evaluate(self.root)['method']['status'], 'satisfied')
        self.assertEqual(self.project()['workflow_control']['confirmations']['method']['quote'], self.quote)

    def test_edited_legacy_method_cannot_be_adopted_as_unchanged(self):
        p = self.project(); p['workflow_control']['confirmations']['method'] = {
            'actor': 'synthetic_fixture_user', 'confirmation_ref': 'decisions.md', 'quote': self.quote,
            'input_digest': vp.digest(vp.legacy_method_inputs(self.root, p))}; vp.write(self.root / 'project.json', p)
        lock = vp.read(self.root / 'implementation-lock.json'); lock['elements']['PANEL_PUSH']['implementation_method'] = 'new_method'; vp.write(self.root / 'implementation-lock.json', lock)
        with self.assertRaisesRegex(ValueError, 'old method inputs have changed'):
            wc.adopt_confirmed_method(self.root)


if __name__ == '__main__':
    unittest.main()
