"""v1.1.0 Detail gates: early lint, stable question IDs, one closure ledger."""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / 'scripts'))

from _synthetic_project import copy_synthetic_ready

from validate_project import validate  # noqa: E402
from compile_render_manifest import compile_manifest  # noqa: E402

LEDGER_HEAD = ('### Question Closure Ledger\n\n| question_id | status | plan_node_id | 处理方式 | confirmed_by |\n'
               '|---|---|---|---|---|\n')


def write_fixture(root, files):
    for name, data in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if name.endswith('.csv'):
            with path.open('w', encoding='utf-8', newline='') as fh:
                writer = csv.DictWriter(fh, fieldnames=data['headers'])
                writer.writeheader(); writer.writerows(data['rows'])
        elif name.endswith('.jsonl'):
            path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in data), encoding='utf-8')
        elif name.endswith('.json'):
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        else:
            path.write_text(data, encoding='utf-8')


class GateBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.files = json.loads((PACKAGE / 'tests/fixtures/ready-project.json').read_text(encoding='utf-8'))
        write_fixture(self.root, self.files)

    def errors(self):
        return validate(self.root)['errors']

    def assert_error(self, fragment):
        errors = self.errors()
        self.assertTrue(any(fragment in e for e in errors), errors)

    def assert_no_error(self, fragment):
        errors = self.errors()
        self.assertFalse(any(fragment in e for e in errors), errors)

    def edit_csv(self, name, fn):
        path = self.root / name
        with path.open('r', encoding='utf-8-sig', newline='') as fh:
            reader = csv.DictReader(fh); headers = reader.fieldnames; rows = list(reader)
        fn(rows)
        with path.open('w', encoding='utf-8', newline='') as fh:
            writer = csv.DictWriter(fh, fieldnames=headers); writer.writeheader(); writer.writerows(rows)

    def set_question(self, **values):
        self.edit_csv('structure-questions.csv', lambda rows: rows[0].update(values))

    def edit_project(self, **values):
        path = self.root / 'project.json'
        project = json.loads(path.read_text(encoding='utf-8'))
        project.update(values)
        path.write_text(json.dumps(project, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def write_ledger(self, row):
        (self.root / 'execution-handoff.md').write_text('# Handoff\n\n' + LEDGER_HEAD + row + '\n', encoding='utf-8')
        self.edit_project(execution_handoff_ref='execution-handoff.md')


class DraftLintTests(GateBase):
    def setUp(self):
        super().setUp()
        path = self.root / 'project.json'
        project = json.loads(path.read_text(encoding='utf-8'))
        project['structure_state']['directed_deep_pass'] = 'in_progress'
        path.write_text(json.dumps(project, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def test_clean_in_progress_detail_has_no_draft_errors(self):
        self.assertFalse([e for e in self.errors() if e.startswith('detail draft:')])

    def test_observation_outside_interval_is_reported_before_completion(self):
        self.edit_csv('deep-observations.csv', lambda rows: rows[0].update(end_ms='9000'))
        self.assert_error('detail draft: deep-observations.csv row 2: range must stay inside detail interval DI001')

    def test_free_text_target_question_is_reported_while_writing(self):
        self.edit_csv('detail-intervals.csv', lambda rows: rows[0].update(target_questions='这里是否发生喂食？'))
        self.assert_error('write stable IDs, not free text')

    def test_bad_enum_and_duplicate_id_are_reported(self):
        def fn(rows):
            rows[0]['evidence_status'] = 'verified'
            rows.append(dict(rows[0]))
        self.edit_csv('deep-observations.csv', fn)
        self.assert_error('invalid evidence_status')
        self.assert_error('duplicate observation_id DO001')

    def test_boundary_order_is_checked_while_writing(self):
        self.edit_csv('edit-boundaries.csv', lambda rows: rows[0].update(preferred_in_ms=rows[0]['safe_in_start_ms'],
                                                                        safe_in_start_ms=str(int(rows[0]['safe_in_start_ms']) + 1)))
        self.assert_error('detail draft: edit-boundaries.csv row 2: expected safe_in_start')


class ClosureTests(GateBase):
    def test_fixture_passes_closure_gates(self):
        self.assert_no_error('question')

    def test_free_text_target_question_blocks_completed_detail(self):
        self.edit_csv('detail-intervals.csv', lambda rows: rows[0].update(target_questions='这里是否发生喂食？'))
        self.assert_error('free-text questions must be migrated to stable IDs')

    def test_target_question_must_be_answered_by_an_observation(self):
        self.edit_csv('deep-observations.csv', lambda rows: rows[0].update(question_refs='none'))
        self.assert_error('target question Q001 is not answered by any deep observation')

    def test_question_bound_to_interval_must_be_in_its_target_list(self):
        def fn(rows):
            extra = dict(rows[0]); extra.update(question_id='Q002', answer_status='contradicted')
            rows.append(extra)
        self.edit_csv('structure-questions.csv', fn)
        self.assert_error("Q002: question declares detail_interval_id=DI001 but is missing")
        self.assert_error('selected plan node P01 uses contradicted question Q002')

    def test_unresolved_question_needs_concrete_gap_and_ledger(self):
        self.set_question(answer_status='unresolved', unverified_items='none', next_check='none')
        self.assert_error('Q001: unresolved target question needs a concrete evidence gap')
        self.assert_error('must be listed in the execution handoff Question Closure Ledger')

    def test_unresolved_question_on_selected_node_blocks_render_even_when_listed(self):
        self.set_question(answer_status='unresolved', unverified_items='hand direction between frames',
                          next_check='frame strip 1216000-1217000')
        self.write_ledger('| Q001 | unresolved | P01 | 不进入成片，待补逐帧条 | director |')
        self.assert_error('selected plan node P01 still has unresolved question Q001')

    def test_contradicted_question_on_selected_node_needs_confirmed_by(self):
        self.set_question(answer_status='contradicted', answer='共同试吃，不是喂食')
        self.write_ledger('| Q001 | contradicted | P01 | 按"共同试吃"改写该节点 |  |')
        self.assert_error('uses contradicted question Q001 without a confirmed_by entry')

    def test_confirmed_ledger_row_closes_contradicted_question(self):
        self.set_question(answer_status='contradicted', answer='共同试吃，不是喂食')
        self.write_ledger('| Q001 | contradicted | P01 | 按"共同试吃"改写该节点 | 导演 2026-10-05 |')
        self.assert_no_error('Q001')

    def test_ledger_status_must_match_and_handling_must_be_concrete(self):
        self.set_question(answer_status='contradicted', answer='共同试吃，不是喂食')
        self.write_ledger('| Q001 | unresolved | P01 | resolved | director |')
        self.assert_error("ledger status 'unresolved' does not match")
        self.assert_error('ledger row needs a concrete downstream handling')


class RenderClosureTests(GateBase):
    """Exercise closure with an otherwise fully valid, authorized render project."""
    def setUp(self):
        super().setUp()
        copy_synthetic_ready(self.root)
        self.assertEqual(validate(self.root)['status'], 'pass')

    def blocked(self, fragment):
        self.assert_error(fragment)
        with self.assertRaises(ValueError):
            compile_manifest(self.root)

    def test_unresolved_cannot_hide_behind_wrong_or_placeholder_node(self):
        for plan in ('P99', 'none', ''):
            with self.subTest(plan=plan):
                self.set_question(stage='broad', detail_interval_id='none', plan_node_id=plan,
                                  answer_status='unresolved', unverified_items='need continuous footage',
                                  next_check='review full opportunity window')
                self.write_ledger('| Q001 | unresolved | P01 | 待连续复核后决定 |  |')
                self.blocked('selected plan node P01 still has unresolved question Q001')

    def test_contradicted_cannot_hide_behind_wrong_node(self):
        self.set_question(answer_status='contradicted', plan_node_id='P99')
        self.write_ledger('| Q001 | contradicted | P01 | 待重新确认 |  |')
        self.blocked('selected plan node P01 uses contradicted question Q001')

    def test_duplicate_question_cannot_replace_an_unresolved_answer(self):
        def change(rows):
            supported = dict(rows[0])
            rows[0].update(answer_status='unresolved', unverified_items='missing continuous review',
                           next_check='review full interval')
            rows.append(supported)
        self.edit_csv('structure-questions.csv', change)
        self.write_ledger('| Q001 | unresolved | P01 | 待补证据 |  |')
        self.blocked('duplicate question_id Q001')

    def test_ledger_confirmation_must_apply_to_the_linked_node(self):
        self.set_question(answer_status='contradicted')
        self.write_ledger('| Q001 | contradicted | P99 | 改写其他节点 | 导演甲 |')
        self.blocked('ledger plan_node_id must match linked detail nodes')

    def test_duplicate_or_outside_ledger_rows_cannot_supply_confirmation(self):
        self.set_question(answer_status='contradicted')
        confirmed = '| Q001 | contradicted | P01 | 按核实结果改写 | 导演甲 |'
        self.write_ledger('| Q001 | contradicted | P01 | 待确认 |  |\n' + confirmed)
        self.blocked('duplicate question_id in Question Closure Ledger')
        self.write_ledger('\n### Other table\n\n' + confirmed)
        self.blocked('question is missing from the handoff Question Closure Ledger')

    def test_question_source_and_interval_bindings_must_match(self):
        self.set_question(source_id='SRC999')
        self.blocked('source_id differs from linked detail interval DI001')
        self.set_question(source_id='SRC001', detail_interval_id='DI999')
        self.blocked('unknown detail_interval_id DI999')

    def test_valid_broad_question_and_confirmed_ledger_still_compile(self):
        self.set_question(stage='broad', detail_interval_id='none', plan_node_id='none')
        self.assertTrue(compile_manifest(self.root)['render_allowed'])
        self.set_question(answer_status='contradicted')
        self.write_ledger('| Q001 | contradicted | P01 | 按核实结果改写该节点 | 导演甲 |')
        self.assertTrue(compile_manifest(self.root)['render_allowed'])


class LedgerHeadingAndMigrationTests(GateBase):
    """Second review round: localized ledger headings, a clear hint, documented consistency rules."""
    def setUp(self):
        super().setUp()
        copy_synthetic_ready(self.root)
        self.assertEqual(validate(self.root)['status'], 'pass')
        self.set_question(answer_status='contradicted', answer='共同试吃，不是喂食')

    def write_handoff(self, heading):
        row = '| Q001 | contradicted | P01 | 按“共同试吃”改写该节点 | 导演甲 |'
        (self.root / 'execution-handoff.md').write_text(
            '# Handoff\n\n%s\n\n| question_id | status | plan_node_id | 处理方式 | confirmed_by |\n'
            '|---|---|---|---|---|\n%s\n' % (heading, row), encoding='utf-8')
        self.edit_project(execution_handoff_ref='execution-handoff.md')

    def test_heading_with_chinese_note_is_accepted(self):
        self.write_handoff('### Question Closure Ledger（问题闭环清单）')
        self.assert_no_error('Q001')
        self.assertTrue(compile_manifest(self.root)['render_allowed'])

    def test_chinese_only_heading_is_accepted(self):
        self.write_handoff('### 问题闭环清单')
        self.assert_no_error('Q001')

    def test_missing_ledger_heading_explains_what_is_expected(self):
        self.write_handoff('### 其他说明')
        self.assert_error('execution handoff has no Question Closure Ledger section')
        self.assert_error('Q001: contradicted question is missing from the handoff Question Closure Ledger')

    def test_observation_node_must_match_its_interval(self):
        # Documented v1.0.7 -> v1.1.0 migration rule, not only the question-ID rule.
        self.edit_csv('deep-observations.csv', lambda rows: rows[0].update(plan_node_id='P02'))
        self.assert_error('DO001: plan_node_id differs from its detail interval DI001')


if __name__ == '__main__':
    unittest.main()
