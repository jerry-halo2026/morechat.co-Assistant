#!/usr/bin/env python3
"""Two small Detail gates added in v1.1.0.

1. lint_detail_draft: while Detail is still in progress, check the Detail files
   that already exist (headers, IDs, ranges, references, enums) so mistakes show
   up when a row is written, not at the final gate.
2. check_question_closure: once Detail is complete, every target question uses a
   stable question ID, is answered by at least one observation, and every
   contradicted / unresolved question is listed in the handoff Question Closure
   Ledger - the single human-visible closure record. At ready_for_render, a
   selected plan node may not carry an unresolved question, and a contradicted
   one needs a named human confirmation in that ledger.
"""
import csv
from pathlib import Path

PLACEHOLDERS = {'', 'none', 'unknown', 'not_applicable', 'n/a', 'na', 'tbd', 'pending', '-', '待定', '无'}
EVIDENCE_STATUSES = {'pending', 'supported', 'contradicted', 'partial'}
BOUNDARY_STATUSES = {'pending', 'supported', 'partial', 'contradicted'}
CONTINUITY_TYPES = {'dialogue', 'action', 'reaction', 'music', 'scene', 'mixed'}
SPEAKER_DECISIONS = {'resolved', 'supported', 'partial', 'unresolved', 'contradicted', 'not_applicable'}
OPEN_STATUSES = {'unresolved', 'contradicted'}
TEMPLATES = {
    'detail-intervals.csv': 'detail-interval-template.csv',
    'deep-observations.csv': 'deep-observation-template.csv',
    'speaker-adjudications.csv': 'speaker-adjudication-template.csv',
    'edit-boundaries.csv': 'edit-boundary-template.csv',
}
ASSETS = Path(__file__).resolve().parents[1] / 'assets'


def read_csv(path):
    if not path.is_file():
        return None, []
    with path.open('r', encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


def text(row, key):
    value = row.get(key)
    return value.strip() if isinstance(value, str) else ''


def is_placeholder(value):
    return (value or '').strip().lower() in PLACEHOLDERS


def refs(value):
    raw = (value or '').strip()
    if raw.lower() in ('', 'none', 'unknown', 'not_applicable'):
        return []
    return [part.strip() for part in raw.split(';') if part.strip()]


def to_ms(value):
    try:
        return int((value or '').strip())
    except (ValueError, AttributeError):
        return None


def question_index(root, errors=None):
    _, rows = read_csv(root / 'structure-questions.csv')
    result = {}
    for row in rows:
        qid = text(row, 'question_id')
        if qid in result:
            if errors is not None:
                errors.append('structure-questions.csv: duplicate question_id %s' % qid)
        elif qid:
            result[qid] = row
    return result


def lint_detail_draft(root, sources):
    """Structural checks on Detail files that exist; completeness is left to the final gate."""
    errors = []
    tables = {}
    for name, template in TEMPLATES.items():
        headers, rows = read_csv(root / name)
        if headers is None:
            continue
        expected, _ = read_csv(ASSETS / template)
        missing = [h for h in (expected or []) if h not in headers]
        if missing:
            errors.append('%s: missing template columns %s' % (name, ', '.join(missing)))
        tables[name] = rows
    questions = question_index(root)

    def check_ids(name, key):
        seen = set()
        for number, row in enumerate(tables.get(name, []), start=2):
            value = text(row, key)
            if not value:
                errors.append('%s row %d: %s must be explicit' % (name, number, key))
            elif value in seen:
                errors.append('%s row %d: duplicate %s %s' % (name, number, key, value))
            seen.add(value)

    def check_range(name, number, row):
        sid, a, b = text(row, 'source_id'), to_ms(row.get('start_ms')), to_ms(row.get('end_ms'))
        if sid not in sources:
            errors.append('%s row %d: unknown source_id %s' % (name, number, sid or '(blank)'))
        if a is None or b is None or not a < b:
            errors.append('%s row %d: start_ms/end_ms must be integers with start < end' % (name, number))
            return None
        duration = sources.get(sid, {}).get('duration_ms') if sid in sources else None
        if isinstance(duration, int) and b > duration:
            errors.append('%s row %d: range ends after source duration' % (name, number))
        return a, b

    check_ids('detail-intervals.csv', 'detail_interval_id')
    intervals = {}
    for number, row in enumerate(tables.get('detail-intervals.csv', []), start=2):
        span = check_range('detail-intervals.csv', number, row)
        intervals[text(row, 'detail_interval_id')] = (row, span)
        for qid in refs(row.get('target_questions')):
            if qid not in questions:
                errors.append('detail-intervals.csv row %d: target question %r is not a question_id in '
                              'structure-questions.csv (write stable IDs, not free text)' % (number, qid))

    def inside_interval(name, number, row, span):
        di = text(row, 'detail_interval_id')
        if di not in intervals:
            errors.append('%s row %d: unknown detail_interval_id %s' % (name, number, di or '(blank)'))
            return
        di_row, di_span = intervals[di]
        if text(di_row, 'source_id') != text(row, 'source_id'):
            errors.append('%s row %d: source_id differs from its detail interval' % (name, number))
        if span and di_span and not (di_span[0] <= span[0] and span[1] <= di_span[1]):
            errors.append('%s row %d: range must stay inside detail interval %s' % (name, number, di))

    check_ids('deep-observations.csv', 'observation_id')
    for number, row in enumerate(tables.get('deep-observations.csv', []), start=2):
        inside_interval('deep-observations.csv', number, row, check_range('deep-observations.csv', number, row))
        if text(row, 'evidence_status') not in EVIDENCE_STATUSES:
            errors.append('deep-observations.csv row %d: invalid evidence_status' % number)
        for qid in refs(row.get('question_refs')):
            if qid not in questions:
                errors.append('deep-observations.csv row %d: unknown question_ref %s' % (number, qid))

    check_ids('speaker-adjudications.csv', 'adjudication_id')
    for number, row in enumerate(tables.get('speaker-adjudications.csv', []), start=2):
        check_range('speaker-adjudications.csv', number, row)
        if text(row, 'decision') not in SPEAKER_DECISIONS:
            errors.append('speaker-adjudications.csv row %d: invalid decision' % number)

    check_ids('edit-boundaries.csv', 'boundary_id')
    for number, row in enumerate(tables.get('edit-boundaries.csv', []), start=2):
        name = 'edit-boundaries.csv'
        if text(row, 'boundary_status') not in BOUNDARY_STATUSES:
            errors.append('%s row %d: invalid boundary_status' % (name, number))
        if text(row, 'continuity_type') not in CONTINUITY_TYPES:
            errors.append('%s row %d: invalid continuity_type' % (name, number))
        keys = ('safe_in_start_ms', 'preferred_in_ms', 'safe_in_end_ms', 'safe_out_start_ms',
                'preferred_out_ms', 'safe_out_end_ms')
        values = [to_ms(row.get(k)) for k in keys]
        if all(v is not None for v in values):
            s0, pin, s1, o0, pout, o1 = values
            if not (s0 <= pin < s1 <= o0 <= pout <= o1):
                errors.append('%s row %d: expected safe_in_start <= preferred_in < safe_in_end <= '
                              'safe_out_start <= preferred_out <= safe_out_end' % (name, number))
            inside_interval(name, number, row, (s0, o1))
        elif text(row, 'detail_interval_id') not in intervals:
            errors.append('%s row %d: unknown detail_interval_id' % (name, number))
    return ['detail draft: ' + e for e in errors]


LEDGER_HEADING_KEYS = ('question closure ledger', '问题闭环')


def is_ledger_heading(title):
    """A heading such as 'Question Closure Ledger', 'Question Closure Ledger（问题闭环清单）' or '问题闭环清单'."""
    title = title.lower()
    return any(key in title for key in LEDGER_HEADING_KEYS)


def parse_ledger(path, known_ids, errors=None):
    """Return (rows, has_section) for the handoff Question Closure Ledger, or None if the file is missing.

    Rows: | question_id | status | plan_node_id | handling | confirmed_by |. Only tables under a
    heading that contains 'Question Closure Ledger' or '问题闭环' count; rows elsewhere never confirm.
    """
    rows = {}
    if not path.is_file():
        return None
    active = has_section = False
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line.startswith('#'):
            active = is_ledger_heading(line.lstrip('#').strip())
            has_section = has_section or active
            continue
        if not active or not line.startswith('|'):
            continue
        cells = [c.strip().strip('`') for c in line.strip('|').split('|')]
        if cells and cells[0] in known_ids:
            if cells[0] in rows:
                if errors is not None:
                    errors.append('%s: duplicate question_id in Question Closure Ledger' % cells[0])
                continue
            cells += [''] * (5 - len(cells))
            rows[cells[0]] = {'status': cells[1], 'plan_node_id': cells[2],
                              'handling': cells[3], 'confirmed_by': cells[4]}
    return rows, has_section


def check_question_closure(root, project, detail_index, deep_index, events, ready):
    errors = []
    questions = question_index(root, errors)
    targets_by_di = {}
    question_intervals = {}
    for di, row in detail_index.items():
        targets = refs(row.get('target_questions'))
        targets_by_di[di] = targets
        for qid in targets:
            if qid not in questions:
                errors.append('%s: target question %r is not a question_id in structure-questions.csv; '
                               'free-text questions must be migrated to stable IDs' % (di, qid))
            else:
                question_intervals.setdefault(qid, set()).add(di)
    for qid, q in questions.items():
        di = text(q, 'detail_interval_id')
        if di in detail_index and qid not in targets_by_di.get(di, []):
            errors.append('%s: question declares detail_interval_id=%s but is missing from that '
                           'interval\'s target_questions' % (qid, di))
        if di in detail_index:
            question_intervals.setdefault(qid, set()).add(di)
        elif not is_placeholder(di):
            errors.append('%s: unknown detail_interval_id %s' % (qid, di))

    linked = {}
    for oid, row in deep_index.items():
        di = text(row, 'detail_interval_id')
        if di in detail_index and text(row, 'plan_node_id') != text(detail_index[di], 'plan_node_id'):
            errors.append('%s: plan_node_id differs from its detail interval %s' % (oid, di))
        for qid in refs(row.get('question_refs')):
            linked.setdefault((di, qid), []).append(oid)
            if qid not in questions:
                errors.append('%s: unknown question_ref %s' % (oid, qid))
            elif di in detail_index:
                question_intervals.setdefault(qid, set()).add(di)
    in_scope = {qid: questions[qid] for qid in question_intervals}
    question_plans = {}
    for qid, intervals in question_intervals.items():
        q = questions[qid]
        for di in sorted(intervals):
            detail = detail_index[di]
            question_plans.setdefault(qid, set()).add(text(detail, 'plan_node_id'))
            declared_di = text(q, 'detail_interval_id')
            if not is_placeholder(declared_di) and declared_di != di:
                errors.append('%s: declared detail_interval_id differs from linked interval %s' % (qid, di))
            for key in ('source_id', 'plan_node_id'):
                value = text(q, key)
                if not is_placeholder(value) and value != text(detail, key):
                    errors.append('%s: %s differs from linked detail interval %s' % (qid, key, di))
    for di, targets in targets_by_di.items():
        for qid in targets:
            if qid not in questions:
                continue
            if (di, qid) not in linked:
                errors.append('%s: target question %s is not answered by any deep observation '
                              '(question_refs) of this interval' % (di, qid))

    open_questions = {}
    for qid, q in in_scope.items():
        status = text(q, 'answer_status')
        if status == 'unresolved':
            if is_placeholder(q.get('unverified_items')) or is_placeholder(q.get('next_check')):
                errors.append('%s: unresolved target question needs a concrete evidence gap (unverified_items) '
                              'and next_check' % qid)
        if status in OPEN_STATUSES:
            open_questions[qid] = q

    ref = project.get('execution_handoff_ref')
    handoff = root / ref if isinstance(ref, str) and ref.strip() else None
    parsed = parse_ledger(handoff, set(questions), errors) if handoff else None
    ledger, has_section = parsed if parsed is not None else (None, False)
    if open_questions and parsed is not None and not has_section:
        errors.append('execution handoff has no Question Closure Ledger section: put the ledger table under a '
                      'heading that contains "Question Closure Ledger" (a Chinese note such as '
                      '"Question Closure Ledger（问题闭环清单）" or "问题闭环清单" is fine)')
    if open_questions and ledger is None:
        errors.append('contradicted / unresolved target questions %s must be listed in the execution '
                      'handoff Question Closure Ledger; set execution_handoff_ref' % sorted(open_questions))
    ledger = ledger or {}
    if open_questions:
        for qid, q in sorted(open_questions.items()):
            row = ledger.get(qid)
            if row is None:
                if handoff is not None and handoff.is_file():
                    errors.append('%s: %s question is missing from the handoff Question Closure Ledger'
                                  % (qid, text(q, 'answer_status')))
                continue
            if row['status'] != text(q, 'answer_status'):
                errors.append('%s: ledger status %r does not match structure-questions answer_status %r'
                              % (qid, row['status'], text(q, 'answer_status')))
            if set(refs(row['plan_node_id'])) != question_plans[qid]:
                errors.append('%s: ledger plan_node_id must match linked detail nodes %s'
                              % (qid, sorted(question_plans[qid])))
            if is_placeholder(row['handling']) or row['handling'].lower() == 'resolved':
                errors.append('%s: ledger row needs a concrete downstream handling, not %r' % (qid, row['handling']))

    if ready:
        selected = set()
        for event in events:
            if not isinstance(event, dict) or event.get('kind') != 'source':
                continue
            for ref in event.get('deep_observation_refs') or []:
                if isinstance(ref, str) and ref in deep_index:
                    observation = deep_index[ref]
                    detail = detail_index.get(text(observation, 'detail_interval_id'), observation)
                    selected.add(text(detail, 'plan_node_id'))
        for qid, q in sorted(questions.items()):
            plans = question_plans.get(qid, set())
            if not plans and text(q, 'stage').lower() in ('detail', 'e'):
                plans = {text(q, 'plan_node_id')}
            for plan in sorted(plans & selected):
                status = text(q, 'answer_status')
                if status == 'unresolved':
                    errors.append('ready_for_render: selected plan node %s still has unresolved question %s' % (plan, qid))
                elif status == 'contradicted':
                    row = ledger.get(qid)
                    if row is None or is_placeholder(row['confirmed_by']):
                        errors.append('ready_for_render: selected plan node %s uses contradicted question %s without '
                                      'a confirmed_by entry in the handoff Question Closure Ledger' % (plan, qid))
    return errors
