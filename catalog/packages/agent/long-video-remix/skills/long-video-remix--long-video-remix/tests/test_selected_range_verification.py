"""v1.2.4: selected-range verification with D2 snapshot compatibility hardening.

Synthetic fixtures only; these tests validate contracts, not real audio quality.
"""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / 'scripts'))

from _synthetic_project import copy_synthetic_ready

from execution_integrity import digest
from prepare_execution_authorization import prepare
from validate_project import validate


class SelectedRangeVerificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        copy_synthetic_ready(self.root)
        self.assertEqual(validate(self.root)['status'], 'pass')

    def edit_csv(self, name, fn):
        path = self.root / name
        with path.open('r', encoding='utf-8', newline='') as fh:
            reader = csv.DictReader(fh)
            headers, rows = list(reader.fieldnames or []), list(reader)
        fn(rows)
        with path.open('w', encoding='utf-8', newline='') as fh:
            writer = csv.DictWriter(fh, fieldnames=headers)
            writer.writeheader(); writer.writerows(rows)

    def edit_json(self, name, fn):
        path = self.root / name
        data = json.loads(path.read_text(encoding='utf-8'))
        fn(data)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def make_planning_project(self):
        self.edit_json('timeline.json', lambda x: x.update(status='draft'))
        self.edit_json('project.json', lambda x: x.update(render_authorized=False,
                                                           execution_authorization_digest=None))

    def reconfirm(self):
        auth = prepare(self.root)
        auth.update(status='confirmed', confirmed_by='synthetic-test-author',
                    authorization_id='AUTH-SELECTED-RANGE')
        (self.root / 'execution-authorization.json').write_text(
            json.dumps(auth, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        self.edit_json('project.json', lambda x: x.update(execution_authorization_digest=digest(auth)))

    def test_detail_can_finish_with_partial_dialogue_boundary_and_no_precise_audio_tail(self):
        self.make_planning_project()
        self.edit_csv('edit-boundaries.csv', lambda rows: rows[0].update(
            boundary_status='partial', audio_start_ms='unknown', audio_end_ms='unknown',
            audio_tail_end_ms='unknown', boundary_reason='selection-ready envelope; final audio deferred'))
        self.edit_csv('deep-observations.csv', lambda rows: rows[0].update(
            audio_verification_status='subtitle_only', original_audio_keypoints='not_verified',
            dialogue_audio='unknown'))
        report = validate(self.root)
        self.assertEqual(report['status'], 'pass', report['errors'])

    def test_supported_dialogue_boundary_still_requires_precise_audio_values(self):
        self.make_planning_project()
        self.edit_csv('edit-boundaries.csv', lambda rows: rows[0].update(
            boundary_status='supported', audio_start_ms='unknown', audio_end_ms='unknown',
            audio_tail_end_ms='unknown'))
        report = validate(self.root)
        self.assertEqual(report['status'], 'fail')
        self.assertTrue(any('supported dialogue boundary requires audio start/end/tail times' in e
                            for e in report['errors']), report['errors'])

    def test_schema_18_ready_blocks_partial_selected_boundary(self):
        self.edit_csv('edit-boundaries.csv', lambda rows: rows[0].update(boundary_status='partial'))
        report = validate(self.root)
        self.assertEqual(report['status'], 'fail')
        self.assertTrue(any('schema 1.8+ ready_for_render requires selected edit boundary supported after Execute Step 0' in e
                            for e in report['errors']), report['errors'])

    def test_schema_17_keeps_v122_partial_boundary_compatibility(self):
        self.edit_json('project.json', lambda x: x.update(schema_version='1.7'))
        self.edit_csv('edit-boundaries.csv', lambda rows: rows[0].update(boundary_status='partial'))
        self.reconfirm()
        report = validate(self.root)
        self.assertEqual(report['status'], 'pass', report['errors'])

    def test_schema_17_partial_mixed_boundary_still_requires_legacy_action_times(self):
        self.make_planning_project()
        self.edit_json('project.json', lambda x: x.update(schema_version='1.7'))
        self.edit_csv('edit-boundaries.csv', lambda rows: rows[0].update(
            continuity_type='mixed', boundary_status='partial',
            action_start_ms='unknown', action_end_ms='unknown', reaction_or_settle_end_ms='unknown'))
        report = validate(self.root)
        self.assertEqual(report['status'], 'fail')
        self.assertTrue(any('mixed boundary requires action start/end/reaction-settle times' in e
                            for e in report['errors']), report['errors'])

    def test_schema_18_ready_requires_d2_selection_snapshot(self):
        self.edit_json('timeline.json', lambda x: x['events'][0].pop('d2_selection_snapshot', None))
        report = validate(self.root)
        self.assertEqual(report['status'], 'fail')
        self.assertTrue(any('requires d2_selection_snapshot' in e for e in report['errors']), report['errors'])

    def test_step0_extension_requires_d2_permission(self):
        self.edit_json('timeline.json', lambda x: x['events'][0]['d2_selection_snapshot'].update(
            planned_source_in_ms=1100, allowed_adjustments=[]))
        self.reconfirm()
        report = validate(self.root)
        self.assertEqual(report['status'], 'fail')
        self.assertTrue(any('without add_transition_handle permission' in e for e in report['errors']), report['errors'])

    def test_step0_extension_inside_snapshot_window_can_be_authorized(self):
        self.edit_json('timeline.json', lambda x: x['events'][0]['d2_selection_snapshot'].update(
            planned_source_in_ms=1100, allowed_adjustments=['add_transition_handle']))
        self.reconfirm()
        report = validate(self.root)
        self.assertEqual(report['status'], 'pass', report['errors'])
        auth = prepare(self.root)
        self.assertEqual(auth['allowed_adjustments']['E001'], ['add_transition_handle'])

    def test_step0_cannot_widen_snapshotted_safe_windows(self):
        self.edit_csv('edit-boundaries.csv', lambda rows: rows[0].update(safe_in_start_ms='800'))
        self.reconfirm()
        report = validate(self.root)
        self.assertEqual(report['status'], 'fail')
        self.assertTrue(any('safe windows changed after Direct 2 snapshot' in e for e in report['errors']), report['errors'])


if __name__ == '__main__':
    unittest.main()
