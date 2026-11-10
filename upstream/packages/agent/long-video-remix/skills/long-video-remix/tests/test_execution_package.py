"""Exercise cross-model package declarations and stale-reference protection.

Fixtures are synthetic records; no video, typography or visual QA is certified.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / 'scripts'))
from check_render_authorization import check
from compile_render_manifest import compile_manifest
from execution_integrity import digest
from prepare_execution_authorization import prepare
from validate_project import validate
from test_execution_integrity import write_fixture


class ExecutionPackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.files = json.loads((PACKAGE / 'tests/fixtures/ready-project.json').read_text())
        self.files['project.json'].update(
            execution_package_policy='plan_and_reference',
            structure_exceptions_ref='structure-exceptions.jsonl',
            keyframe_references_ref='keyframe-references.json',
            execution_handoff_ref='execution-handoff.md',
            execution_reference_ref='execution-reference.md',
            execution_reference_asset_refs=[])
        self.files['execution-handoff.md'] = 'Synthetic handoff with source evidence and downstream package requirements.\n'
        self.files['execution-reference.md'] = 'Synthetic confirmed production rules; no image preview is claimed.\n'
        self.files['keyframe-references.json'] = [{
            'frame_id': 'F001', 'source_id': 'SRC001', 'timestamp_ms': 1000,
            'image_ref': None, 'source_segment': 'U001', 'narrative_role': 'opening',
            'notes': 'Image export is unavailable; source evidence remains in existing records.',
            'status': 'unavailable', 'reason': 'This environment cannot export a frame image.',
            'impact': 'low', 'downstream_handling': 'Continue with explicit production parameters; do not claim an image preview.'}]
        self.files['structure-exceptions.jsonl'] = [{
            'exception_id': 'EX001', 'stage': 'E', 'artifact': 'keyframe-references.json',
            'record_id': 'F001', 'field': 'image_ref', 'status': 'unavailable',
            'reason': 'This environment cannot export a frame image.', 'impact': 'low',
            'downstream_handling': 'Carry the gap into the handoff and use specified production rules.'}]
        self.save()

    def save(self, confirm=True):
        write_fixture(self.root, self.files)
        if confirm:
            # Only this test author confirms its own synthetic decision.
            auth = prepare(self.root)
            auth.update(status='confirmed', confirmed_by='synthetic-test-author',
                        authorization_id='AUTH-PACKAGE-SYNTHETIC')
            (self.root / 'execution-authorization.json').write_text(json.dumps(auth))
            project = self.files['project.json'].copy()
            project['execution_authorization_digest'] = digest(auth)
            (self.root / 'project.json').write_text(json.dumps(project))

    def assert_blocked(self, message):
        report = validate(self.root)
        self.assertEqual(report['status'], 'fail', report)
        self.assertTrue(any(message in x for x in report['errors']), report['errors'])
        with self.assertRaises(ValueError):
            compile_manifest(self.root)

    def test_image_export_exception_continues_without_weakening_render_checks(self):
        report = validate(self.root)
        self.assertEqual(report['status'], 'pass', report['errors'])
        self.assertTrue(any('unavailable' in x for x in report['warnings']))
        self.assertTrue(compile_manifest(self.root)['render_allowed'])

    def test_missing_handoff_blocks_false_detail_completion(self):
        (self.root / 'execution-handoff.md').unlink()
        self.assert_blocked('execution-handoff.md')

    def test_missing_reference_blocks_new_package_execution(self):
        (self.root / 'execution-reference.md').unlink()
        self.assert_blocked('execution reference document')

    def test_changed_reference_invalidates_confirmation_and_old_manifest(self):
        manifest = compile_manifest(self.root)
        (self.root / 'execution-reference.md').write_text('Changed style decision without reconfirmation.\n')
        self.assert_blocked('execution_reference_ref changed since confirmation')
        with self.assertRaises(ValueError):
            check(self.root, manifest)

    def test_style_asset_change_invalidates_confirmation(self):
        # A byte fixture tests identity only; this is not a claimed reference image.
        self.files['style-sample.dat'] = 'First synthetic reference asset.\n'
        self.files['project.json']['execution_reference_asset_refs'] = ['style-sample.dat']
        self.save()
        manifest = compile_manifest(self.root)
        (self.root / 'style-sample.dat').write_text('Changed synthetic asset.\n')
        self.assert_blocked('reference assets changed since confirmation')
        with self.assertRaises(ValueError):
            check(self.root, manifest)

    def test_missing_mockup_is_a_reminder_not_a_block(self):
        report = validate(self.root)
        self.assertEqual(report['status'], 'pass', report['errors'])
        self.assertTrue(any('no mockup' in x for x in report['warnings']), report['warnings'])
        self.assertTrue(compile_manifest(self.root)['render_allowed'])

    def test_declared_mockup_removes_the_reminder(self):
        # A byte fixture tests declaration only; it is not a claimed mockup image.
        self.files['mockup-01.dat'] = 'Synthetic mockup placeholder bytes.\n'
        self.files['project.json']['execution_reference_asset_refs'] = ['mockup-01.dat']
        self.save()
        report = validate(self.root)
        self.assertEqual(report['status'], 'pass', report['errors'])
        self.assertFalse(any('no mockup' in x for x in report['warnings']), report['warnings'])

    def enable_visual_gate(self, status='not_started'):
        self.files['project.json'].update(
            schema_version='1.7', visual_gate_status=status,
            visual_mockup_ref=None, visual_proof_ref=None)
        self.files['capability-map.json'] = {
            'schema_version': '1.0', 'capabilities': [{
                'capability': 'render_visual_proof', 'actual_tool': 'python3',
                'entrypoint': 'render_visual_proof.py', 'status': 'available',
                'output_mapping': {'proof': 'proof-01.dat'}}]}
        self.files['render_visual_proof.py'] = 'print(\"synthetic proof renderer\")\n'

    def test_schema_17_new_package_cannot_omit_visual_gate_fields(self):
        self.files['project.json']['schema_version'] = '1.7'
        for key in ('visual_gate_status', 'visual_mockup_ref', 'visual_proof_ref'):
            self.files['project.json'].pop(key, None)
        self.save()
        self.assert_blocked('project schema 1.7+ requires visual_gate_status')

    def test_schema_17_requires_new_execution_package_policy(self):
        self.files['project.json']['schema_version'] = '1.7'
        self.files['project.json'].pop('execution_package_policy', None)
        self.save()
        self.assert_blocked('project schema 1.7+ requires execution_package_policy=plan_and_reference')

    def test_new_visual_gate_blocks_ready_before_proof(self):
        self.enable_visual_gate('not_started')
        self.save()
        self.assert_blocked('visual_gate_status=proof_confirmed or not_applicable')

    def test_visual_gate_not_applicable_allows_nonvisual_project(self):
        self.enable_visual_gate('not_applicable')
        self.save()
        report = validate(self.root)
        self.assertEqual(report['status'], 'pass', report['errors'])
        self.assertTrue(compile_manifest(self.root)['render_allowed'])

    def test_mockup_can_be_confirmed_while_gate_stays_open(self):
        self.enable_visual_gate('awaiting_proof')
        self.files['mockup-01.dat'] = 'Synthetic aesthetic mockup bytes.\n'
        self.files['project.json']['visual_mockup_ref'] = 'mockup-01.dat'
        self.files['project.json']['execution_reference_asset_refs'] = ['mockup-01.dat']
        self.save()
        self.assert_blocked('visual_gate_status=proof_confirmed or not_applicable')

    def test_proof_confirmed_requires_distinct_mockup_and_proof_assets(self):
        self.enable_visual_gate('proof_confirmed')
        self.files['mockup-01.dat'] = 'Synthetic aesthetic mockup bytes.\n'
        self.files['proof-01.dat'] = 'Synthetic executable proof bytes.\n'
        self.files['project.json'].update(
            visual_mockup_ref='mockup-01.dat', visual_proof_ref='proof-01.dat',
            execution_reference_asset_refs=['mockup-01.dat', 'proof-01.dat', 'capability-map.json'])
        self.save()
        report = validate(self.root)
        self.assertEqual(report['status'], 'pass', report['errors'])
        self.assertTrue(compile_manifest(self.root)['render_allowed'])

    def test_proof_confirmed_rejects_byte_identical_copy(self):
        self.enable_visual_gate('proof_confirmed')
        self.files['mockup-01.dat'] = 'same bytes\n'
        self.files['proof-01.dat'] = 'same bytes\n'
        self.files['project.json'].update(
            visual_mockup_ref='mockup-01.dat', visual_proof_ref='proof-01.dat',
            execution_reference_asset_refs=['mockup-01.dat', 'proof-01.dat', 'capability-map.json'])
        self.save()
        self.assert_blocked('visual mockup/proof reuse requires')

    def test_engineered_mockup_can_be_reused_as_proof_with_bound_evidence(self):
        self.enable_visual_gate('proof_confirmed')
        self.files['mockup-01.dat'] = 'same engineered bytes\n'
        self.files['proof-01.dat'] = 'same engineered bytes\n'
        self.files['engineering-receipt.json'] = {'renderer': 'synthetic-final-toolchain', 'status': 'pass'}
        self.files['project.json'].update(
            visual_mockup_ref='mockup-01.dat', visual_proof_ref='proof-01.dat',
            visual_proof_reuse={
                'mode': 'reuse_engineered_mockup',
                'mockup_ref': 'mockup-01.dat',
                'proof_ref': 'proof-01.dat',
                'reason': 'Mockup was already rendered by the declared final execution toolchain.',
                'engineering_evidence_refs': ['engineering-receipt.json']},
            execution_reference_asset_refs=['mockup-01.dat', 'proof-01.dat', 'engineering-receipt.json', 'capability-map.json'])
        self.save()
        report = validate(self.root)
        self.assertEqual(report['status'], 'pass', report['errors'])
        self.assertTrue(compile_manifest(self.root)['render_allowed'])

    def test_mockup_proof_reuse_without_engineering_evidence_is_blocked(self):
        self.enable_visual_gate('proof_confirmed')
        self.files['mockup-01.dat'] = 'same engineered bytes\n'
        self.files['proof-01.dat'] = 'same engineered bytes\n'
        self.files['project.json'].update(
            visual_mockup_ref='mockup-01.dat', visual_proof_ref='proof-01.dat',
            visual_proof_reuse={
                'mode': 'reuse_engineered_mockup',
                'mockup_ref': 'mockup-01.dat',
                'proof_ref': 'proof-01.dat',
                'reason': 'Claims final toolchain reuse but provides no evidence refs.',
                'engineering_evidence_refs': []},
            execution_reference_asset_refs=['mockup-01.dat', 'proof-01.dat', 'capability-map.json'])
        self.save()
        self.assert_blocked('visual_proof_reuse requires engineering_evidence_refs')

    def test_proof_confirmed_requires_capability_map_entrypoint(self):
        self.enable_visual_gate('proof_confirmed')
        self.files['mockup-01.dat'] = 'mockup bytes\n'
        self.files['proof-01.dat'] = 'proof bytes\n'
        self.files['project.json'].update(
            visual_mockup_ref='mockup-01.dat', visual_proof_ref='proof-01.dat',
            execution_reference_asset_refs=['mockup-01.dat', 'proof-01.dat', 'capability-map.json'])
        self.files.pop('capability-map.json', None)
        self.save()
        self.assert_blocked('proof_confirmed requires capability-map.json')

    def test_proof_asset_change_invalidates_confirmation(self):
        self.enable_visual_gate('proof_confirmed')
        self.files['mockup-01.dat'] = 'Synthetic aesthetic mockup bytes.\n'
        self.files['proof-01.dat'] = 'Synthetic executable proof bytes.\n'
        self.files['project.json'].update(
            visual_mockup_ref='mockup-01.dat', visual_proof_ref='proof-01.dat',
            execution_reference_asset_refs=['mockup-01.dat', 'proof-01.dat', 'capability-map.json'])
        self.save()
        manifest = compile_manifest(self.root)
        (self.root / 'proof-01.dat').write_text('Changed synthetic proof bytes.\n')
        self.assert_blocked('reference assets changed since confirmation')
        with self.assertRaises(ValueError):
            check(self.root, manifest)

    def test_capability_map_change_invalidates_confirmation(self):
        self.enable_visual_gate('proof_confirmed')
        self.files['mockup-01.dat'] = 'Synthetic aesthetic mockup bytes.\n'
        self.files['proof-01.dat'] = 'Synthetic executable proof bytes.\n'
        self.files['project.json'].update(
            visual_mockup_ref='mockup-01.dat', visual_proof_ref='proof-01.dat',
            execution_reference_asset_refs=['mockup-01.dat', 'proof-01.dat', 'capability-map.json'])
        self.save()
        manifest = compile_manifest(self.root)
        capability = json.loads((self.root / 'capability-map.json').read_text())
        capability['capabilities'][0]['entrypoint'] = 'changed_renderer.py'
        (self.root / 'capability-map.json').write_text(json.dumps(capability))
        self.assert_blocked('reference assets changed since confirmation')
        with self.assertRaises(ValueError):
            check(self.root, manifest)

    def test_proof_confirmed_requires_capability_that_outputs_the_declared_proof(self):
        self.enable_visual_gate('proof_confirmed')
        self.files['mockup-01.dat'] = 'mockup bytes\n'
        self.files['proof-01.dat'] = 'proof bytes\n'
        self.files['project.json'].update(
            visual_mockup_ref='mockup-01.dat', visual_proof_ref='proof-01.dat',
            execution_reference_asset_refs=['mockup-01.dat', 'proof-01.dat', 'capability-map.json'])
        self.files['capability-map.json'] = {
            'schema_version': '1.0', 'capabilities': [{
                'capability': 'inspect_media', 'actual_tool': 'python3',
                'entrypoint': 'sources.json', 'status': 'available',
                'output_mapping': {'metadata': 'sources.json'}}]}
        self.save()
        self.assert_blocked('output_mapping produces visual_proof_ref')

    def test_capability_map_top_level_array_reports_format_error(self):
        self.enable_visual_gate('proof_confirmed')
        self.files['mockup-01.dat'] = 'mockup bytes\n'
        self.files['proof-01.dat'] = 'proof bytes\n'
        self.files['project.json'].update(
            visual_mockup_ref='mockup-01.dat', visual_proof_ref='proof-01.dat',
            execution_reference_asset_refs=['mockup-01.dat', 'proof-01.dat', 'capability-map.json'])
        self.files['capability-map.json'] = []
        self.save()
        self.assert_blocked('capability-map.json must be an object')

    def _assert_bad_project_schema(self, bad):
        self.files['project.json']['schema_version'] = bad
        for key in ('visual_gate_status', 'visual_mockup_ref', 'visual_proof_ref'):
            self.files['project.json'].pop(key, None)
        self.save()
        report = validate(self.root)
        self.assertEqual(report['status'], 'fail')
        self.assertTrue(any('project.schema_version must use dotted numeric format' in e
                            for e in report['errors']), report['errors'])

    def test_v_prefixed_project_schema_is_rejected(self):
        self._assert_bad_project_schema('v1.8')

    def test_prerelease_project_schema_is_rejected(self):
        self._assert_bad_project_schema('1.8-rc1')

    def test_missing_exception_reason_is_not_silently_accepted(self):
        self.files['structure-exceptions.jsonl'][0]['reason'] = ''
        self.save()
        self.assert_blocked('reason must be explicit')

    def test_unknown_keyframe_time_is_null_and_does_not_stop_independent_work(self):
        self.files['keyframe-references.json'][0]['timestamp_ms'] = None
        self.save()
        self.assertEqual(validate(self.root)['status'], 'pass')

    def test_empty_keyframe_list_requires_an_artifact_exception(self):
        self.files['keyframe-references.json'] = []
        self.save()
        self.assert_blocked('empty keyframe references')
        self.files['structure-exceptions.jsonl'][0].update(record_id=None, field='*')
        self.save()
        self.assertEqual(validate(self.root)['status'], 'pass')

    def test_exception_does_not_release_unverified_adopted_evidence(self):
        self.files['deep-observations.csv']['rows'][0]['evidence_status'] = 'pending'
        self.save()
        self.assert_blocked('evidence')

    def test_available_keyframe_cannot_point_to_a_nonexistent_image(self):
        self.files['keyframe-references.json'][0].update(status='available', image_ref='missing.png')
        self.save()
        self.assert_blocked('available image file is missing')

    def test_preparation_stays_a_draft_with_reference_dependencies(self):
        auth = prepare(self.root)
        self.assertEqual(auth['status'], 'draft')
        self.assertIsNone(auth['confirmed_by'])
        self.assertTrue(auth['execution_reference_digest'])
        self.assertEqual(auth['execution_reference_asset_digests'], {})

    def available_keyframe(self):
        self.files['keyframe-references.json'][0].update(
            status='available', image_ref='keyframe.pgm')
        self.save()
        # Build a single-pixel PGM image in the temporary test project.
        frame = self.root / 'keyframe.pgm'
        frame.write_bytes(b'P5\n1 1\n255\n\x00')

    def alternate_unit(self):
        source = self.files['sources.json'][0].copy()
        source['source_id'] = 'SRC002'
        self.files['sources.json'].append(source)
        self.files['units.jsonl'].append({
            'unit_id': 'U002', 'source_id': 'SRC002', 'scene_id': 'S002',
            'start_ms': 0, 'end_ms': 8000, 'utterance_ids': [], 'protected_ranges': []})
        self.files['scenes.jsonl'].append({
            'scene_id': 'S002', 'source_ranges': [
                {'source_id': 'SRC002', 'start_ms': 0, 'end_ms': 8000}],
            'facts': ['synthetic alternate scene'], 'unknowns': []})

    def test_available_keyframe_matches_unit_and_existing_frame(self):
        self.available_keyframe()
        self.assertEqual(validate(self.root)['status'], 'pass')
        manifest = compile_manifest(self.root)
        self.assertEqual(check(self.root, manifest)['status'], 'pass')

    def test_nonexistent_keyframe_unit_is_blocked(self):
        self.available_keyframe()
        self.files['keyframe-references.json'][0]['source_segment'] = 'MISSING_UNIT'
        self.save()
        self.assert_blocked('unknown source_segment unit')

    def test_unavailable_keyframe_cannot_reference_a_nonexistent_unit(self):
        self.files['keyframe-references.json'][0]['source_segment'] = 'MISSING_UNIT'
        self.save()
        self.assert_blocked('unknown source_segment unit')

    def test_keyframe_unit_source_must_match(self):
        self.alternate_unit()
        self.files['keyframe-references.json'][0]['source_segment'] = 'U002'
        self.available_keyframe()
        self.assert_blocked('source_segment source mismatch')

    def test_keyframe_time_must_match_reused_frame_id(self):
        self.available_keyframe()
        self.files['keyframe-references.json'][0]['timestamp_ms'] = 1100
        self.save()
        self.assert_blocked('timestamp_ms must match existing frame')

    def test_unavailable_keyframe_keeps_known_frame_time_consistent(self):
        self.files['keyframe-references.json'][0]['timestamp_ms'] = 1100
        self.save()
        self.assert_blocked('timestamp_ms must match existing frame')

    def test_keyframe_source_must_match_reused_frame_id(self):
        self.alternate_unit()
        self.files['keyframe-references.json'][0].update(
            source_segment='U002', source_id='SRC002')
        self.available_keyframe()
        self.assert_blocked('source_id must match existing frame')

    def test_keyframe_time_must_be_inside_its_unit(self):
        self.available_keyframe()
        self.files['keyframe-references.json'][0].update(
            frame_id='NEW_FRAME', timestamp_ms=8000)
        self.save()
        self.assert_blocked('timestamp_ms is outside source_segment')

    def test_new_keyframe_id_inside_known_unit_remains_allowed(self):
        self.available_keyframe()
        self.files['keyframe-references.json'][0].update(
            frame_id='NEW_FRAME', timestamp_ms=2000)
        self.save()
        self.assertEqual(validate(self.root)['status'], 'pass')

    def test_overwritten_keyframe_image_invalidates_old_render_entry(self):
        self.available_keyframe()
        manifest = compile_manifest(self.root)
        image = self.root / 'keyframe.pgm'
        image.write_bytes(image.read_bytes() + b'changed-synthetic-image-bytes')
        self.assertEqual(validate(self.root)['status'], 'pass')
        with self.assertRaisesRegex(ValueError, 'inputs changed'):
            check(self.root, manifest)
        self.assertNotEqual(compile_manifest(self.root)['input_digest'], manifest['input_digest'])

    def test_unavailable_keyframe_requires_exception_file(self):
        (self.root / 'structure-exceptions.jsonl').unlink()
        self.assert_blocked('unavailable requires a matching exception declaration')

    def test_unavailable_keyframe_exception_must_match_record(self):
        self.files['structure-exceptions.jsonl'][0]['record_id'] = 'OTHER_FRAME'
        self.save()
        self.assert_blocked('unavailable requires a matching exception declaration')

    def test_unavailable_keyframe_exception_must_match_field(self):
        self.files['structure-exceptions.jsonl'][0]['field'] = 'narrative_role'
        self.save()
        self.assert_blocked('unavailable requires a matching exception declaration')

    def test_unavailable_keyframe_exception_must_match_status(self):
        self.files['structure-exceptions.jsonl'][0]['status'] = 'partial'
        self.save()
        self.assert_blocked('unavailable requires a matching exception declaration')

    def test_unavailable_keyframe_accepts_explicit_artifact_exception(self):
        self.files['structure-exceptions.jsonl'][0].update(record_id=None, field='*')
        self.save()
        self.assertEqual(validate(self.root)['status'], 'pass')


if __name__ == '__main__':
    unittest.main()
