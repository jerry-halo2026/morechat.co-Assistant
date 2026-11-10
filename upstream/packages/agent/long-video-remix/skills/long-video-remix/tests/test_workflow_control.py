"""Exercise missed, stale and cross-session decisions using synthetic media records."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / 'scripts'))

from _synthetic_project import copy_synthetic_ready
import workflow_control as wc
from validate_project import validate
from compile_render_manifest import compile_manifest
from prepare_execution_authorization import prepare


class WorkflowControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'project'
        copy_synthetic_ready(self.root)
        self.quote = '测试夹具：用户同意本轮已展示的具体方案。'
        (self.root / 'decisions.md').write_text('# 用户确认\n\n' + self.quote + '\n', encoding='utf-8')
        (self.root / 'spec.md').write_text('# 声音\n\n保留原声，不加配乐。\n\n# 视觉\n\n使用原片留白，不遮人物。\n', encoding='utf-8')
        wc.initialize(self.root)
        project = self.project()
        project['current_stage'] = 'D2'
        project['workflow_control']['audio_choice'] = {'mode': 'no_music', 'description': '保留原声，不加配乐。', 'ref': 'spec.md#声音'}
        project['workflow_control']['visual_spec_refs'] = ['spec.md#视觉']
        self.write(project)

    def tearDown(self):
        self.temp.cleanup()

    def project(self):
        return json.loads((self.root / 'project.json').read_text())

    def write(self, project):
        (self.root / 'project.json').write_text(json.dumps(project, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def approve(self, keys=wc.MANUAL):
        shown = []
        for key in keys:
            for ref in wc.required_shown_refs(self.root, self.project(), key):
                if ref not in shown:
                    shown.append(ref)
        return wc.confirm(self.root, keys, 'user', 'decisions.md#用户确认', self.quote, shown)

    def states(self):
        return {key: row['status'] for key, row in wc.evaluate(self.root).items()}

    def test_initialize_does_not_invent_or_import_confirmations(self):
        self.assertEqual(self.project()['workflow_control']['confirmations'], {})
        self.assertEqual(wc.report(self.root)['next_gate'], 'audio')
        self.assertEqual(wc.report(self.root)['status'], 'open')

    def test_missing_music_blocks_handoff_even_with_old_confirmed_flags(self):
        result = wc.report(self.root, 'execute_handoff')
        self.assertFalse(result['action_allowed'])
        self.assertIn('audio', [row['id'] for row in result['pending_gates']])

    def test_pending_music_does_not_block_independent_mockup_preparation(self):
        self.approve(('direction',))
        self.assertTrue(wc.report(self.root, 'make_mockup')['action_allowed'])
        self.assertTrue(wc.require_action(self.root, 'make_mockup')['action_allowed'])
        self.assertFalse(wc.report(self.root, 'process_audio')['action_allowed'])

    def test_unconfirmed_mockup_blocks_proof(self):
        self.approve(('direction', 'audio'))
        self.assertFalse(wc.report(self.root, 'make_proof')['action_allowed'])
        with self.assertRaises(ValueError):
            self.approve(('proof',))

    def test_visual_confirmation_cannot_be_backfilled_without_shown_artifact(self):
        self.approve(('direction', 'audio', 'mockup'))
        path = self.root / 'decisions.md'
        render_quote = '渲染视频'
        path.write_text(path.read_text() + '\n' + render_quote + '\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'shown-ref'):
            wc.confirm(self.root, ('proof',), 'user', 'decisions.md', render_quote)

    def test_valid_existing_confirmations_survive_another_process(self):
        self.approve()
        command = [sys.executable, str(PACKAGE / 'scripts/workflow_control.py'), 'status', str(self.root)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'clear')
        self.assertFalse(json.loads(result.stdout)['must_surface'])

    def test_all_current_decisions_allow_original_compiler(self):
        self.approve()
        self.assertEqual(validate(self.root)['errors'], [])
        self.assertTrue(compile_manifest(self.root)['render_allowed'])

    def test_compiler_itself_blocks_missing_internal_decisions(self):
        with self.assertRaisesRegex(ValueError, 'workflow_control'):
            compile_manifest(self.root)

    def test_authorization_draft_is_guarded_before_render(self):
        with self.assertRaisesRegex(ValueError, 'Workflow gate'):
            prepare(self.root)
        self.approve()
        self.assertEqual(prepare(self.root)['status'], 'draft')

    def test_first_authorization_can_be_prepared_without_an_existing_authorization(self):
        self.approve()
        (self.root / 'execution-authorization.json').unlink()
        self.assertEqual(prepare(self.root)['status'], 'draft')
        with self.assertRaises(ValueError):
            compile_manifest(self.root)

    def test_audio_change_reopens_audio_but_keeps_visual_confirmations(self):
        self.approve()
        project = self.project()
        project['workflow_control']['audio_choice']['description'] = '改为另一种已提议的声音处理。'
        self.write(project)
        states = self.states()
        self.assertEqual(states['audio'], 'stale')
        self.assertEqual(states['mockup'], 'satisfied')
        self.assertEqual(states['proof'], 'satisfied')

    def test_audio_section_change_does_not_reopen_unrelated_visual_section(self):
        self.approve()
        path = self.root / 'spec.md'
        path.write_text(path.read_text().replace('保留原声，不加配乐。', '修改声音说明。'))
        self.assertEqual(self.states()['audio'], 'stale')
        self.assertEqual(self.states()['mockup'], 'satisfied')

    def test_visual_change_reopens_mockup_and_dependent_proof(self):
        self.approve()
        path = self.root / 'spec.md'
        path.write_text(path.read_text().replace('不遮人物', '修改画面布局'))
        states = self.states()
        self.assertEqual(states['mockup'], 'stale')
        self.assertEqual(states['proof'], 'pending')
        self.assertEqual(states['audio'], 'satisfied')
        self.assertFalse(wc.report(self.root, 'render')['action_allowed'])

    def test_toolchain_change_reopens_proof_only(self):
        self.approve()
        path = self.root / 'capability-map.json'
        data = json.loads(path.read_text())
        for row in data['capabilities']:
            if row.get('entrypoint'):
                row['entrypoint'] += ' --changed'
        path.write_text(json.dumps(data))
        self.assertEqual(self.states()['proof'], 'stale')
        self.assertEqual(self.states()['mockup'], 'satisfied')

    def test_changed_d2_selection_snapshot_reopens_plan(self):
        self.approve()
        path = self.root / 'timeline.json'
        timeline = json.loads(path.read_text())
        event = next(row for row in timeline['events'] if row.get('kind') == 'source')
        event['d2_selection_snapshot']['allowed_adjustments'].append('synthetic new allowance')
        path.write_text(json.dumps(timeline))
        self.assertEqual(self.states()['plan'], 'stale')

    def test_step0_bookkeeping_does_not_reapprove_d2_selection(self):
        project = self.project()
        path = self.root / project['execution_plan_ref']
        text = path.read_text()
        path.write_text(text + '\n## Execute Step 0 · Selected Range Verification\n\npending\n')
        self.approve()
        path.write_text(path.read_text().replace('\npending\n', '\ncompleted within the original allowance\n'))
        self.assertEqual(self.states()['plan'], 'satisfied')

    def test_confirm_rejects_fabricated_excerpt_and_automatic_actor(self):
        before = (self.root / 'project.json').read_bytes()
        for actor, quote in [('user', '并不存在的确认'), ('assistant', self.quote), ('auto', self.quote)]:
            with self.assertRaises(ValueError):
                wc.confirm(self.root, ('audio',), actor, 'decisions.md', quote)
            self.assertEqual((self.root / 'project.json').read_bytes(), before)

    def test_failed_batch_confirmation_is_atomic(self):
        before = (self.root / 'project.json').read_bytes()
        with self.assertRaises(ValueError):
            self.approve(('direction', 'proof'))
        self.assertEqual((self.root / 'project.json').read_bytes(), before)

    def test_deleted_confirmation_source_does_not_leave_gate_satisfied(self):
        self.approve()
        (self.root / 'decisions.md').unlink()
        self.assertEqual(self.states()['audio'], 'pending')
        self.assertFalse(wc.report(self.root, 'render')['action_allowed'])

    def test_confirmation_can_be_rebound_after_old_record_is_invalid(self):
        self.approve()
        project = self.project()
        project['workflow_control']['confirmations']['audio']['confirmation_ref'] = 'missing.md'
        self.write(project)
        self.assertEqual(self.states()['audio'], 'pending')
        self.approve(('audio',))
        self.assertEqual(self.states()['audio'], 'satisfied')

    def test_confirmation_quote_must_be_in_the_referenced_section(self):
        path = self.root / 'decisions.md'
        path.write_text('# Other\n\n' + self.quote + '\n\n# 用户确认\n\n尚未给出确认。\n')
        with self.assertRaises(ValueError):
            self.approve(('audio',))

    def test_handoff_preserves_pending_items_and_unrelated_text(self):
        path = self.root / 'handoff.md'
        original = '# Existing handoff\n\n保留原文与空白。  \n'
        path.write_text(original)
        wc.handoff(self.root, 'handoff.md')
        first = path.read_text()
        self.assertTrue(first.startswith(original))
        self.assertIn('音乐形式与音轨策略确认', first)
        self.assertIn('partial handoff', first)
        self.assertIn('Next-Step Delivery', first)
        self.assertIn('实际随附文件清单', first)
        self.assertIn('源媒体重绑定信息', first)
        self.assertIn('source_signature', first)
        record = self.project()['workflow_control']['last_handoff']
        self.assertEqual(record['stage'], 'D2')
        self.assertEqual(record['ref'], 'handoff.md')
        self.assertEqual(record['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        wc.handoff(self.root, 'handoff.md')
        self.assertEqual(path.read_text(), first)
        self.assertEqual(self.project()['workflow_control']['confirmations'], {})

    def test_forward_advance_requires_handoff_regeneration_after_artifact_change(self):
        self.approve()
        wc.handoff(self.root, 'handoff.md')
        (self.root / 'overview.md').write_text((self.root / 'overview.md').read_text() + '\nchanged after handoff\n')
        with self.assertRaisesRegex(ValueError, 'regenerate handoff'):
            wc.advance(self.root, 'F')

    def test_handoff_cannot_escape_project_or_overwrite_json(self):
        for value in ('../outside.md', 'project.json'):
            with self.assertRaises(ValueError):
                wc.handoff(self.root, value)

    def test_major_block_advance_is_guarded_and_cannot_skip(self):
        with self.assertRaises(ValueError):
            wc.advance(self.root, 'F')
        with self.assertRaises(ValueError):
            wc.advance(self.root, 'G')
        self.approve()
        with self.assertRaisesRegex(ValueError, 'handoff'):
            wc.advance(self.root, 'F')
        wc.handoff(self.root, 'handoff.md')
        self.assertEqual(wc.advance(self.root, 'F')['current_stage'], 'F')
        with self.assertRaises(ValueError):
            wc.advance(self.root, 'D2')
        self.assertEqual(wc.advance(self.root, 'D2', '局部文案调整需返回编导确认。')['current_stage'], 'D2')

    def test_legacy_fixture_preserves_original_validation(self):
        project = self.project()
        del project['workflow_control']
        del project['execution_policy']['workflow_gate_control']
        self.write(project)
        result = validate(self.root)
        self.assertEqual(result['errors'], [])
        self.assertTrue(any('legacy checks only' in row for row in result['warnings']))

    def test_deleting_required_controller_is_not_a_bypass(self):
        project = self.project()
        del project['workflow_control']
        self.write(project)
        self.assertTrue(any('workflow_control' in x for x in validate(self.root)['errors']))

    def test_visual_na_needs_a_real_reason(self):
        project = self.project()
        project['visual_gate_status'] = 'not_applicable'
        self.write(project)
        self.assertEqual(self.states()['mockup'], 'pending')
        project['workflow_control']['visual_not_applicable_reason'] = '本测试不采用额外视觉设计。'
        self.write(project)
        self.assertEqual(self.states()['mockup'], 'not_applicable')
        self.assertEqual(self.states()['proof'], 'not_applicable')

    def test_qa_cannot_pass_from_a_static_report_or_old_render(self):
        self.approve()
        output = self.root / 'synthetic-output.bin'
        output.write_bytes(b'synthetic render placeholder, not real media')
        project = self.project()
        project['workflow_control']['render_output_ref'] = output.name
        self.write(project)
        qa = {'project_id': project['project_id'], 'checks': [{'name': name, 'status': 'pass', 'method': 'synthetic unit-test record', 'evidence': 'not a real playback'} for name in sorted(wc.QA_NAMES)],
            'final_playback_verified': False, 'blocking_issues': [], 'artifact_sha256': hashlib.sha256(output.read_bytes()).hexdigest()}
        (self.root / 'qa.json').write_text(json.dumps(qa))
        self.assertEqual(self.states()['qa'], 'pending')
        qa['final_playback_verified'] = True
        (self.root / 'qa.json').write_text(json.dumps(qa))
        self.assertEqual(self.states()['qa'], 'satisfied')
        output.write_bytes(b'changed synthetic output')
        self.assertEqual(self.states()['qa'], 'pending')

    def test_unknown_action_is_an_error(self):
        with self.assertRaises(ValueError):
            wc.report(self.root, 'just_continue_anyway')


if __name__ == '__main__':
    unittest.main()
