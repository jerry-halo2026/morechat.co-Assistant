#!/usr/bin/env python3
"""Surface existing workflow checkpoints; guard dependent actions, never approve them."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re


PROTOCOL = '1.3'
POLICY = 'required_v4'
LEGACY_PROTOCOL = '1.0'
LEGACY_POLICY = 'required_v1'
COMPLETE = ('complete', 'completed', 'done')
AUDIO_MODES = ('original_only', 'original_with_music', 'replace_music', 'no_music', 'silent', 'custom')
STAGES = ('A', 'B', 'C', 'D1', 'E', 'D2', 'F', 'G')
BLOCK = {'A': 0, 'B': 0, 'C': 0, 'D1': 1, 'E': 2, 'D2': 3, 'F': 4, 'G': 5}
BASE_EXECUTE = ('direction', 'detail_ready', 'audio', 'reference_routing', 'mockup', 'proof', 'plan', 'production_lock')
PHASE_GATES = {
    0: ('source_ready', 'broad_ready'),
    1: ('direction',),
    2: ('direction', 'detail_ready'),
    3: ('audio', 'reference_routing', 'mockup', 'proof', 'plan', 'production_lock'),
    4: ('production_lock', 'selected_ranges', 'authorization', 'render_result'),
    5: ('production_lock', 'qa'),
}
ACTIONS = {
    'broad_handoff': ('source_ready', 'broad_ready'),
    'start_detail': ('source_ready', 'broad_ready', 'direction'),
    'detail_handoff': ('direction', 'detail_ready'),
    'make_mockup': ('direction', 'detail_ready', 'reference_routing'),
    'make_proof': ('direction', 'detail_ready', 'reference_routing', 'mockup'),
    'build_composition': ('direction', 'detail_ready', 'audio', 'reference_routing', 'mockup'),
    'process_audio': ('audio',),
    'execute_handoff': BASE_EXECUTE,
    'authorize': BASE_EXECUTE + ('selected_ranges',),
    'render': BASE_EXECUTE + ('selected_ranges', 'authorization'),
    'qa_start': BASE_EXECUTE + ('selected_ranges', 'authorization', 'render_result'),
    'deliver_complete': BASE_EXECUTE + ('selected_ranges', 'authorization', 'render_result', 'qa'),
}
EXIT_ACTIONS = ('broad_handoff', 'start_detail', 'detail_handoff', 'execute_handoff', 'qa_start', 'deliver_complete')
LABELS = {
    'source_ready': ('素材与时间基准', '补齐来源版本和时间映射；不补造已观察结果。'),
    'broad_ready': ('Broad 正式交付', '完成基础观察层、Content Map 和 coverage，再交 Direct 1。'),
    'direction': ('Direct 1 叙事方向确认', '展示方向与待核问题，绑定本轮或已有的真实确认来源。'),
    'detail_ready': ('Detail 证据与关键帧交付', '补齐最小充分证据、关键帧清单、异常和下游 handoff。'),
    'audio': ('音乐形式与音轨策略确认', '展示具体声音方案并引用已有确认；未决定时主动提出待选项。'),
    'reference_routing': ('Visual Reference Selection', '新项目必须先让 visual/V0–V2 通过正式增强 checker：按视觉问题与结构卡选择 REF/XR/MR 或逐问题说明 no_ref_needed；这是 Mockup 前机器门槛，不新增用户审批 Gate。'),
    'mockup': ('Aesthetic Mockup 确认', '展示可打开的真实关键帧样稿，确认文字与人物/原字幕的关系。'),
    'proof': ('Executable Proof 确认', '展示最终执行工具链生成的 Proof，并确认其可复现效果。'),
    'plan': ('Direct 2 执行包确认', '展示完整执行包、选段快照及允许调整，再记录确认来源。'),
    'selected_ranges': ('Execute Step 0 入选范围精校', '只精校入选片段及 handles；越过 D2 快照时返回 D2。'),
    'authorization': ('最终范围执行授权', '以 Step 0 后实际范围准备并确认原 execution authorization。'),
    'render_result': ('实际渲染产物', '登记实际输出文件；成功计划或日志不算成片。'),
    'qa': ('真实播放与 Reference Compliance', '对当前成片做原有 QA；未实看不填通过。'),
    'method': ('视觉制作方法确认', '展示叙事作用、视觉重点、处理依据、参数、失败情形和动态验证点；记录真实选择。'),
    'composition': ('代表性 Blender Proof 与动态样片确认', '只对 proof_composition_ids 中的最小充分代表性集合交付可编辑工程、连续音画样片及逐项审阅；其余被机器覆盖关系证明的合成在 Execute 后按锁定实现一次性生产。'),
    'production_lock': ('Production Lock', 'Proof / Composition 确认后冻结当前工具链、关键视觉规则、delivery spec、文字与旁白 policy；输入变化只重开受影响锁。'),
}
MANUAL = ('direction', 'audio', 'mockup', 'proof', 'plan')
PRODUCTION_MANUAL = ('method', 'composition')
QA_NAMES = {'Narrative', 'Meaning', 'Context', 'Audio', 'Rhythm', 'Visual',
            'Text', 'Redundancy', 'Source', 'Mobile', 'ReferenceCompliance'}
BEGIN = '<!-- lvr-workflow-checkpoints:start -->'
END = '<!-- lvr-workflow-checkpoints:end -->'
DELIVERY_BEGIN = '<!-- lvr-next-step-delivery:start -->'
DELIVERY_END = '<!-- lvr-next-step-delivery:end -->'

# These are portable project artifacts commonly needed by the next model / machine.
# The list is intentionally broader than any one stage; handoff only records files that
# actually exist, plus explicit project refs. It does not create a new workflow Gate.
PORTABLE_ARTIFACTS = (
    'sources.json', 'coverage.json', 'frames.jsonl', 'frame-observations.csv',
    'action-node-candidates.csv', 'structure-questions.csv', 'transcript.jsonl',
    'scenes.jsonl', 'overview.md', 'content-map.md', 'units.jsonl',
    'detail-intervals.csv', 'deep-observations.csv', 'speaker-adjudications.csv',
    'edit-boundaries.csv', 'reviews.jsonl', 'keyframe-references.json',
    'execution-handoff.md', 'visual-methods.json', 'composition-plan.json',
    'implementation-lock.json', 'execution-plan.md', 'execution-reference.md',
    'capability-map.json', 'delivery-spec.json', 'execution-authorization.json',
    'timeline.json', 'transitions.json', 'render-manifest.json', 'qa.json',
    'render-audit.json', 'method-baseline.json',
)

PROJECT_REF_KEYS = (
    'brief_ref', 'content_map_ref', 'narrative_direction_ref', 'execution_plan_ref',
    'execution_authorization_ref', 'structure_exceptions_ref', 'keyframe_references_ref',
    'execution_handoff_ref', 'execution_reference_ref', 'visual_mockup_ref',
    'visual_proof_ref',
)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def read_json(path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def enabled(project):
    policy = project.get('execution_policy', {})
    return 'workflow_control' in project or (isinstance(policy, dict) and 'workflow_gate_control' in policy)


def contained(root, ref):
    if not isinstance(ref, str) or not ref.strip():
        raise ValueError('A project-relative file reference is required')
    path = Path(ref.split('#', 1)[0])
    root = root.resolve()
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('References must stay inside the project: ' + ref)
    target = (root / path).resolve()
    if target != root and root not in target.parents:
        raise ValueError('Reference escapes project through a symlink: ' + ref)
    return target


def slug(text):
    return re.sub(r'[^\w\s-]', '', text.strip().lower()).replace(' ', '-')


def _markdown_section(data, anchor, ref):
    """Resolve both a heading and its slug to the same section location."""
    start, level = None, None
    selected = []
    for index, line in enumerate(data.decode('utf-8').splitlines(keepends=True)):
        heading = re.match(r'^(#{1,6})\s+(.+?)\s*#*\s*$', line.rstrip())
        if start is None:
            if heading and anchor in (heading[2], slug(heading[2])):
                start, level = index, len(heading[1])
                selected.append(line)
        elif heading and len(heading[1]) <= level:
            break
        else:
            selected.append(line)
    if start is None or not ''.join(selected[1:]).strip():
        raise ValueError('Missing or empty Markdown section: ' + ref)
    return start, ''.join(selected).encode('utf-8')


def artifact_bytes(root, ref):
    """Read an actual file, or one named Markdown section. Missing means pending."""
    path = contained(root, ref)
    if not path.is_file() or not path.stat().st_size:
        raise ValueError('Missing or empty artifact: ' + ref)
    data = path.read_bytes()
    _, separator, anchor = ref.partition('#')
    return _markdown_section(data, anchor, ref)[1] if separator else data


def _same_revision_section(root, ref, previous_ref):
    """Compare resolved file and heading identities without rewriting saved references."""
    if ref == previous_ref:
        return True
    if not isinstance(previous_ref, str) or '#' not in previous_ref:
        return False
    path = contained(root, ref)
    previous_path = contained(root, previous_ref)
    if not previous_path.is_file() or not path.samefile(previous_path):
        return False
    data = path.read_bytes()
    start, _ = _markdown_section(data, ref.partition('#')[2], ref)
    try:
        previous_start, _ = _markdown_section(data, previous_ref.partition('#')[2], previous_ref)
    except ValueError:
        return False
    return start == previous_start


def artifact(root, ref):
    return {'ref': ref, 'sha256': hashlib.sha256(artifact_bytes(root, ref)).hexdigest()}


def _revision_instruction_artifact(root, ref):
    """Revision-only section fingerprint: trailing whitespace is not part of instruction identity."""
    raw = artifact_bytes(root, ref).decode('utf-8')
    normalized = raw.rstrip() + '\n'
    return {'ref': ref, 'sha256': hashlib.sha256(normalized.encode('utf-8')).hexdigest()}


def control(project):
    policy = project.get('execution_policy', {})
    mode = policy.get('workflow_gate_control') if isinstance(policy, dict) else None
    value = project.get('workflow_control')
    if isinstance(value, dict) and value.get('schema_version') in (LEGACY_PROTOCOL, '1.1', '1.2') and mode in (None, LEGACY_POLICY, 'required_v2', 'required_v3'):
        raise ValueError('Run workflow_control.py init to update workflow_control before D2 / Execute')
    if mode != POLICY:
        raise ValueError('D2 / Execute requires execution_policy.workflow_gate_control=' + POLICY)
    if not isinstance(value, dict) or value.get('schema_version') != PROTOCOL:
        raise ValueError('workflow_control must be initialized with schema_version=' + PROTOCOL)
    if not isinstance(value.get('confirmations'), dict):
        raise ValueError('workflow_control.confirmations must be an object')
    if not isinstance(value.get('production_spec_refs'), list):
        raise ValueError('workflow_control.production_spec_refs must be an array')
    if project.get('current_stage') not in STAGES:
        raise ValueError('current_stage must be one of ' + ', '.join(STAGES))
    return value


def load_project(root):
    project = read_json(root / 'project.json')
    if not isinstance(project, dict):
        raise ValueError('A readable project.json object is required')
    return project


def save_project(root, project):
    # Only project state is authoritative. Reports and handoff tables are derived.
    target = root / 'project.json'
    temporary = root / 'project.json.workflow-tmp'
    if temporary.exists():
        raise ValueError('An earlier workflow update is unfinished; inspect ' + str(temporary))
    temporary.write_text(json.dumps(project, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(target)



# Method preservation is part of workflow_control, not another approval stage.
METHOD_POLICY = 'preserve_confirmed_v1'
METHOD_BASELINE = 'method-baseline.json'
METHOD_CORE = ('visual-methods', 'implementation-lock', 'composition-plan')
JOB_OUTPUT_KEYS = ('scene_ref', 'video_ref', 'demo_ref', 'proof_ref', 'receipt_ref', 'readback_ref', 'review_ref')


def _method_require(ok, message):
    if not ok:
        raise ValueError('LINEAGE_VIOLATION: ' + message)


def method_refs(project):
    pipeline = project.get('visual_pipeline') or {}
    return {'visual-methods': pipeline.get('methods_ref'),
            'implementation-lock': pipeline.get('implementation_lock_ref'),
            'composition-plan': pipeline.get('composition_plan_ref'),
            'execution-plan': project.get('execution_plan_ref'),
            'execution-reference': project.get('execution_reference_ref'), 'timeline': 'timeline.json'}


def _method_context(project):
    keys = ('project_id', 'output', 'source_scope', 'confirmed_constraints', 'audio_policy',
            'source_audio_policy', 'text_policy', 'voiceover_policy', 'narrative_direction_ref',
            'execution_plan_ref', 'execution_reference_ref', 'visual_pipeline')
    result = {key: project.get(key) for key in keys}
    ctl = project['workflow_control']
    result['audio_choice'] = ctl.get('audio_choice')
    result['visual_spec_refs'] = ctl.get('visual_spec_refs')
    return result


def _method_documents(root, project, names):
    result = {}
    for name in names:
        ref = method_refs(project).get(name)
        _method_require(isinstance(ref, str) and '#' not in ref, 'missing whole-file reference for ' + name)
        text = artifact_bytes(root, ref).decode('utf-8')
        result[name] = {'ref': ref, 'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
                        'data': json.loads(text) if ref.endswith('.json') else text}
    return result


def _method_parts(path):
    _method_require(isinstance(path, str) and path.startswith('/') and path != '/', 'an exact non-root JSON path is required')
    parts = path[1:].split('/')
    _method_require(all(part and '*' not in part and '~' not in part for part in parts), 'wildcards/escaped paths are not supported')
    return parts


def _method_location(document, path):
    """Resolve keyed objects or unique @field=value rows; never array positions."""
    value = document
    parts = _method_parts(path)
    for index, part in enumerate(parts):
        if isinstance(value, list):
            _method_require(part.startswith('@') and '=' in part, 'arrays require stable @id=value selectors: ' + path)
            key, wanted = part[1:].split('=', 1)
            ids = [row.get(key) for row in value if isinstance(row, dict)]
            _method_require(len(ids) == len(value) and all(x is not None for x in ids)
                            and len({str(x) for x in ids}) == len(ids), 'missing/duplicate stable ids: ' + path)
            matches = [i for i, row in enumerate(value) if str(row[key]) == wanted]
            _method_require(len(matches) == 1, 'selector does not identify exactly one row: ' + path)
            key = matches[0]
        else:
            _method_require(isinstance(value, dict) and part in value, 'missing path: ' + path)
            key = part
        if index == len(parts) - 1:
            return value, key
        value = value[key]


def _method_block(text, path):
    _method_require(isinstance(path, str) and re.fullmatch(r'(block|container):[A-Za-z0-9_.-]+', path), 'Markdown requires an explicit block:id or container:id')
    kind, key = path.split(':', 1)
    tag = 'param' if kind == 'block' else 'container'
    begin, end = '<!-- lvr:' + tag + ' ' + key + ' -->', '<!-- /lvr:' + tag + ' ' + key + ' -->'
    _method_require(text.count(begin) == 1 and text.count(end) == 1, 'missing/ambiguous Markdown parameter block: ' + key)
    a, b = text.index(begin) + len(begin), text.index(end)
    _method_require(a <= b and (kind == 'container' or '<!-- lvr:param ' not in text[a:b]), 'invalid/nested Markdown parameter block: ' + key)
    return a, b


def method_value(documents, locator, value=None, write=False):
    _method_require(isinstance(locator, dict) and locator.get('artifact') in documents, 'unknown parameter artifact')
    entry = documents[locator['artifact']]
    path = locator.get('path')
    if isinstance(entry['data'], str):
        a, b = _method_block(entry['data'], path)
        if write:
            _method_require(isinstance(value, str) and (path.startswith('container:') or '<!--' not in value), 'Markdown parameter must be plain text')
            entry['data'] = entry['data'][:a] + value + entry['data'][b:]
        else:
            return entry['data'][a:b]
    else:
        parent, key = _method_location(entry['data'], path)
        if write:
            parent[key] = value
        else:
            return parent[key]


def _method_safe_locator(locator):
    name, path = locator.get('artifact'), locator.get('path', '')
    if name in ('execution-plan', 'execution-reference'):
        _method_require(path.startswith('block:'), 'prose edits require parameter blocks')
        return
    parts = _method_parts(path)
    fixed = {'renderer', 'renderer_lock', 'implementation_method', 'backend', 'mode', 'kind', 'parent',
             'easing', 'interpolation', 'font_ref', 'font_family', 'asset_ref', 'native_scene_ref', 'fit', 'z_order', 'source_id', 'unit_id',
             'source_signature', 'time_mapping_digest', 'source_constraint_ref', 'adopted_boundary_ref', 'edit_boundary_ref',
             'event_ids', 'method_ids', 'implementation_element_ids', 'd2_selection_snapshot',
             'proof_composition_ids', 'safe_adaptation', 'parameter_bindings', 'reference_trace'}
    _method_require(not any(part in fixed for part in parts), 'method/identity fields cannot be adaptation slots: ' + path)
    if name == 'implementation-lock':
        _method_require(len(parts) >= 4 and parts[0] == 'elements' and parts[2] == 'parameters', 'Lock slots must be concrete element parameters')
    elif name == 'visual-methods':
        _method_require(len(parts) >= 4 and parts[0] == 'methods' and parts[1].startswith('@method_id=')
                        and parts[2] == 'parameters', 'Method slots must be concrete method parameters')
    elif name == 'composition-plan':
        _method_require(len(parts) >= 3 and parts[0] == 'compositions' and parts[1].startswith('@composition_id='), 'Composition slots require a stable composition id')
        _method_require(parts[-1] not in JOB_OUTPUT_KEYS, 'output names are derived by adapt, not free parameters')
    elif name == 'timeline':
        _method_require(len(parts) >= 3 and parts[0] in ('events', 'text_tracks', 'audio_tracks')
                        and parts[1].startswith('@'), 'Timeline slots require stable track/event ids')
    else:
        _method_require(False, 'unsupported parameter artifact: ' + str(name))



def _method_bound_value(target, value):
    if 'format' not in target:
        return value
    template = target['format']
    _method_require(isinstance(template, str) and template.count('{value}') == 1
                    and '{' not in template.replace('{value}', '') and '}' not in template.replace('{value}', ''),
                    'formatted bindings support exactly one literal {value} placeholder')
    return template.replace('{value}', str(value))


def _method_render_binding(target):
    if target.get('artifact') != 'composition-plan' or 'format' in target:
        return False
    parts = _method_parts(target.get('path'))
    return len(parts) >= 3 and (parts[2] in ('groups', 'layers') or parts[2] in ('frame_count', 'local_start_frame'))


def _method_rules(documents):
    lock = documents['implementation-lock']['data']
    adaptation = lock.get('safe_adaptation')
    _method_require(isinstance(adaptation, dict) and isinstance(adaptation.get('allowed'), list)
                    and isinstance(adaptation.get('requires_d2_return'), list), 'safe_adaptation must declare allowed and requires_d2_return')
    rules = {}
    for row in adaptation['allowed']:
        if isinstance(row, str) and row.strip():
            continue  # Legacy prose is retained, never treated as an editable field.
        _method_require(isinstance(row, dict) and isinstance(row.get('slot'), str) and row['slot'] not in rules,
                        'adaptation slots must be unique typed records')
        _method_safe_locator(row)
        _method_require(row.get('type') in ('number', 'integer', 'string', 'boolean'), 'slots support explicit scalar types only')
        _method_check_value(row, method_value(documents, row))
        rules[row['slot']] = row
    bindings = lock.get('parameter_bindings', [])
    _method_require(isinstance(bindings, list), 'parameter_bindings must be an array')
    owners, targets = set(), set()
    for binding in bindings:
        source, destinations = binding.get('source'), binding.get('targets')
        _method_require(isinstance(source, dict) and isinstance(destinations, list) and destinations, 'bindings require a source and actual targets')
        _method_safe_locator(source)
        identity = (source['artifact'], source['path'])
        _method_require(identity not in owners and identity not in targets, 'duplicate/chained binding owner')
        owners.add(identity)
        original = method_value(documents, source)
        for target in destinations:
            _method_safe_locator(target)
            identity = (target['artifact'], target['path'])
            _method_require(identity not in targets and identity not in owners, 'duplicate/chained binding target')
            targets.add(identity)
            _method_require(digest(method_value(documents, target)) == digest(_method_bound_value(target, original)), 'bound parameter differs from its owner: ' + str(identity))
    for row in rules.values():
        identity = (row['artifact'], row['path'])
        _method_require(identity not in targets, 'edit the canonical parameter owner, not a derived target')
        if row['artifact'] in ('implementation-lock', 'visual-methods'):
            mapped = [b for b in bindings if b['source'] == {'artifact': row['artifact'], 'path': row['path']}]
            _method_require(len(mapped) == 1 and any(_method_render_binding(t) for t in mapped[0]['targets']),
                            'adaptable implementation parameters require an actual composition mapping')
    return rules, bindings


def _method_check_value(rule, value):
    kind = rule['type']
    valid = ((type(value) in (int, float) and kind == 'number') or (type(value) is int and kind == 'integer')
             or (isinstance(value, str) and kind == 'string') or (type(value) is bool and kind == 'boolean'))
    _method_require(valid, 'wrong value type for slot ' + rule['slot'])
    digest(value)  # reject NaN/infinity, including nested values supplied by callers
    if kind in ('number', 'integer'):
        _method_require(type(rule.get('minimum')) in (int, float) and type(rule.get('maximum')) in (int, float)
                        and rule['minimum'] <= value <= rule['maximum'], 'parameter outside approved bounds: ' + rule['slot'])
    if kind == 'string':
        _method_require(type(rule.get('max_length')) is int and 0 < rule['max_length'] <= 10000
                        and len(value) <= rule['max_length'], 'string exceeds approved bound: ' + rule['slot'])
    if 'enum' in rule:
        _method_require(isinstance(rule['enum'], list) and any(digest(value) == digest(x) for x in rule['enum']), 'parameter outside approved enum')


def legacy_v1414_method_contract_digest(documents, context):
    import copy
    data = copy.deepcopy(documents)
    rules, bindings = _method_rules(data)
    for rule in rules.values():
        method_value(data, rule, '<adaptable:' + rule['slot'] + '>', True)
        for binding in bindings:
            if binding['source'] == {'artifact': rule['artifact'], 'path': rule['path']}:
                for target in binding['targets']:
                    method_value(data, target, _method_bound_value(target, '<adaptable:' + rule['slot'] + '>'), True)
    # Actual artifact identities are content evidence, not a new implementation method.
    lock = data['implementation-lock']['data']
    for key in ('selected_mockup_ref', 'selected_mockup_sha256', 'confirmed_mockups'):
        if key in lock:
            lock[key] = '<current-confirmed-visual-binding>'
    if isinstance(lock.get('visual_stage_binding'), dict):
        lock['visual_stage_binding']['v7_sha256'] = '<current-v7-binding>'
    # Output filenames change only through adapt's deterministic revision naming.
    for job in data['composition-plan']['data'].get('compositions', []):
        for key in JOB_OUTPUT_KEYS:
            if job.get(key):
                job[key] = '<generated-output>'
    return digest({'context': context, 'artifacts': {name: row['data'] for name, row in data.items() if name in METHOD_CORE}})


def _method_projection(documents):
    """Known content fields are variable instances; unknown fields remain locked."""
    import copy
    data = copy.deepcopy(documents)
    rules, bindings = _method_rules(data)
    jobs = data['composition-plan']['data']['compositions']
    for rule in rules.values():
        original_value = method_value(documents, rule)
        method_value(data, rule, '<adaptable:' + rule['slot'] + '>', True)
        for binding in bindings:
            if binding['source'] != {'artifact': rule['artifact'], 'path': rule['path']}:
                continue
            for target in binding['targets']:
                method_value(data, target, _method_bound_value(target, '<adaptable:' + rule['slot'] + '>'), True)
                # A copied instance of the same grammar has the same adjustable positions.
                if target['artifact'] == 'composition-plan':
                    parts = _method_parts(target['path'])
                    relative = '/' + '/'.join(parts[2:])
                    prototype = next(j for j in jobs if j['composition_id'] == parts[1].split('=', 1)[1])
                    for job in jobs:
                        if (job['method_ids'], job['implementation_element_ids']) != (prototype['method_ids'], prototype['implementation_element_ids']):
                            continue
                        try:
                            parent, key = _method_location(job, relative)
                        except ValueError:
                            continue
                        actual = method_value(documents, {'artifact': 'composition-plan', 'path': '/compositions/@composition_id=' + job['composition_id'] + relative})
                        _method_require(digest(actual) == digest(_method_bound_value(target, original_value)),
                                        'shared instance parameter differs from its owner: ' + job['composition_id'] + relative)
                        parent[key] = _method_bound_value(target, '<adaptable:' + rule['slot'] + '>')
    methods = data['visual-methods']['data']
    for row in methods['methods']:
        for key in ('event_ids', 'source_evidence_refs', 'source_conditions', 'original_frame_assessment'):
            row.pop(key, None)
    lock = data['implementation-lock']['data']
    for key in ('selected_mockup_ref', 'selected_mockup_sha256', 'confirmed_mockups'):
        lock.pop(key, None)
    if isinstance(lock.get('visual_stage_binding'), dict):
        lock['visual_stage_binding'].pop('v7_sha256', None)
    for row in lock['elements'].values():
        row.pop('event_ids', None)
    # Binding topology per grammar stays locked; concrete composition IDs are instances.
    for binding in lock.get('parameter_bindings', []):
        targets = []
        for target in binding['targets']:
            if target['artifact'] == 'composition-plan':
                target['path'] = re.sub(r'^/compositions/@composition_id=[^/]+', '/compositions/@composition_id=<instance>', target['path'])
            if target not in targets:
                targets.append(target)
        binding['targets'] = sorted(targets, key=digest)
    plan = data['composition-plan']['data']
    grammar = []
    for job in jobs:
        for key in JOB_OUTPUT_KEYS + ('composition_id', 'event_ids', 'anchor_event_id', 'local_start_frame',
                'frame_count', 'preview_audio_ref', 'proof_covered_by', 'proof_coverage_reason', 'additional_proof_exception'):
            job.pop(key, None)
        for layer in job.get('layers', []):
            for key in ('text', 'start_frame', 'end_frame', 'source_in_ms', 'source_out_ms'):
                layer.pop(key, None)
            if layer.get('kind') in ('image', 'video'):
                layer.pop('asset_ref', None)
        for join in job.get('joins', []):
            for key in ('frame', 'before_frames', 'after_frames', 'from_event_id', 'to_event_id'):
                join.pop(key, None)
        grammar.append(digest(job))
    plan.pop('compositions')
    plan.pop('proof_composition_ids', None)
    plan.pop('proof_composition_id', None)
    return {name: data[name]['data'] for name in METHOD_CORE}, sorted(set(grammar))


def method_contract_digest(documents, context, grammar_catalog=None):
    fixed, used = _method_projection(documents)
    catalog = used if grammar_catalog is None else grammar_catalog
    _method_require(isinstance(catalog, list) and set(used) <= set(catalog),
                    'composition visual grammar changed; declare a scoped D2 method revision')
    return digest({'context': context, 'artifacts': fixed, 'grammar_catalog': sorted(set(catalog))})


def _method_catalog(root, project):
    record = (project.get('workflow_control', {}).get('method_preservation') or {}).get('baseline')
    if record and contained(root, METHOD_BASELINE).is_file():
        baseline = read_json(contained(root, METHOD_BASELINE))
        if baseline.get('schema_version') == '1.1':
            _method_require(artifact(root, METHOD_BASELINE)['sha256'] == record.get('sha256'), 'method baseline altered')
            return baseline['grammar_catalog']
    return None


def method_visual_digest(root, project):
    """Content/timing may evolve; visual grammar and executable structure stay fixed."""
    import copy
    import visual_pipeline as production
    directory = production.visual_stage_dir(project)
    if directory is None:
        return None
    record = copy.deepcopy(read_json(contained(root, directory + '/V7-lock.json')))
    _method_require(isinstance(record, dict), 'a current V7 lock is required')
    for key in ('inputs_sha256', 'inputs_design_sha256', 'expansion_checks'):
        record.pop(key, None)
    for element in record.get('elements', []):
        for key in ('text', 't_in', 't_out'):
            element.pop(key, None)
    return digest(record)


def sync_confirmed_visual_bindings(root, project, new_lock):
    """Refresh only derived V6/V7 identities through the existing sync command."""
    state = project.get('workflow_control', {}).get('method_preservation')
    if not isinstance(state, dict) or state.get('baseline') is None:
        return False
    import copy
    import visual_pipeline as production
    baseline = method_guard(root, project, allow_narrative_change=True)
    _method_require(method_visual_digest(root, project) == baseline.get('visual_method_digest'),
                    'visual grammar changed; use the existing D2 method decision')
    old_lock = baseline['artifacts']['implementation-lock']['data']
    def fixed(lock):
        data = copy.deepcopy(lock)
        for key in ('selected_mockup_ref', 'selected_mockup_sha256', 'confirmed_mockups'):
            data.pop(key, None)
        if isinstance(data.get('visual_stage_binding'), dict):
            data['visual_stage_binding'].pop('v7_sha256', None)
        return data
    _method_require(digest(fixed(new_lock)) == digest(fixed(old_lock)), 'visual sync cannot change parameters or the implementation method')
    design = production.visual_stage_design(root, project, require_lock=True)
    expected = {'v7_ref': design['report']['artifacts']['V7-lock']['ref'],
                'v7_sha256': design['report']['artifacts']['V7-lock']['sha256'], 'chosen_candidate': design['chosen_candidate']}
    mocks = production.confirmed_visual_artifacts(root, project)
    _method_require(new_lock.get('visual_stage_binding') == expected and new_lock.get('confirmed_mockups') == mocks
                    and new_lock.get('selected_mockup_ref') == project.get('visual_mockup_ref')
                    and any(x == {'ref': new_lock['selected_mockup_ref'], 'sha256': new_lock.get('selected_mockup_sha256')} for x in mocks),
                    'visual sync must bind current actually confirmed V6/V7 artifacts')
    ref = baseline['artifacts']['implementation-lock']['ref']
    path = contained(root, ref)
    text = json.dumps(new_lock, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if text.encode('utf-8') == path.read_bytes():
        return True
    revision = digest({'base': state['baseline']['sha256'], 'visual_binding': expected, 'mockups': mocks})[:12]
    marker = contained(root, METHOD_BASELINE + '.applying')
    project_before = (root / 'project.json').read_bytes().decode('utf-8')
    journal = {'base_sha256': state['baseline']['sha256'], 'revision': revision, 'project_before': project_before,
               'baseline_before': contained(root, METHOD_BASELINE).read_bytes().decode('utf-8'),
               'files': {ref: {'before': path.read_bytes().decode('utf-8'), 'after': text}}}
    with marker.open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(journal, ensure_ascii=False) + '\n')
    if (root / 'project.json').read_bytes().decode('utf-8') != project_before or hashlib.sha256(path.read_bytes()).hexdigest() != baseline['artifacts']['implementation-lock']['sha256']:
        marker.unlink(); _method_require(False, 'project changed during visual sync')
    temporary = path.with_name(path.name + '.adapt-pending')
    _method_require(not temporary.exists(), 'unfinished visual binding write')
    temporary.write_text(text, encoding='utf-8'); temporary.replace(path)
    _method_write_checkpoint(root, project, baseline['artifacts'], baseline,
        {'kind': 'confirmed_visual_binding_sync', 'revision': revision, 'parent_sha256': state['baseline']['sha256'],
         'v7': expected, 'confirmed_mockups': mocks}, narrative_override=baseline['narrative'])
    save_project(root, project)
    marker.unlink()
    return True



def method_inputs(root, project):
    documents = _method_documents(root, project, METHOD_CORE)
    # Bindings into a document outside METHOD_CORE must still be checked.
    required = {x['artifact'] for b in documents['implementation-lock']['data'].get('parameter_bindings', [])
                for x in [b.get('source', {})] + b.get('targets', []) if x.get('artifact')}
    required.update(row['artifact'] for row in documents['implementation-lock']['data'].get('safe_adaptation', {}).get('allowed', []) if isinstance(row, dict))
    documents.update(_method_documents(root, project, sorted(required - set(documents))))
    revision = (project['workflow_control'].get('method_preservation') or {}).get('open_revision')
    catalog = None if revision and revision.get('kind') == 'method' else _method_catalog(root, project)
    return {'method_contract': method_contract_digest(documents, _method_context(project), catalog),
            'sources': artifact(root, 'sources.json')}


def _method_baseline(root, project):
    _method_require(not contained(root, METHOD_BASELINE + '.applying').exists(), 'a parameter patch was interrupted; restore its baseline before continuing')
    state = project['workflow_control'].get('method_preservation')
    _method_require(isinstance(state, dict) and state.get('schema_version') == '1.0', 'missing method preservation state; run init')
    record = state.get('baseline')
    if record is None:
        _method_require(not contained(root, METHOD_BASELINE).exists(), 'orphan method baseline; inspect it before adoption')
        _method_require(not project['workflow_control']['confirmations'].get('method'), 'confirmed method has no baseline; explicit adoption is required')
        return state, None
    _method_require(isinstance(record, dict) and record.get('ref') == METHOD_BASELINE, 'invalid method baseline reference')
    path = contained(root, record['ref'])
    _method_require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == record.get('sha256'), 'method baseline missing or altered')
    baseline = read_json(path)
    _method_require(isinstance(baseline, dict) and baseline.get('schema_version') == '1.1'
                    and baseline.get('project_id') == project.get('project_id') and isinstance(baseline.get('artifacts'), dict), 'invalid method baseline')
    _method_require(baseline.get('method_digest') == method_contract_digest(baseline['artifacts'], baseline['context'], baseline.get('grammar_catalog')), 'method baseline contract is inconsistent')
    confirmation = project['workflow_control']['confirmations'].get('method') or {}
    _method_require(confirmation.get('method_contract_digest') == baseline['method_digest'], 'method baseline is not anchored to its real method confirmation')
    _method_require(confirmation.get('visual_method_digest') == baseline.get('visual_method_digest'), 'visual method baseline is not anchored to its real method confirmation')
    return state, baseline


def _method_step0_timeline(before, after, output):
    """Recognize only the original snapshotted range calibration and derived coordinates."""
    import copy
    from timeline_math import canonical_assembly_ranges
    old, new = copy.deepcopy(before), copy.deepcopy(after)
    if old.get('status') not in ('draft', 'ready_for_render') or new.get('status') not in ('draft', 'ready_for_render'):
        return False
    new['status'] = old['status']
    if len(old.get('events', [])) != len(new.get('events', [])):
        return False
    changed = {}
    for a, b in zip(old['events'], new['events']):
        if a.get('event_id') != b.get('event_id'):
            return False
        if (a.get('source_in_ms'), a.get('source_out_ms')) == (b.get('source_in_ms'), b.get('source_out_ms')):
            continue
        snap = a.get('d2_selection_snapshot') or {}
        keys = ('planned_source_in_ms', 'planned_source_out_ms', 'safe_in_start_ms', 'safe_in_end_ms', 'safe_out_start_ms', 'safe_out_end_ms')
        if a.get('kind') != 'source' or not all(type(snap.get(k)) is int for k in keys):
            return False
        allowed = snap.get('allowed_adjustments', [])
        if not isinstance(allowed, list) or set(allowed) - {'trim_inside_safe_window', 'add_transition_handle'}:
            return False
        for row in (a, b):
            x, y = row.get('source_in_ms'), row.get('source_out_ms')
            if not (type(x) is int and type(y) is int and x < y
                    and snap['safe_in_start_ms'] <= x < snap['safe_in_end_ms']
                    and snap['safe_out_start_ms'] <= y <= snap['safe_out_end_ms']):
                return False
            if (x > snap['planned_source_in_ms'] or y < snap['planned_source_out_ms']) and 'trim_inside_safe_window' not in allowed:
                return False
            if (x < snap['planned_source_in_ms'] or y > snap['planned_source_out_ms']) and 'add_transition_handle' not in allowed:
                return False
        changed[a['event_id']] = (a, copy.deepcopy(b))
        b['source_in_ms'], b['source_out_ms'] = a['source_in_ms'], a['source_out_ms']
    if not changed:
        return digest(old) == digest(new)
    old_ranges = canonical_assembly_ranges(before['events'], output['fps_num'], output['fps_den'])
    new_ranges = canonical_assembly_ranges(after['events'], output['fps_num'], output['fps_den'])
    lengths = {}
    for a, b, actual, first, second in zip(old['events'], new['events'], after['events'], old_ranges, new_ranges):
        lengths[a['event_id']] = (first['length_frames'], second['length_frames'])
        for key, coordinate in (('out_in_frame', 'assembly_in_frame'), ('out_out_frame', 'assembly_out_frame')):
            if actual.get(key) != a.get(key):
                if actual.get(key) != second[coordinate]:
                    return False
                b[key] = a.get(key)
    for key in ('audio_tracks', 'text_tracks'):
        if len(old.get(key, [])) != len(new.get(key, [])):
            return False
        for a, b in zip(old.get(key, []), new.get(key, [])):
            if digest(a) == digest(b):
                continue
            eid = a.get('sync_event_id') or a.get('anchor_event_id')
            if eid not in changed:
                return False
            first, second = changed[eid]
            if key == 'audio_tracks':
                if a.get('sync_mode') != 'locked' or a.get('source_id') != first.get('source_id'):
                    return False
                for endpoint in ('source_in_ms', 'source_out_ms'):
                    if b.get(endpoint) != a.get(endpoint):
                        if type(a.get(endpoint)) is not int or b.get(endpoint) != a[endpoint] + second[endpoint] - first[endpoint]:
                            return False
                        b[endpoint] = a[endpoint]
            if b.get('local_out_frame') != a.get('local_out_frame'):
                if a.get('local_out_frame') != lengths[eid][0] or b.get('local_out_frame') != lengths[eid][1]:
                    return False
                b['local_out_frame'] = a['local_out_frame']
            if key == 'text_tracks' and b.get('stable_hold_frames') != a.get('stable_hold_frames'):
                expected = lengths[eid][1] - a.get('local_in_frame', 0) - a.get('fade_in_frames', 0) - a.get('fade_out_frames', 0)
                old_expected = lengths[eid][0] - a.get('local_in_frame', 0) - a.get('fade_in_frames', 0) - a.get('fade_out_frames', 0)
                if (a.get('stable_hold_frames') != old_expected
                        or after.get(key, [])[old[key].index(a)].get('local_out_frame') != lengths[eid][1]
                        or b.get('stable_hold_frames') != expected):
                    return False
                b['stable_hold_frames'] = a.get('stable_hold_frames')
            if digest(a) != digest(b):
                return False
    if old.get('duration_budget') != new.get('duration_budget'):
        budget = new.get('duration_budget') or {}
        original = old.get('duration_budget') or {}
        frames = sum(row['length_frames'] for row in new_ranges)
        overlap = original.get('sum_transition_overlap_frames')
        if type(overlap) is not int:
            return False
        expected = dict(original, sum_event_frames=frames, computed_output_frames=frames-overlap)
        if digest(budget) != digest(expected):
            return False
        new['duration_budget'] = original
    return digest(old) == digest(new)


def _method_step0_notes(before, after):
    """Existing Step 0 status bookkeeping cannot change execution prose or parameters."""
    if strip_step0(before) != strip_step0(after):
        return False
    def normalize(text):
        lines, active, count, result = text.splitlines(keepends=True), None, 0, []
        for line in lines:
            heading = re.match(r'^(#{1,6})\s+(.+)', line)
            if heading and 'Execute Step 0' in heading[2]:
                active = len(heading[1]); count += 1
            elif active is not None and heading and len(heading[1]) <= active:
                active = None
            if active is not None:
                line = re.sub(r'\b(pending|completed)\b|待核|已完成', '<step0-status>', line, flags=re.I)
            result.append(line)
        return count, ''.join(result)
    first, second = normalize(before), normalize(after)
    return first[0] == second[0] == 1 and first[1] == second[1]



def method_guard(root, project, allow_narrative_change=False):
    import visual_pipeline as production
    if not production.enabled(project):
        return None
    _method_require(project.get('execution_policy', {}).get('method_preservation') == METHOD_POLICY, 'method preservation policy is required; run init')
    state, baseline = _method_baseline(root, project)
    if baseline is None:
        return None
    _method_require(not state.get('open_revision'), 'revision is in progress; inspect revise/status and close it through the existing plan decision')
    _method_require(digest(_method_context(project)) == digest(baseline['context']), 'confirmed project method context/refs changed')
    _method_require(method_visual_digest(root, project) == baseline.get('visual_method_digest'), 'visual grammar changed; use the existing D2 method decision')
    current = _method_documents(root, project, baseline['artifacts'])
    for name, old in baseline['artifacts'].items():
        same = current[name]['ref'] == old['ref'] and current[name]['sha256'] == old['sha256']
        if not same and name == 'timeline' and isinstance(current[name]['data'], dict):
            same = _method_step0_timeline(old['data'], current[name]['data'], project['output'])
        if not same and name == 'execution-plan':
            same = _method_step0_notes(old['data'], current[name]['data'])
        if not same:
            changes = revision_structured_diff(name, old['data'], current[name]['data'])
            detail = ', '.join(row['path'] for row in changes[:12]) or '$bytes'
            _method_require(False, 'untracked edit in ' + name + ' ' + detail + '; restore the baseline, then declare revise scope or use adapt')
    _method_rules(current)
    if not allow_narrative_change:
        _method_require(artifact(root, project['narrative_direction_ref']) == baseline['narrative'], 'Narrative changed without applying its parameter patch')
    return baseline


def _method_write_checkpoint(root, project, names, previous=None, revision=None, narrative_override=None):
    documents = _method_documents(root, project, names)
    _method_rules(documents)
    catalog = previous['grammar_catalog'] if previous else _method_projection(documents)[1]
    baseline = {'schema_version': '1.1', 'project_id': project['project_id'], 'context': _method_context(project),
                'artifacts': documents, 'narrative': narrative_override or artifact(root, project['narrative_direction_ref']),
                'visual_method_digest': method_visual_digest(root, project),
                'grammar_catalog': catalog, 'method_digest': method_contract_digest(documents, _method_context(project), catalog),
                'checkpoint_revision': revision.get('revision') if revision else None}
    if previous:
        _method_require(baseline['method_digest'] == previous['method_digest'] and baseline['visual_method_digest'] == previous.get('visual_method_digest'), 'parameter patch changed the confirmed method')
    path = contained(root, METHOD_BASELINE)
    pending = contained(root, METHOD_BASELINE + '.pending')
    _method_require(not pending.exists(), 'unfinished method checkpoint; inspect pending file')
    pending.write_text(json.dumps(baseline, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    pending.replace(path)
    state = project['workflow_control']['method_preservation']
    state['baseline'] = {'ref': METHOD_BASELINE, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    if revision is not None:
        state['last_patch'] = revision


REVISION_IDS = ('composition_id', 'event_id', 'text_id', 'track_id', 'method_id', 'layer_id', 'join_id', 'key_id', 'slot')


def _segment_sections(container_text):
    """Parse plan.segments by stable Segment number. The number is identity, not display order."""
    headings = list(re.finditer(r'^###\s+(.+?)\s*$', container_text, re.M))
    segments, order = {}, []
    prefix = container_text[:headings[0].start()] if headings else container_text
    footer = ''
    for index, heading in enumerate(headings):
        raw = heading.group(1).strip()
        if not raw.startswith('Segment'):
            _method_require(False, 'invalid Segment heading format: use `### Segment N` or `### Segment N · description`; Segment number is identity, not order')
        match = re.fullmatch(r'Segment\s+([1-9][0-9]*)(?:\s+(.+))?', raw)
        _method_require(match is not None, 'invalid Segment heading format: use `### Segment N` or `### Segment N · description`; Segment number is identity, not order')
        identity = 'seg' + match.group(1)
        _method_require(identity not in segments, 'duplicate Segment identity: ' + identity)
        end = headings[index + 1].start() if index + 1 < len(headings) else len(container_text)
        body = container_text[heading.end():end]
        block_matches = list(re.finditer(r'<lvr:block ([A-Za-z0-9_.-]+)>', body))
        block_ids = [m.group(1) for m in block_matches]
        structure_body = body
        if index + 1 == len(headings) and block_matches:
            tail = body[block_matches[-1].end():]
            if tail.strip():
                footer = tail
                structure_body = body[:block_matches[-1].end()] + ('\n' if body[block_matches[-1].end():].startswith('\n') else '')
        segments[identity] = {'identity': identity, 'heading': raw, 'description': match.group(2) or '',
                              'body': body, 'structure_body': structure_body, 'block_ids': block_ids,
                              'full': container_text[heading.start():end]}
        order.append(identity)
    return segments, order, prefix, footer


def _revision_blocks(text):
    pattern = r'<!-- lvr:param ([A-Za-z0-9_.-]+) -->(.*?)<!-- /lvr:param \1 -->'
    found = list(re.finditer(pattern, text, re.S))
    ids = [m[1] for m in found]
    _method_require(len(ids) == len(set(ids)) and len(found) == text.count('<!-- lvr:param ')
                    == text.count('<!-- /lvr:param '), 'missing/duplicate/nested Markdown block')
    _method_require(all('<!-- lvr:param ' not in m[2] and '<!-- lvr:container ' not in m[2] for m in found), 'nested Markdown block')
    _method_require(all(not re.search(r'^#{1,6}\s', m[2], re.M) for m in found), 'Markdown headings must remain outside editable text blocks')
    values = {m[1]: m[2] for m in found}
    skeleton = re.sub(pattern, lambda m: '<lvr:block ' + m[1] + '>', text, flags=re.S)
    containers = list(re.finditer(r'<!-- lvr:container ([A-Za-z0-9_.-]+) -->(.*?)<!-- /lvr:container \1 -->', skeleton, re.S))
    _method_require(len(containers) == skeleton.count('<!-- lvr:container ') == skeleton.count('<!-- /lvr:container ')
                    and len(containers) <= 1, 'invalid/nested Markdown container')
    for container in containers:
        _method_require(container[1] == 'plan.segments' and not re.search(r'^#{1,2}(?:\s|$)', container[2], re.M),
                        'only plan.segments may contain Segment headings; level 1/2 headings stay outside')
        _segment_sections(container[2])
        headings = re.findall(r'^## (.+)$', skeleton[:container.start()], re.M)
        _method_require(headings and headings[-1].strip() == '最终素材取舍', 'plan.segments must belong to 最终素材取舍')
        values['container:' + container[1]] = container[2]
    outside = re.sub(r'<!-- lvr:container ([A-Za-z0-9_.-]+) -->.*?<!-- /lvr:container \1 -->', lambda m: '<lvr:container ' + m[1] + '>', skeleton, flags=re.S)
    return values, outside


def revision_structured_diff(artifact_name, before, after, path=''):
    if digest(before) == digest(after):
        return []
    def row(op, location, old, new):
        return {'artifact': artifact_name, 'path': location or '$root', 'op': op, 'before': old, 'after': new}
    if isinstance(before, str) and isinstance(after, str) and not path and artifact_name in ('execution-plan', 'execution-reference'):
        old, outside_old = _revision_blocks(before); new, outside_new = _revision_blocks(after)
        rows = []
        old_container = old.get('container:plan.segments')
        new_container = new.get('container:plan.segments')
        old_segments = new_segments = {}; old_order = new_order = []; old_prefix = new_prefix = old_footer = new_footer = ''
        if old_container is not None or new_container is not None:
            old_segments, old_order, old_prefix, old_footer = _segment_sections(old_container or '')
            new_segments, new_order, new_prefix, new_footer = _segment_sections(new_container or '')
        old_membership = {block: seg for seg, data in old_segments.items() for block in data['block_ids']}
        new_membership = {block: seg for seg, data in new_segments.items() for block in data['block_ids']}
        for key in sorted((set(old) | set(new)) - {'container:plan.segments'}):
            if old.get(key) == new.get(key) and ((key in old) == (key in new)):
                continue
            change = row('replace' if key in old and key in new else ('add' if key in new else 'remove'),
                         'block:' + key, old.get(key), new.get(key))
            member = new_membership.get(key) if change['op'] != 'remove' else old_membership.get(key)
            if member:
                change['container'] = 'container:plan.segments'
                change['segment'] = 'segment:' + member
            rows.append(change)
        if old_container is not None or new_container is not None:
            for seg in sorted(set(old_segments) | set(new_segments), key=lambda value: int(value[3:])):
                if seg not in old_segments:
                    rows.append(row('add', 'segment:' + seg, None, new_segments[seg]['full']))
                elif seg not in new_segments:
                    rows.append(row('remove', 'segment:' + seg, old_segments[seg]['full'], None))
                else:
                    if old_segments[seg]['heading'] != new_segments[seg]['heading']:
                        rows.append(row('replace', 'segment:' + seg + '.title', old_segments[seg]['heading'], new_segments[seg]['heading']))
                    if old_segments[seg]['structure_body'].rstrip() != new_segments[seg]['structure_body'].rstrip():
                        rows.append(row('replace', 'segment:' + seg + '.structure', old_segments[seg]['structure_body'], new_segments[seg]['structure_body']))
            common = set(old_segments) & set(new_segments)
            if [seg for seg in old_order if seg in common] != [seg for seg in new_order if seg in common]:
                rows.append(row('reorder', 'container:plan.segments/$order', old_order, new_order))
            if old_prefix != new_prefix or old_footer != new_footer:
                rows.append(row('replace', 'container:plan.segments/$static', old_prefix + old_footer, new_prefix + new_footer))
        if outside_old != outside_new:
            rows.append(row('replace', '$outside', outside_old, outside_new))
        return rows
    if isinstance(before, dict) and isinstance(after, dict):
        rows = []
        for key in sorted(before.keys() | after.keys()):
            location = path + '/' + key
            if key not in before or key not in after:
                rows.append(row('add' if key in after else 'remove', location, before.get(key), after.get(key)))
            else:
                rows += revision_structured_diff(artifact_name, before[key], after[key], location)
        return rows
    if isinstance(before, list) and isinstance(after, list):
        combined = before + after
        identity = next((key for key in REVISION_IDS if combined and all(isinstance(v, dict) and isinstance(v.get(key), str) and v[key] for v in combined)), None)
        if identity:
            for values in (before, after):
                _method_require(len({v[identity] for v in values}) == len(values), 'duplicate stable ID at ' + artifact_name + path)
                _method_require(all(not any(c in v[identity] for c in '/~*') for v in values), 'unsupported stable ID at ' + path)
            old, new = ({v[identity]: v for v in values} for values in (before, after))
            rows = []
            for key in sorted(old.keys() | new.keys()):
                location = path + '/@' + identity + '=' + key
                if key not in old or key not in new:
                    rows.append(row('add' if key in new else 'remove', location, old.get(key), new.get(key)))
                else:
                    rows += revision_structured_diff(artifact_name, old[key], new[key], location)
            if [v[identity] for v in before if v[identity] in new] != [v[identity] for v in after if v[identity] in old]:
                rows.append(row('reorder', path + '/$order', [v[identity] for v in before], [v[identity] for v in after]))
            return rows
        if any(isinstance(v, dict) for v in combined) and path.split('/')[-1] in ('events', 'text_tracks', 'audio_tracks', 'compositions', 'methods', 'layers', 'joins', 'keyframes'):
            _method_require(False, 'changed collection requires unique stable IDs at ' + artifact_name + path)
    return [row('replace', path, before, after)]


def _revision_in_scope(change, revision):
    return any(all(change[key] == scope[key] for key in ('artifact', 'path', 'op'))
               or (change.get('segment') == scope['path'] and change['artifact'] == scope['artifact']
                   and change['op'] == scope['op'] and scope['op'] in ('add', 'remove'))
               for scope in revision['scope'])


def _revision_static_validation(root, project, documents=None):
    """Same non-render validator, with computed JSON values; execution guards remain separate."""
    from validate_project import validate
    overrides = {'project.json': project}
    overrides.update({entry['ref']: entry['data'] for entry in (documents or {}).values() if isinstance(entry['data'], dict)})
    result = validate(root, render_checks=False, _overrides=overrides, _workflow_checks=False)
    return {'errors': result['errors'], 'inputs': {name: hashlib.sha256(contained(root, name).read_bytes()).hexdigest() for name in sorted(set(result['checked'])) if contained(root, name).is_file()}}


def _revision_receipts(root, project):
    import visual_pipeline as production
    inputs, reviews = {}, dict(project['workflow_control']['method_preservation'].get('review_scopes') or {})
    plan = production.composition_plan(root, project)
    for job in plan['compositions']:
        inputs[job['composition_id']] = digest(production.job_input(root, project, plan, job))
        try:
            receipt = production.validate_job_receipt(root, project, plan, job, True)
            production.validate_review(root, project, job, receipt)
            review = read_json(contained(root, job['review_ref']))
            reviews[job['composition_id']] = {'review_sha256': artifact(root, job['review_ref'])['sha256'],
                'job_digest': inputs[job['composition_id']], 'implementation_lock_sha256': next((r.get('implementation_lock_sha256') for r in review.get('checks', []) if r.get('name') == 'ReferenceCompliance'), None)}
        except (ValueError, OSError, TypeError, KeyError):
            pass
    return inputs, reviews


def revise(root, request=None, cancel=False):
    """Declare before editing. No replacement or expansion of an open scope."""
    project = load_project(root); control(project)
    state = project['workflow_control']['method_preservation']
    if request is None and not cancel:
        return revision_preview(root, project)
    if cancel:
        _method_require(state.get('open_revision'), 'no open revision')
        _, baseline = _method_baseline(root, project)
        current = _method_documents(root, project, baseline['artifacts'])
        _method_require(all(row['sha256'] == current[name]['sha256'] and row['ref'] == current[name]['ref'] for name, row in baseline['artifacts'].items())
                        and digest(_method_context(project)) == digest(baseline['context']), 'restore controlled artifacts before cancelling; no edits will be discarded')
        state.pop('open_revision'); save_project(root, project)
        return {'status': 'cancelled', 'workflow': report(root, project=project)}
    baseline = method_guard(root, project, allow_narrative_change=True)
    _method_require(baseline is not None and project['current_stage'] == 'D2', 'revisions require an existing confirmed baseline and return to D2')
    _method_require(set(method_refs(project)) <= set(baseline['artifacts']), 'confirm the original plan before structural revisions')
    names = set(baseline['artifacts']) | set(method_refs(project))
    documents = _method_documents(root, project, names)
    _method_require(all(documents[name]['sha256'] == row['sha256'] and documents[name]['ref'] == row['ref'] for name, row in baseline['artifacts'].items()), 'revise must start from exact baseline bytes, including Step 0 changes; checkpoint those through adapt first')
    _method_require(isinstance(request, dict) and set(request) == {'schema_version', 'kind', 'base_sha256', 'narrative_sha256', 'instruction_ref', 'quote', 'scope'}
                    and request['schema_version'] == '1.0' and request['kind'] in ('content', 'method', 'markup'), 'invalid revision request')
    narrative = artifact(root, project['narrative_direction_ref'])
    _method_require(request['base_sha256'] == state['baseline']['sha256'] and request['narrative_sha256'] == narrative['sha256'], 'revision parent/Narrative is not current')
    _method_require(isinstance(request.get('instruction_ref'), str) and '#' in request['instruction_ref'],
                    'revision instruction_ref must name an exact Markdown section with #section; whole-file instruction refs are not stable enough')
    instruction = _revision_instruction_artifact(root, request['instruction_ref'])
    _method_require(isinstance(request['quote'], str) and request['quote'].strip() and request['quote'] in artifact_bytes(root, request['instruction_ref']).decode('utf-8'), 'revision requires an exact existing instruction quote')
    scope = request['scope']
    _method_require(isinstance(scope, list) and scope and len({digest(s) for s in scope}) == len(scope), 'revision needs unique exact scopes')
    for item in scope:
        _method_require(isinstance(item, dict) and set(item) == {'artifact', 'path', 'op'} and item['artifact'] in documents
                        and item['op'] in ('replace', 'add', 'remove', 'reorder'), 'invalid scope entry')
        entry, path = documents[item['artifact']], item['path']
        if isinstance(entry['data'], str):
            _method_require(isinstance(path, str), 'Markdown scope requires an exact block or Segment identity')
            blocks, _ = _revision_blocks(entry['data'])
            container = blocks.get('container:plan.segments')
            segments = _segment_sections(container)[0] if container is not None else {}
            if re.fullmatch(r'block:[A-Za-z0-9_.-]+', path):
                key = path[6:]
                _method_require((request['kind'] == 'markup' and item['op'] == 'add' and key not in blocks)
                                or (request['kind'] != 'markup' and item['op'] == 'replace' and key in blocks), 'existing prose needs a separate text-preserving markup revision first')
            elif re.fullmatch(r'segment:seg[1-9][0-9]*', path):
                _method_require(item['artifact'] == 'execution-plan' and request['kind'] != 'markup' and item['op'] in ('add', 'remove'),
                                'Segment scope supports only execution-plan segment:segN add/remove')
                identity = path.split(':', 1)[1]
                _method_require((item['op'] == 'add' and identity not in segments) or (item['op'] == 'remove' and identity in segments),
                                'Segment add/remove must name the exact new or existing Segment identity')
            elif path == 'container:plan.segments':
                _method_require(request['kind'] == 'markup' and item['op'] == 'add' and item['artifact'] == 'execution-plan'
                                and 'container:plan.segments' not in blocks,
                                'container:plan.segments is only for text-preserving markup migration; declare each structural change as segment:segN add/remove')
            else:
                _method_require(False, 'Markdown scope requires block:id or exact segment:segN add/remove; Segment number is identity, not order')
        else:
            parts = _method_parts(path.removesuffix('/$order'))
            _method_require(parts[-1] not in REVISION_IDS and parts[-1] not in JOB_OUTPUT_KEYS, 'identity/output fields cannot be replaced in scope')
            if item['op'] == 'add':
                parent_path = '/' + '/'.join(parts[:-1])
                parent = method_value(documents, {'artifact': item['artifact'], 'path': parent_path})
                last = parts[-1]
                if isinstance(parent, list):
                    _method_require(last.startswith('@') and '=' in last, 'added rows require stable ID selectors')
                    key, value = last[1:].split('=', 1)
                    _method_require(key in REVISION_IDS and not any(str(row.get(key)) == value for row in parent), 'added ID already exists')
                else:
                    _method_require(isinstance(parent, dict) and last not in parent, 'added field already exists')
            elif item['op'] == 'reorder':
                _method_require(path.endswith('/$order'), 'reorder requires /$order')
                _method_location(entry['data'], path.removesuffix('/$order'))
            else:
                value = method_value(documents, item)
                _method_require(not isinstance(value, dict) or (item['op'] == 'remove' and parts[-1].startswith('@')), 'scope cannot replace a whole object; name its fields')
                _method_require(not isinstance(value, list) or (parts[-1] not in ('events', 'text_tracks', 'audio_tracks', 'compositions', 'methods', 'layers', 'joins', 'keyframes')
                                and not any(isinstance(row, (dict, list)) for row in value)), 'scope cannot target a collection; select a stable ID and field')
            _method_require(request['kind'] != 'markup', 'markup revision only adds Markdown blocks')
    # These bindings are transaction state, not additional approval records.
    original_inputs, reviews = _revision_receipts(root, project)
    revision = dict(request, narrative=narrative, instruction=instruction, base_artifacts={name: {'ref': row['ref'], 'sha256': row['sha256']} for name, row in documents.items()}, job_inputs=original_inputs,
                    validation_before=_revision_static_validation(root, project, documents)['errors'])
    revision['revision'] = digest(revision)[:16]
    state['review_scopes'] = reviews; state['open_revision'] = revision
    save_project(root, project)
    return {'status': 'revision_open', 'revision': revision['revision'], 'scope': scope, 'execution_blocked': True}


def _revision_derived(documents, baseline, revision):
    """Only deterministic binding values and assembly coordinates are derived."""
    derived = set()
    def assign(name, path, expected):
        locator = {'artifact': name, 'path': path}
        before = method_value(baseline['artifacts'], locator)
        actual = method_value(documents, locator)
        _method_require(digest(actual) in (digest(before), digest(expected)), 'derived field differs from computed result: ' + name + path)
        if digest(before) != digest(expected):
            method_value(documents, locator, expected, True); derived.add((name, path, 'replace'))
    # Extend/remove concrete binding destinations when approved grammar instances are added/removed.
    if revision['kind'] != 'method':
        import copy
        old_jobs = {j['composition_id']: j for j in baseline['artifacts']['composition-plan']['data']['compositions']}
        jobs = documents['composition-plan']['data']['compositions']
        if set(old_jobs) != {j['composition_id'] for j in jobs}:
            expected = copy.deepcopy(baseline['artifacts']['implementation-lock']['data'].get('parameter_bindings', []))
            for binding in expected:
                destinations = []
                for target in binding['targets']:
                    if target['artifact'] != 'composition-plan':
                        destinations.append(target); continue
                    parts = _method_parts(target['path']); prototype = old_jobs[parts[1].split('=', 1)[1]]
                    for job in jobs:
                        if (job['method_ids'], job['implementation_element_ids']) != (prototype['method_ids'], prototype['implementation_element_ids']):
                            continue
                        candidate = dict(target, path='/compositions/@composition_id=' + job['composition_id'] + '/' + '/'.join(parts[2:]))
                        _method_location(job, '/' + '/'.join(parts[2:]))
                        if candidate not in destinations: destinations.append(candidate)
                binding['targets'] = destinations
            assign('implementation-lock', '/parameter_bindings', expected)
    for binding in documents['implementation-lock']['data'].get('parameter_bindings', []):
        source = binding['source']
        try:
            old = method_value(baseline['artifacts'], source); new = method_value(documents, source)
        except ValueError:
            continue
        change = dict(source, op='replace')
        if digest(old) != digest(new) and _revision_in_scope(change, revision):
            for target in binding['targets']:
                assign(target['artifact'], target['path'], _method_bound_value(target, new))
    if 'timeline' in documents:
        from timeline_math import canonical_assembly_ranges
        old = baseline['artifacts']['timeline']['data']; new = documents['timeline']['data']
        # Raw source endpoints/order are declared changes; coordinates are never inferred from prose.
        identity = lambda event: {key: event.get(key) for key in ('event_id', 'kind', 'source_in_ms', 'source_out_ms', 'speed', 'out_in_frame', 'out_out_frame') if key in event and (event.get('kind') == 'card' or key not in ('out_in_frame', 'out_out_frame'))}
        if [identity(e) for e in old.get('events', [])] != [identity(e) for e in new.get('events', [])]:
            old_ids = {e['event_id'] for e in old.get('events', [])}
            ranges = canonical_assembly_ranges(new['events'], baseline['context']['output']['fps_num'], baseline['context']['output']['fps_den'])
            for event, frame in zip(new['events'], ranges):
                if event['event_id'] in old_ids:
                    for key, computed in (('out_in_frame', 'assembly_in_frame'), ('out_out_frame', 'assembly_out_frame')):
                        assign('timeline', '/events/@event_id=' + event['event_id'] + '/' + key, frame[computed])
            budget = old.get('duration_budget') or {}
            if type(budget.get('sum_transition_overlap_frames')) is int:
                total = sum(r['length_frames'] for r in ranges)
                assign('timeline', '/duration_budget/sum_event_frames', total)
                assign('timeline', '/duration_budget/computed_output_frames', total - budget['sum_transition_overlap_frames'])
    return derived


def revision_preview(root, project=None, prepared=False):
    import copy
    import visual_pipeline as production
    project = project or load_project(root); control(project)
    state, baseline = _method_baseline(root, project); revision = state.get('open_revision')
    _method_require(isinstance(revision, dict), 'no open revision')
    sealed = dict(revision); identity = sealed.pop('revision')
    _method_require(identity == digest(sealed)[:16] and revision['base_sha256'] == state['baseline']['sha256'], 'revision state/parent changed')
    _method_require(artifact(root, project['narrative_direction_ref']) == revision['narrative']
                    and _revision_instruction_artifact(root, revision['instruction_ref']) == revision['instruction'], 'revision Narrative/instruction changed; restore or restart from clean state')
    _method_require(digest(_method_context(project)) == digest(baseline['context']), 'revision cannot change project method context/refs')
    current = _method_documents(root, project, revision['base_artifacts'])
    for name, row in revision['base_artifacts'].items():
        _method_require(current[name]['ref'] == row['ref'], 'revision artifact ref changed: ' + name)
    parent = copy.deepcopy(baseline)
    # First plan confirmation can include execution documents not previously frozen.
    _method_require(set(current) <= set(parent['artifacts']), 'confirm the original plan before structural revisions')
    documents = copy.deepcopy(current)
    derived = _revision_derived(documents, parent, revision)
    changes = []
    markup = revision['kind'] == 'markup'
    for name, entry in documents.items():
        old = parent['artifacts'][name]['data']; new = entry['data']
        rows = revision_structured_diff(name, old, new)
        if markup and isinstance(old, str):
            strip = lambda text: re.sub(r'<!-- /?lvr:(?:param|container) [A-Za-z0-9_.-]+ -->', '', text)
            _method_require(strip(old) == strip(new), 'markup migration must preserve every original text byte')
            rows = [r for r in rows if r['path'] != '$outside']
        for row in rows:
            key = (name, row['path'], row['op'])
            row['classification'] = 'derived' if key in derived else ('in_scope' if _revision_in_scope(row, revision) else 'out_of_scope')
        if not rows and current[name]['sha256'] != parent['artifacts'][name]['sha256']:
            rows = [{'artifact': name, 'path': '$bytes', 'op': 'replace', 'classification': 'out_of_scope', 'before': parent['artifacts'][name]['sha256'], 'after': current[name]['sha256']}]
        changes += rows
    violations = [r for r in changes if r['classification'] == 'out_of_scope']
    if violations:
        summary = {'revision': identity, 'parent_sha256': revision['base_sha256'], 'instruction': revision['instruction'],
            'quote': revision['quote'], 'narrative': revision['narrative'], 'scope': revision['scope'], 'kind': revision['kind'],
            'actual_diff': changes, 'affected_compositions': [], 'removed_compositions': [],
            'current_artifacts': {name: {'ref': r['ref'], 'sha256': r['sha256']} for name, r in current.items()}}
        summary['diff_sha256'] = digest(summary); summary['status'] = 'LINEAGE_VIOLATION'
        if prepared:
            _method_require(False, 'out-of-scope diff: ' + '; '.join(r['artifact'] + ' ' + r['path'] for r in violations))
        return summary
    _method_rules(documents)
    if revision['kind'] != 'method':
        _method_require(method_contract_digest(documents, baseline['context'], baseline['grammar_catalog']) == baseline['method_digest']
                        and method_visual_digest(root, project) == baseline.get('visual_method_digest'), 'content revision changed the confirmed visual method')
    # job_input includes actual media/font/native dependencies; a method fingerprint never substitutes for it.
    plan = documents['composition-plan']['data']; actual_plan = current['composition-plan']['data']
    affected = []
    for job in plan['compositions']:
        actual = next(j for j in actual_plan['compositions'] if j['composition_id'] == job['composition_id'])
        inputs = production.job_input(root, project, actual_plan, actual)
        if revision['job_inputs'].get(job['composition_id']) != digest(inputs) or digest(job) != digest(actual):
            affected.append(job['composition_id'])
    removed = sorted(set(revision['job_inputs']) - {j['composition_id'] for j in plan['compositions']})
    from collections import Counter
    _method_require(isinstance(revision.get('validation_before'), list), 'revision predates validation snapshot; restore artifacts, cancel and reopen its scope')
    validation = _revision_static_validation(root, project, documents)
    validation['baseline_errors'] = revision['validation_before']
    validation['new_errors'] = list((Counter(validation['errors']) - Counter(revision['validation_before'])).elements())
    validation['resolved_errors'] = list((Counter(revision['validation_before']) - Counter(validation['errors'])).elements())
    generated = []
    for job in plan['compositions']:
        if job['composition_id'] not in affected:
            continue
        for key in JOB_OUTPUT_KEYS:
            if job.get(key):
                old = job[key]
                suffix = slug(job['composition_id'])[:30] + '-' + digest(job['composition_id'])[:8] + '-' + key.removesuffix('_ref')
                new = str(Path(old).parent / (identity + '-' + suffix + Path(old).suffix))
                _method_require(not contained(root, new).exists(), 'revision output already exists: ' + new)
                job[key] = new
                generated.append({'artifact': 'composition-plan', 'path': '/compositions/@composition_id=' + job['composition_id'] + '/' + key,
                    'op': 'replace', 'classification': 'derived', 'before': old, 'after': new})
    summary = {'revision': identity, 'parent_sha256': revision['base_sha256'], 'instruction': revision['instruction'],
        'quote': revision['quote'], 'narrative': revision['narrative'], 'scope': revision['scope'], 'kind': revision['kind'],
        'actual_diff': changes + generated, 'affected_compositions': sorted(affected), 'removed_compositions': removed,
        'current_artifacts': {name: {'ref': r['ref'], 'sha256': r['sha256']} for name, r in current.items()}, 'validation': validation}
    summary['diff_sha256'] = digest(summary)
    summary['status'] = 'blocked' if validation['new_errors'] else 'revision_ready_for_plan_confirmation'
    if prepared:
        _method_require(not violations, 'out-of-scope diff: ' + '; '.join(r['artifact'] + ' ' + r['path'] for r in violations))
        _method_require(not validation['new_errors'], 'revision introduces validation errors: ' + '; '.join(validation['new_errors']))
        return summary, documents, baseline
    return summary


def _confirm_revision(root, project, gate_ids, actor, confirmation_ref, quote, shown_refs, method_change, base_sha256, diff_sha256):
    import visual_pipeline as production
    state = project['workflow_control']['method_preservation']; revision = state['open_revision']
    normalized = lambda value: ' '.join((value or '').split())
    previous_plan = project['workflow_control']['confirmations'].get('plan') or {}
    _method_require(isinstance(confirmation_ref, str) and '#' in confirmation_ref,
                    'revision confirmation_ref must name an exact Markdown section with #section; whole-file confirmation refs can replay old approvals')
    _method_require(not _same_revision_section(root, confirmation_ref, revision['instruction_ref'])
                    and normalized(quote) != normalized(revision['quote']),
                    'a reviewed revision needs a new actual decision from a confirmation section, not its instruction')
    _method_require(not _same_revision_section(root, confirmation_ref, previous_plan.get('confirmation_ref')),
                    'a reviewed revision needs a new confirmation section, different from the previous plan approval')
    summary, documents, previous = revision_preview(root, project, True)
    is_method = revision['kind'] == 'method'
    _method_require(set(gate_ids or ()) == ({'plan', 'method'} if is_method else {'plan'})
                    and bool(method_change) == is_method, 'close this revision with plan, plus method/--method-change only for a method revision')
    previous_method = project['workflow_control']['confirmations'].get('method') or {}
    _method_require(not is_method or (base_sha256 == revision['base_sha256']
                                      and not _same_revision_section(root, confirmation_ref, previous_method.get('confirmation_ref'))),
                    'method revision requires current parent and a new actual decision section')
    _method_require(diff_sha256 == summary['diff_sha256'], 'confirmation must bind the exact displayed --diff-sha256; inspect revise again')
    _method_require(project['current_stage'] == 'D2', 'revision closure requires D2')
    original_project = (root/'project.json').read_text(); marker = contained(root, METHOD_BASELINE + '.applying')
    writes = {r['ref']: r['data'] if isinstance(r['data'], str) else json.dumps(r['data'], ensure_ascii=False, indent=2, allow_nan=False)+'\n' for name, r in documents.items()
              if digest(r['data']) != digest(_method_documents(root, project, [name])[name]['data'])}
    journal = {'base_sha256': revision['base_sha256'], 'revision': revision['revision'], 'project_before': original_project,
        'baseline_before': contained(root, METHOD_BASELINE).read_text(), 'files': {ref: {'before': contained(root, ref).read_text(), 'after': text} for ref, text in writes.items()}}
    with marker.open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(journal, ensure_ascii=False, allow_nan=False)+'\n')
    if ((root/'project.json').read_text() != original_project or any(artifact(root, row['ref'])['sha256'] != row['sha256'] for row in summary['current_artifacts'].values())
            or any(not contained(root, ref).is_file() or hashlib.sha256(contained(root, ref).read_bytes()).hexdigest() != sha for ref, sha in summary['validation']['inputs'].items())
            or artifact(root, project['narrative_direction_ref']) != revision['narrative'] or _revision_instruction_artifact(root, revision['instruction_ref']) != revision['instruction']):
        marker.unlink(); _method_require(False, 'revision changed during confirmation; no implicit merge')
    for ref, text in writes.items():
        target = contained(root, ref); pending = target.with_name(target.name+'.adapt-pending')
        _method_require(not pending.exists(), 'unfinished revision write')
        pending.write_text(text, encoding='utf-8'); pending.replace(target)
    production.composition_plan(root, project)
    replacements = {r['before']: r['after'] for r in summary['actual_diff'] if r['classification']=='derived' and r['artifact']=='composition-plan' and r['path'].split('/')[-1] in JOB_OUTPUT_KEYS}
    if project.get('visual_proof_ref') in replacements:
        project['visual_proof_ref'] = replacements[project['visual_proof_ref']]
    for key in ('visual_proof_refs', 'execution_reference_asset_refs'):
        if isinstance(project.get(key), list): project[key] = [replacements.get(ref, ref) for ref in project[key]]
    for key in gate_ids:
        current = evaluate(root, project)[key]
        _method_require(current.get('input_digest'), key + ': ' + current.get('reason', 'inputs incomplete'))
        expected = required_shown_refs(root, project, key)
        _method_require(not expected or isinstance(shown_refs, list) and set(expected) <= set(shown_refs), 'current shown artifacts are required for ' + key)
        record = {'actor': actor.strip(), 'confirmation_ref': confirmation_ref, 'quote': quote,
            'input_digest': current['input_digest'], 'revision_diff_sha256': summary['diff_sha256']}
        if expected: record['shown_artifacts'] = [artifact(root, ref) for ref in expected]
        if key == 'method':
            record['method_contract_digest'] = production.method_inputs(root, project)['method_contract']
            record['visual_method_digest'] = method_visual_digest(root, project)
        project['workflow_control']['confirmations'][key] = record
    project['execution_plan_status'] = 'confirmed'
    state.pop('open_revision')
    _method_write_checkpoint(root, project, documents, None if is_method else previous, summary)
    save_project(root, project); marker.unlink()
    return {'status': 'revision_committed', 'method_preserved': not is_method, 'diff_sha256': summary['diff_sha256'], 'workflow': report(root, project=project)}


def adapt_method(root, patch):
    """Apply a concrete Narrative-backed patch, inheriting everything else."""
    import copy
    import visual_pipeline as production
    project = load_project(root)
    original_project_text = (root / 'project.json').read_bytes().decode('utf-8')
    production.policy(project)
    baseline = method_guard(root, project, allow_narrative_change=True)
    _method_require(baseline is not None, 'confirm the current method before adaptation')
    inherited_plan = evaluate(root, project)['plan']['status'] == 'satisfied'
    state = project['workflow_control']['method_preservation']
    _method_require(isinstance(patch, dict) and set(patch) <= {'schema_version', 'base_sha256', 'narrative_sha256', 'instruction_ref', 'quote', 'changes', 'unchanged_execution_reason'}, 'unknown patch fields')
    _method_require(isinstance(patch, dict) and patch.get('schema_version') == '1.0'
                    and patch.get('base_sha256') == state['baseline']['sha256'], 'patch base is not the current effective version')
    narrative = artifact(root, project['narrative_direction_ref'])
    _method_require(patch.get('narrative_sha256') == narrative['sha256'], 'patch must bind the current Narrative bytes')
    instruction = artifact_bytes(root, patch.get('instruction_ref')).decode('utf-8')
    _method_require(isinstance(patch.get('quote'), str) and bool(patch['quote'].strip()) and patch['quote'] in instruction, 'patch needs an exact existing instruction quote')
    narrative_text = artifact_bytes(root, project['narrative_direction_ref']).decode('utf-8')
    documents = _method_documents(root, project, baseline['artifacts'])
    rules, bindings = _method_rules(documents)
    changes = patch.get('changes')
    _method_require(isinstance(changes, list), 'patch must list concrete parameter changes')
    if not changes:
        reason = patch.get('unchanged_execution_reason')
        technical_delta = any(row['sha256'] != baseline['artifacts'][name]['sha256'] for name, row in documents.items())
        _method_require((narrative != baseline['narrative'] or technical_delta) and isinstance(reason, str) and len(reason.strip()) >= 10
                        and reason in patch['quote'], 'empty patch requires an explicit instruction to preserve the execution parameters')
    seen = set()
    for change in changes:
        _method_require(isinstance(change, dict) and set(change) == {'slot', 'old', 'value', 'narrative_basis'}, 'patch changes need exact slot/old/value/narrative_basis fields')
        slot = change.get('slot')
        _method_require(slot in rules and slot not in seen, 'unknown/duplicate parameter slot: ' + str(slot))
        seen.add(slot)
        rule = rules[slot]
        _method_require(isinstance(change.get('narrative_basis'), str) and change['narrative_basis'].strip()
                        and change['narrative_basis'] in narrative_text, 'each change needs an exact current Narrative basis')
        _method_require('old' in change and digest(change['old']) == digest(method_value(documents, rule)), 'old parameter value does not match the baseline')
        _method_require('value' in change, 'patch requires the exact new parameter value')
        _method_check_value(rule, change['value'])
        connected = [b for b in bindings if b['source'] == {'artifact': rule['artifact'], 'path': rule['path']}]
        locations = [rule] + [t for binding in connected for t in binding['targets']]
        used_by = set()
        jobs = documents['composition-plan']['data']['compositions']
        for location in locations:
            if location['artifact'] in ('implementation-lock', 'visual-methods'):
                owner = _method_parts(location['path'])[1]
                used_by.update(job['composition_id'] for job in jobs
                    if (owner in job['implementation_element_ids'] if location['artifact'] == 'implementation-lock'
                        else owner.removeprefix('@method_id=') in job['method_ids']))
        mapped_to = {t['path'].split('/')[2].removeprefix('@composition_id=') for binding in connected
                     for t in binding['targets'] if _method_render_binding(t)}
        if used_by and digest(change['old']) != digest(change['value']):
            _method_require(used_by <= mapped_to, 'shared parameter lacks bindings for compositions ' + str(sorted(used_by - mapped_to)))
        method_value(documents, rule, change['value'], True)
        for binding in bindings:
            if binding['source'] == {'artifact': rule['artifact'], 'path': rule['path']}:
                for target in binding['targets']:
                    method_value(documents, target, _method_bound_value(target, change['value']), True)
    _method_rules(documents)
    _method_require(method_contract_digest(documents, baseline['context']) == baseline['method_digest'], 'adaptation changed the implementation method')
    plan = documents['composition-plan']['data']
    old_jobs = {j['composition_id']: j for j in baseline['artifacts']['composition-plan']['data']['compositions']}
    affected = [j['composition_id'] for j in plan['compositions'] if digest(j) != digest(old_jobs[j['composition_id']])]
    # A changed event/track also invalidates compositions that actually consume it.
    if 'timeline' in documents:
        old = baseline['artifacts']['timeline']['data']; new = documents['timeline']['data']
        fields = ('event_id', 'source_id', 'unit_id', 'source_in_ms', 'source_out_ms', 'speed',
                  'd2_selection_snapshot', 'source_signature', 'time_mapping_digest')
        old_events = {row['event_id']: {k: row.get(k) for k in fields} for row in old.get('events', [])}
        changed_events = {row['event_id'] for row in new.get('events', [])
                          if {k: row.get(k) for k in fields} != old_events.get(row['event_id'])}
        affected += [j['composition_id'] for j in plan['compositions'] if set(j['event_ids']) & changed_events]
    old_methods = {row['method_id']: digest(row) for row in baseline['artifacts']['visual-methods']['data']['methods']}
    changed_methods = {row['method_id'] for row in documents['visual-methods']['data']['methods']
                       if digest(row) != old_methods.get(row['method_id'])}
    affected += [job['composition_id'] for job in plan['compositions'] if set(job['method_ids']) & changed_methods]
    affected = sorted(set(affected))
    # Seal reusable review evidence before editing; never rewrite an old review's findings.
    review_scopes = dict(state.get('review_scopes') or {})
    current_plan = production.composition_plan(root, project)
    for job in current_plan['compositions']:
        if not contained(root, job.get('review_ref') or 'missing-review').is_file():
            continue
        try:
            receipt = production.validate_job_receipt(root, project, current_plan, job, require_proof=True)
            production.validate_review(root, project, job, receipt)
            review_scopes[job['composition_id']] = {
                'review_sha256': hashlib.sha256(contained(root, job['review_ref']).read_bytes()).hexdigest(),
                'job_digest': digest(production.job_input(root, project, current_plan, job)),
                'implementation_lock_sha256': next((row.get('implementation_lock_sha256') for row in read_json(contained(root, job['review_ref'])).get('checks', []) if row.get('name') == 'ReferenceCompliance'), None)}
        except (ValueError, OSError, TypeError, KeyError):
            continue
    state['review_scopes'] = review_scopes
    revision = digest({'base': patch['base_sha256'], 'narrative': narrative, 'changes': changes})[:12]
    replacements, reserved_outputs = {}, set()
    for job in plan['compositions']:
        if job['composition_id'] not in affected:
            continue
        for key in JOB_OUTPUT_KEYS:
            if job.get(key):
                old = job[key]
                identity = slug(job['composition_id'])[:30] + '-' + digest(job['composition_id'])[:8]
                new = str(Path(old).parent / (revision + '-' + identity + '-' + key.removesuffix('_ref') + Path(old).suffix))
                _method_require(new not in reserved_outputs, 'revised output paths collide')
                reserved_outputs.add(new)
                _method_require(not contained(root, new).exists(), 'revised output already exists: ' + new)
                job[key] = new; replacements[old] = new
    for key in ('visual_proof_ref',):
        if project.get(key) in replacements:
            project[key] = replacements[project[key]]
    for key in ('visual_proof_refs', 'execution_reference_asset_refs'):
        if isinstance(project.get(key), list):
            project[key] = [replacements.get(ref, ref) for ref in project[key]]
    # Verify the base again immediately before the first write (no implicit merge).
    method_guard(root, load_project(root), allow_narrative_change=True)
    marker = contained(root, METHOD_BASELINE + '.applying')
    _method_require(not marker.exists(), 'an earlier parameter patch was interrupted')
    writes = {}
    for name, row in documents.items():
        if digest(row['data']) != digest(baseline['artifacts'][name]['data']):
            writes[row['ref']] = row['data'] if isinstance(row['data'], str) else json.dumps(row['data'], ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    journal = {'base_sha256': patch['base_sha256'], 'revision': revision,
               'project_before': original_project_text, 'baseline_before': contained(root, METHOD_BASELINE).read_bytes().decode('utf-8'),
               'files': {ref: {'before': contained(root, ref).read_bytes().decode('utf-8'), 'after': value} for ref, value in writes.items()}}
    with marker.open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(journal, ensure_ascii=False, allow_nan=False) + '\n')
    # Under the exclusive marker, reject a simultaneous state/Narrative edit.
    if ((root / 'project.json').read_bytes().decode('utf-8') != original_project_text
            or artifact(root, project['narrative_direction_ref']) != narrative
            or any(hashlib.sha256(contained(root, row['ref']).read_bytes()).hexdigest() != row['sha256'] for row in documents.values())):
        marker.unlink()
        _method_require(False, 'the baseline changed while applying the patch; no implicit merge')
    for ref, data in writes.items():
        target = contained(root, ref)
        temporary = target.with_name(target.name + '.adapt-pending')
        _method_require(not temporary.exists(), 'unfinished artifact write: ' + str(temporary))
        temporary.write_text(data, encoding='utf-8'); temporary.replace(target)
    summary = {'revision': revision, 'parent_sha256': patch['base_sha256'], 'narrative': narrative,
               'instruction_ref': patch['instruction_ref'], 'quote': patch['quote'],
               'slots': sorted(seen), 'affected_compositions': affected,
               'changed_artifacts': [name for name in documents if digest(documents[name]['data']) != digest(baseline['artifacts'][name]['data'])]}
    _method_write_checkpoint(root, project, documents, baseline, summary)
    if inherited_plan:
        record = project['workflow_control']['confirmations']['plan']
        record['adaptation'] = {'parent_input_digest': record['input_digest'], 'patch_sha256': digest(summary)}
        record['input_digest'] = evaluate(root, project)['plan']['input_digest']
    save_project(root, project)
    marker.unlink()
    return {'status': 'applied', 'method_preserved': True, **summary,
            'workflow': report(root, project=project)}



def recover_method_patch(root):
    marker = contained(root, METHOD_BASELINE + '.applying')
    _method_require(marker.is_file(), 'no interrupted patch exists')
    journal = read_json(marker)
    _method_require(isinstance(journal, dict) and isinstance(journal.get('files'), dict)
                    and all(isinstance(journal.get(k), str) for k in ('project_before', 'baseline_before', 'revision')),
                    'invalid patch recovery journal')
    project_text = (root / 'project.json').read_bytes().decode('utf-8')
    project_pending = contained(root, 'project.json.workflow-tmp')
    if project_pending.exists():
        staged = read_json(project_pending)
        pending_state = staged.get('workflow_control', {}).get('method_preservation') or {}
        _method_require((pending_state.get('last_patch') or {}).get('revision') == journal['revision'],
                        'project temporary file belongs to another update; recovery will not overwrite it')
    project = load_project(root)
    baseline_pending = contained(root, METHOD_BASELINE + '.pending')
    if baseline_pending.exists():
        staged_baseline = read_json(baseline_pending)
        _method_require(staged_baseline.get('project_id') == project.get('project_id')
                        and staged_baseline.get('checkpoint_revision') == journal['revision'],
                        'baseline temporary file belongs to another update; recovery will not overwrite it')
    state = project.get('workflow_control', {}).get('method_preservation') or {}
    # A committed transaction with a leftover marker may be finished without rewriting artifacts.
    record = state.get('baseline') or {}
    if ((state.get('last_patch') or {}).get('revision') == journal['revision']
            and contained(root, METHOD_BASELINE).is_file()
            and hashlib.sha256(contained(root, METHOD_BASELINE).read_bytes()).hexdigest() == record.get('sha256')
            and all(contained(root, ref).read_bytes().decode('utf-8') == row['after'] for ref, row in journal['files'].items())):
        if project_pending.exists():
            project_pending.unlink()
        if baseline_pending.exists():
            baseline_pending.unlink()
        marker.unlink()
        method_guard(root, project)
        return {'status': 'recovered', 'result': 'completed_existing_commit'}
    _method_require(project_text == journal['project_before'], 'project changed independently; recovery will not overwrite it')
    for ref, row in journal['files'].items():
        _method_require(contained(root, ref).read_bytes().decode('utf-8') in (row['before'], row['after']),
                        'artifact changed independently; recovery will not overwrite it: ' + ref)
    for ref, row in journal['files'].items():
        contained(root, ref).write_text(row['before'], encoding='utf-8')
        pending = contained(root, ref).with_name(Path(ref).name + '.adapt-pending')
        if pending.exists():
            pending.unlink()
    contained(root, METHOD_BASELINE).write_text(journal['baseline_before'], encoding='utf-8')
    if project_pending.exists():
        project_pending.unlink()
    if baseline_pending.exists():
        baseline_pending.unlink()
    marker.unlink()
    if (project.get('workflow_control', {}).get('method_preservation') or {}).get('open_revision'):
        revision_preview(root, project)
    else:
        method_guard(root, project, allow_narrative_change=True)
    return {'status': 'recovered', 'result': 'restored_previous_baseline'}



def _legacy_plan_valid(root, project):
    timeline = read_json(contained(root, 'timeline.json'))
    old_inputs = {'plan_ref': project['execution_plan_ref'],
        'plan_without_step0_bookkeeping': strip_step0(artifact_bytes(root, project['execution_plan_ref']).decode('utf-8')),
        'planned_selection': [{key: row.get(key) for key in ('event_id', 'source_id', 'unit_id', 'd2_selection_snapshot')} for row in timeline.get('events', []) if row.get('kind') == 'source'],
        'text_tracks': timeline.get('text_tracks', []), 'output': project.get('output')}
    record = project['workflow_control']['confirmations'].get('plan')
    return record is not None and record.get('input_digest') == digest(old_inputs)


def adopt_confirmed_method(root):
    """Bind unchanged historical confirmation/receipts to the new projections."""
    import visual_pipeline as production
    project = load_project(root)
    production.policy(project)
    ctl = control(project)
    state = ctl.get('method_preservation')
    if isinstance(state, dict) and state.get('baseline'):
        record = state['baseline']; previous = read_json(contained(root, METHOD_BASELINE))
        _method_require(previous.get('schema_version') == '1.0' and not state.get('open_revision')
                        and not contained(root, METHOD_BASELINE + '.applying').exists(), 'adoption cannot replace a current/open baseline')
        _method_require(record.get('sha256') == artifact(root, METHOD_BASELINE)['sha256'], 'old baseline altered')
        old = ctl['confirmations'].get('method') or {}
        _method_require(old.get('actor') and old['actor'].lower() not in ('model', 'assistant', 'auto', 'script', 'system', 'unknown')
                        and old.get('quote') and old['quote'] in artifact_bytes(root, old.get('confirmation_ref')).decode('utf-8'), 'original actual method decision is required')
        signature = legacy_v1414_method_contract_digest(previous['artifacts'], previous['context'])
        _method_require(signature == previous['method_digest'] == old.get('method_contract_digest')
                        and old.get('visual_method_digest') == previous.get('visual_method_digest') == method_visual_digest(root, project), 'old method anchor differs')
        current = _method_documents(root, project, previous['artifacts'])
        _method_require(all(current[name]['ref'] == row['ref'] and current[name]['sha256'] == row['sha256'] for name, row in previous['artifacts'].items())
                        and digest(_method_context(project)) == digest(previous['context']) and artifact(root, project['narrative_direction_ref']) == previous['narrative'], 'old confirmed artifacts changed; restore them before migration')
        _method_require(old['input_digest'] == digest({'method_contract': signature, 'sources': artifact(root, 'sources.json')}), 'old method source inputs changed')
        if ctl['confirmations'].get('plan'):
            _method_require(_legacy_plan_valid(root, project), 'old Plan confirmation inputs changed')
            ctl['confirmations']['plan']['input_digest'] = evaluate(root, project)['plan']['input_digest']
        old['method_contract_digest'] = method_contract_digest(current, previous['context'])
        old['input_digest'] = digest({'method_contract': old['method_contract_digest'], 'sources': artifact(root, 'sources.json')})
        _method_write_checkpoint(root, project, current, revision={'kind': 'adopt_unchanged_v1414', 'parent_sha256': record['sha256']})
        save_project(root, project)
        return {'status': 'adopted', 'method_preserved': True, 'workflow': report(root, project=project)}
    _method_require(isinstance(state, dict) and state.get('baseline') is None
                    and not contained(root, METHOD_BASELINE).exists(), 'adoption cannot replace an existing baseline')
    old = ctl['confirmations'].get('method') or {}
    _method_require(old.get('actor') and old['actor'].lower() not in ('model', 'assistant', 'auto', 'script', 'system', 'unknown')
                    and old.get('quote') and old['quote'] in artifact_bytes(root, old.get('confirmation_ref')).decode('utf-8'),
                    'adoption requires the original real method confirmation')
    _method_require(old.get('input_digest') == digest(production.legacy_method_inputs(root, project)),
                    'old method inputs have changed; adoption cannot certify an edited project')
    plan = production.composition_plan(root, project)
    adopted = {}
    for job in plan['compositions']:
        path = contained(root, job['receipt_ref'])
        if not path.is_file():
            continue
        receipt = read_json(path)
        legacy_digest = digest(production.job_input(root, project, plan, job, scoped=False))
        if receipt.get('input_digest') == legacy_digest:
            adopted[job['composition_id']] = {'receipt_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'legacy_input_digest': legacy_digest, 'scope_digest': digest(production.job_input(root, project, plan, job))}
    state['adopted_receipts'] = adopted
    inputs = production.method_inputs(root, project)
    old['input_digest'] = digest(inputs)
    old['method_contract_digest'] = inputs['method_contract']
    old['visual_method_digest'] = method_visual_digest(root, project)
    names = set(METHOD_CORE)
    lock = read_json(contained(root, method_refs(project)['implementation-lock']))
    names.update(x['artifact'] for b in lock.get('parameter_bindings', []) for x in [b['source']] + b['targets'])
    names.update(row['artifact'] for row in lock.get('safe_adaptation', {}).get('allowed', []) if isinstance(row, dict))
    if ctl['confirmations'].get('plan'):
        _method_require(_legacy_plan_valid(root, project), 'confirmed Plan changed; restore its effective version before adoption')
        ctl['confirmations']['plan']['input_digest'] = evaluate(root, project)['plan']['input_digest']
        names.update(method_refs(project))
    _method_write_checkpoint(root, project, sorted(names), revision={'kind': 'adopt_unchanged_confirmed_method'})
    save_project(root, project)
    return {'status': 'adopted', 'method_preserved': True, 'adopted_receipts': sorted(adopted), 'workflow': report(root)}


def ensure_runtime_policies(project):
    project.setdefault('execution_policy', {})['method_preservation'] = METHOD_POLICY
    ctl = project.get('workflow_control')
    if isinstance(ctl, dict):
        ctl.setdefault('method_preservation', {'schema_version': '1.0', 'baseline': None, 'last_patch': None})
    project.setdefault('text_policy', {
        'schema_version': '1.0', 'enforcement': 'required',
        'min_glyph_height_ratio': {'original_subtitle': 0.045, 'creator_text': 0.055, 'chapter_card': 0.07},
        'max_lines': {'creator_text': 2}, 'max_chars_per_second': 4.5,
        'min_stable_hold_seconds': {'creator_text': 3.0, 'chapter_card': 3.0},
        'undersize_action': 'block_until_policy_changed_and_production_relocked',
        'key_content_avoidance': 'required_in_mockup_demo_and_qa'})
    project.setdefault('voiceover_policy', {
        'schema_version': '1.0', 'allowed': None, 'description': None, 'ref': None,
        'when_unspecified': 'voiceover_forbidden'})
    return project


def initialize(root):
    project = load_project(root)
    before_init = digest(project)
    project = ensure_runtime_policies(project)
    visual = project.get('visual_pipeline')
    if isinstance(visual, dict):
        visual.setdefault('implementation_lock_ref', 'implementation-lock.json')
    value = project.get('workflow_control')
    if isinstance(value, dict):
        version = value.get('schema_version')
        if version in (LEGACY_PROTOCOL, '1.1', '1.2'):
            # Upgrade only the control shell. Existing decisions, source evidence and stage stay untouched.
            value['schema_version'] = PROTOCOL
            value.setdefault('confirmations', {})
            value.setdefault('audio_choice', None)
            value.setdefault('visual_spec_refs', [])
            value.setdefault('visual_not_applicable_reason', None)
            value.setdefault('render_output_ref', None)
            value.setdefault('qa_ref', 'qa.json')
            value.setdefault('production_spec_refs', ['execution-reference.md#Production Lock'])
            value.setdefault('production_lock', None)
            project.setdefault('execution_policy', {})['workflow_gate_control'] = POLICY
            project['execution_policy']['visual_reference_routing_required_before_mockup'] = True
            project['execution_policy']['visual_reference_application_required_before_proof'] = True
            project['execution_policy']['implementation_lock_required_before_proof'] = True
            project['execution_policy']['shown_artifact_binding_required_for_visual_confirmations'] = True
            project['execution_policy']['production_lock_required_before_execute'] = True
            project['execution_policy']['text_runtime_policy_required'] = True
            project['execution_policy']['voiceover_runtime_policy_required'] = True
            save_project(root, project)
            control(project)
            return project
        control(project)
        if digest(project) != before_init:
            save_project(root, project)
        return project
    project['workflow_control'] = {'schema_version': PROTOCOL, 'confirmations': {},
        'audio_choice': None, 'visual_spec_refs': [], 'visual_not_applicable_reason': None,
        'production_spec_refs': ['execution-reference.md#Production Lock'], 'production_lock': None,
        'method_preservation': {'schema_version': '1.0', 'baseline': None, 'last_patch': None},
        'render_output_ref': None, 'qa_ref': 'qa.json'}
    policy = project.setdefault('execution_policy', {})
    policy['workflow_gate_control'] = POLICY
    policy['visual_reference_routing_required_before_mockup'] = True
    policy['visual_reference_application_required_before_proof'] = True
    policy['implementation_lock_required_before_proof'] = True
    policy['shown_artifact_binding_required_for_visual_confirmations'] = True
    policy['production_lock_required_before_execute'] = True
    policy['text_runtime_policy_required'] = True
    policy['voiceover_runtime_policy_required'] = True
    save_project(root, project)
    return project


def strip_step0(text):
    """D2 approval covers planned selection; allowed Step 0 bookkeeping is separate."""
    lines, result, level = text.splitlines(keepends=True), [], None
    for line in lines:
        heading = re.match(r'^(#{1,6})\s+(.+)', line)
        if heading and 'Execute Step 0' in heading[2]:
            level = len(heading[1])
            continue
        if level is not None and heading and len(heading[1]) <= level:
            level = None
        if level is None:
            result.append(line)
    return ''.join(result)


def required_shown_refs(root, project, key):
    """Artifacts that must have been surfaced for visual confirmations.

    This cannot prove a human actually looked at a file, but it prevents a
    generic downstream instruction such as "render video" from silently
    back-filling Mockup / Proof / Composition confirmation records with no
    displayed artifact binding.
    """
    if key == 'mockup':
        import visual_pipeline as production
        if production.enabled(project) and production.visual_stage_dir(project) is not None:
            return [row['ref'] for row in production.confirmed_visual_artifacts(root, project)]
        return [project.get('visual_mockup_ref')]
    if key == 'proof':
        import visual_pipeline as production
        if not production.enabled(project):
            return [project.get('visual_proof_ref')]
        return production.proof_display_refs(root, project)
    if key == 'composition':
        import visual_pipeline as production
        if not production.enabled(project):
            return []
        # Composition confirmation is the representative Production Proof Lock,
        # not a requirement to pre-render every planned Blender window.
        return production.proof_display_refs(root, project)
    return []


def evaluate(root, project=None):
    project = project if project is not None else load_project(root)
    ctl = control(project)
    state = project.get('structure_state', {})
    if not isinstance(state, dict):
        raise ValueError('structure_state must be an object')
    gates = {}

    def gate(key, ready, inputs=None, reason=''):
        gates[key] = {'id': key, 'label': LABELS[key][0], 'kind': 'confirmation' if key in MANUAL + PRODUCTION_MANUAL else 'verification',
            'status': 'satisfied' if ready else 'pending', 'reason': reason,
            'next_action': LABELS[key][1], 'input_digest': digest(inputs) if inputs is not None else None}

    def refs(paths):
        return [artifact(root, value) for value in paths]

    sources = read_json(root / 'sources.json', [])
    source_ok = isinstance(sources, list) and bool(sources) and all(isinstance(row, dict)
        and row.get('source_id') and row.get('version') and isinstance(row.get('time_mapping'), dict)
        and bool(row['time_mapping']) and type(row.get('duration_ms')) is int and row['duration_ms'] > 0 for row in sources)
    gate('source_ready', source_ok, reason='' if source_ok else '来源版本、时长或时间映射尚不完整。')
    for key, flags, paths in [
        ('broad_ready', ('broad_pass', 'content_map', 'minimum_information_floor'),
         ['frame-observations.csv', 'action-node-candidates.csv', 'structure-questions.csv', 'coverage.json', project.get('content_map_ref') or 'content-map.md']),
        ('detail_ready', ('directed_deep_pass', 'detail_intervals', 'speaker_adjudications', 'edit_boundaries'),
         ['detail-intervals.csv', 'deep-observations.csv', 'speaker-adjudications.csv', 'edit-boundaries.csv',
          project.get('keyframe_references_ref') or 'keyframe-references.json', project.get('execution_handoff_ref') or 'execution-handoff.md']),
    ]:
        try:
            refs(paths)
            ready = all(state.get(flag) in COMPLETE for flag in flags)
            gate(key, ready, reason='' if ready else '正式结构产物尚未标为完成；不以摘要代替。')
        except (ValueError, OSError) as exc:
            gate(key, False, reason=str(exc))

    timeline = read_json(root / 'timeline.json', {})
    if not isinstance(timeline, dict):
        raise ValueError('timeline.json must be an object')
    events = timeline.get('events', [])
    if not isinstance(events, list) or any(not isinstance(row, dict) for row in events):
        raise ValueError('timeline events must be an array of objects')
    selected = [row for row in events if row.get('kind') == 'source']

    def manual(key, builder, status_key=None):
        try:
            inputs = builder()
            gate(key, False, inputs)
            record = ctl['confirmations'].get(key)
            if record is None:
                gates[key]['reason'] = '尚未绑定可回查确认来源；已有确认只补引用，不要求重新决定。'
                return
            if not isinstance(record, dict) or not all(isinstance(record.get(k), str) and record[k].strip()
                    for k in ('actor', 'confirmation_ref', 'quote', 'input_digest')):
                raise ValueError('Malformed confirmation record for ' + key)
            if record['actor'].strip().lower() in ('assistant', 'model', 'system', 'auto', 'script', 'unknown'):
                raise ValueError('Automatic actors cannot supply a decision for ' + key)
            if record['quote'] not in artifact_bytes(root, record['confirmation_ref']).decode('utf-8'):
                raise ValueError('Confirmation excerpt is missing from its source for ' + key)
            expected_shown = required_shown_refs(root, project, key)
            if expected_shown:
                shown = record.get('shown_artifacts')
                if not isinstance(shown, list):
                    raise ValueError(key + ': current visual confirmation requires shown_artifacts')
                expected_bindings = [artifact(root, ref) for ref in expected_shown]
                if shown != expected_bindings:
                    raise ValueError(key + ': shown_artifacts do not bind the current displayed files')
            if record['input_digest'] != gates[key]['input_digest']:
                gates[key].update(status='stale', reason='相关方案、资源或参数已变化；旧确认不再覆盖当前输入。')
            elif status_key and project.get(status_key) != 'confirmed':
                gates[key]['reason'] = status_key + ' has not been confirmed'
            else:
                gates[key].update(status='satisfied', reason='', confirmed_by=record['actor'], confirmation_ref=record['confirmation_ref'])
        except (ValueError, TypeError, OSError) as exc:
            if key in gates and gates[key].get('input_digest'):
                gates[key].update(status='pending', reason=str(exc))
            else:
                gate(key, False, reason=str(exc))
            if key in PRODUCTION_MANUAL and key in ctl['confirmations']:
                gates[key]['status'] = 'stale'

    manual('direction', lambda: {'artifacts': refs([project.get('narrative_direction_ref')]),
        'source_scope': project.get('source_scope'), 'constraints': project.get('confirmed_constraints'),
        'sources': [{key: row.get(key) for key in ('source_id', 'version', 'time_mapping')} for row in sources if isinstance(row, dict)]}, 'narrative_direction_status')

    def audio_inputs():
        choice = ctl.get('audio_choice')
        if not isinstance(choice, dict) or choice.get('mode') not in AUDIO_MODES or not isinstance(choice.get('description'), str) or not choice['description'].strip():
            raise ValueError('先明确 audio_choice：音乐形式、声音处理方案及其原文位置。')
        return {'choice': choice, 'audio_policy': project.get('audio_policy'), 'artifacts': refs([choice.get('ref')])}
    manual('audio', audio_inputs)

    import visual_pipeline as production
    production_enabled = production.enabled(project)
    visual_na = project.get('visual_gate_status') == 'not_applicable'
    proof_waived = project.get('visual_gate_status') == 'proof_waived'
    if not production_enabled:
        gate('reference_routing', False, reason='未启用视觉制作，Visual Reference Routing 不适用。')
        gates['reference_routing']['status'] = 'not_applicable'
    elif visual_na:
        why = ctl.get('visual_not_applicable_reason')
        gate('reference_routing', False, reason='not_applicable 需要明确的适用范围及理由。')
        if isinstance(why, str) and why.strip():
            gates['reference_routing'].update(status='not_applicable', reason=why)
    else:
        try:
            routing_inputs = production.reference_routing_inputs(root, project)
            gate('reference_routing', True, routing_inputs)
        except (ValueError, TypeError, KeyError, OSError) as exc:
            gate('reference_routing', False, reason=str(exc))
    def visual_spec():
        values = ctl.get('visual_spec_refs')
        if not isinstance(values, list) or not values:
            raise ValueError('登记 visual_spec_refs，指向已展示的视觉规则原文（建议 Markdown 分节引用）。')
        return {'artifacts': refs(values), 'output': project.get('output')}
    if visual_na:
        why = ctl.get('visual_not_applicable_reason')
        for key in ('mockup', 'proof'):
            gate(key, False, reason='not_applicable 需要明确的适用范围及理由。')
            if isinstance(why, str) and why.strip():
                gates[key].update(status='not_applicable', reason=why)
    else:
        def mockup_inputs():
            if production_enabled and production.visual_stage_dir(project) is not None:
                report = production.visual_stage_report(root, project, 'V6-user-decision')
                return {'mockups': production.confirmed_visual_artifacts(root, project),
                        'visual_stage_decision': report['artifacts']['V6-user-decision'],
                        'visual_spec': visual_spec()}
            return {'mockup': refs([project.get('visual_mockup_ref')]), 'visual_spec': visual_spec()}
        manual('mockup', mockup_inputs)
        def proof_inputs():
            if gates['mockup']['status'] != 'satisfied':
                raise ValueError('先确认当前 Aesthetic Mockup，再确认其可执行 Proof。')
            proof_refs = production.proof_frame_refs(root, project) if production_enabled else [project.get('visual_proof_ref')]
            images = refs([project.get('visual_mockup_ref')] + proof_refs)
            for image in images[1:]:
                same = images[0]['sha256'] == image['sha256'] or images[0]['ref'] == image['ref']
                if same and not (production_enabled and production.proof_reuse_allowed(root, project, images[0]['ref'], image['ref'])):
                    raise ValueError('Mockup 与 Proof 内容相同/同文件时，必须声明 visual_proof_reuse 并绑定真实工程凭据。')
            if len({image['sha256'] for image in images[1:]}) != len(images[1:]):
                raise ValueError('多个代表性 Proof 必须绑定不同的实际文件。')
            capability = read_json(root / 'capability-map.json', {})
            rows = capability.get('capabilities', []) if isinstance(capability, dict) else []
            def contains(value, target):
                if isinstance(value, dict):
                    return any(contains(v, target) for v in value.values())
                if isinstance(value, list):
                    return any(contains(v, target) for v in value)
                return value == target
            actual = []
            for proof_ref in proof_refs:
                matches = [row for row in rows if isinstance(row, dict) and row.get('status') == 'available'
                    and row.get('actual_tool') and row.get('entrypoint')
                    and contains(row.get('output_mapping'), proof_ref)]
                if not matches:
                    raise ValueError('每个 Proof 都必须有最终 Execute 可用的 actual_tool + entrypoint 映射：' + str(proof_ref))
                for row in matches:
                    if row not in actual:
                        actual.append(row)
            result = {'images': images, 'visual_spec': visual_spec(), 'toolchain': actual}
            if production_enabled:
                proof_plan = production.composition_plan(root, project)
                proof_set = set(production.proof_composition_ids(proof_plan))
                proof_jobs = [row for row in proof_plan['compositions'] if row['composition_id'] in proof_set]
                result['implementation_lock'] = production.reference_application_inputs(root, project,
                    [x for row in proof_jobs for x in row['implementation_element_ids']],
                    [x for row in proof_jobs for x in row['method_ids']])
                result['display_artifacts'] = [artifact(root, ref) for ref in production.proof_display_refs(root, project)]
            else:
                result['display_artifacts'] = [artifact(root, project.get('visual_proof_ref'))]
            return result
        if proof_waived:
            waiver = ctl.get('proof_waiver')
            try:
                if not isinstance(waiver, dict):
                    raise ValueError('proof_waived requires workflow_control.proof_waiver')
                for key in ('actor', 'confirmation_ref', 'quote', 'reason', 'scope'):
                    if not isinstance(waiver.get(key), str) or not waiver[key].strip():
                        raise ValueError('proof_waiver requires ' + key)
                if waiver['actor'].strip().lower() in ('assistant','model','system','auto','script','unknown'):
                    raise ValueError('proof waiver must be an actual user/human decision')
                if waiver['scope'] != 'skip_proof_generation_and_review':
                    raise ValueError('proof waiver scope must be skip_proof_generation_and_review')
                if waiver['quote'] not in artifact_bytes(root, waiver['confirmation_ref']).decode('utf-8'):
                    raise ValueError('proof waiver quote must be an exact existing excerpt')
                gate('proof', True, {'waiver': waiver, 'visual_spec': visual_spec()})
                gates['proof'].update(status='satisfied', reason='Proof generation/review explicitly waived by user; final QA remains mandatory.',
                                      confirmed_by=waiver['actor'], confirmation_ref=waiver['confirmation_ref'])
            except (ValueError, TypeError, OSError) as exc:
                gate('proof', False, reason=str(exc))
        else:
            manual('proof', proof_inputs)
            if gates['proof']['status'] == 'satisfied' and project.get('visual_gate_status') != 'proof_confirmed':
                gates['proof'].update(status='pending', reason='visual_gate_status 尚未为 proof_confirmed。')

    def plan_inputs():
        ref = project.get('execution_plan_ref')
        path = contained(root, ref)
        artifact(root, ref)
        planned = [{key: row.get(key) for key in ('event_id', 'source_id', 'unit_id', 'd2_selection_snapshot')} for row in selected]
        return {'plan_ref': ref, 'plan_without_step0_bookkeeping': strip_step0(path.read_text(encoding='utf-8')),
            'planned_selection': planned, 'text_tracks': timeline.get('text_tracks', []), 'output': project.get('output'),
            'execution_package': refs([project['execution_reference_ref']] + [production.policy(project)[key] for key in ('methods_ref', 'implementation_lock_ref', 'composition_plan_ref')]) if production_enabled else None}
    manual('plan', plan_inputs, 'execution_plan_status')

    if production_enabled:
        manual('method', lambda: production.method_inputs(root, project))
        def composition_inputs():
            if gates['method']['status'] != 'satisfied':
                raise ValueError('先确认当前制作方法，再确认工程与动态样片。')
            return production.composition_inputs(root, project)
        if proof_waived:
            try:
                gate('composition', True, composition_inputs())
                gates['composition'].update(status='satisfied', reason='Representative composition review waived with Proof; plan remains locked for production.',
                                            confirmed_by=(ctl.get('proof_waiver') or {}).get('actor'),
                                            confirmation_ref=(ctl.get('proof_waiver') or {}).get('confirmation_ref'))
            except (ValueError, TypeError, KeyError, OSError) as exc:
                gate('composition', False, reason=str(exc))
        else:
            manual('composition', composition_inputs)

    if production_enabled:
        try:
            lock_inputs = production.production_lock_inputs(root, project)
            gate('production_lock', False, lock_inputs)
            record = ctl.get('production_lock')
            if not isinstance(record, dict) or record.get('schema_version') != '1.0' or not isinstance(record.get('input_digest'), str):
                gates['production_lock']['reason'] = 'Production Proof Lock 尚未生成当前实现指纹。'
            elif record['input_digest'] != gates['production_lock']['input_digest']:
                gates['production_lock'].update(status='stale', reason='工具链、关键视觉规则、工程、delivery spec、文字或旁白 policy 已变化；Production Lock 需重建。')
            else:
                gates['production_lock'].update(status='satisfied', reason='', confirmed_by=record.get('actor'), confirmation_ref=record.get('confirmation_ref'))
        except (ValueError, TypeError, KeyError, OSError) as exc:
            gate('production_lock', False, reason=str(exc))
    else:
        gate('production_lock', False, reason='未启用视觉制作，沿用现有授权与渲染入口约束。')
        gates['production_lock']['status'] = 'not_applicable'

    boundaries = {}
    path = root / 'edit-boundaries.csv'
    if path.is_file():
        with path.open(encoding='utf-8-sig', newline='') as handle:
            boundaries = {row.get('boundary_id'): row for row in csv.DictReader(handle)}
    range_ok = bool(selected) and all(isinstance(row.get('d2_selection_snapshot'), dict)
        and boundaries.get(row.get('adopted_boundary_ref') or row.get('edit_boundary_ref'), {}).get('boundary_status') == 'supported' for row in selected)
    gate('selected_ranges', range_ok, reason='' if range_ok else '入选 range 尚未具备 D2 snapshot 和 supported boundary；精确边界仍由原校验器核查。')
    ref = project.get('execution_authorization_ref')
    authorization = None
    try:
        token = artifact(root, ref)
        authorization = read_json(contained(root, ref))
        auth_ok = isinstance(authorization, dict) and authorization.get('status') == 'confirmed' and bool(authorization.get('confirmed_by'))
        auth_ok = auth_ok and digest(authorization) == project.get('execution_authorization_digest') and project.get('render_authorized') is True
        gate('authorization', auth_ok, reason='' if auth_ok else '原执行授权尚未确认或指纹不符；不由关口检查器代签。')
    except (ValueError, OSError) as exc:
        gate('authorization', False, reason=str(exc))
    output_token = None
    try:
        output_token = artifact(root, ctl.get('render_output_ref'))
        if production_enabled:
            delivery = production.verify_delivery_receipt(root, project)
            if delivery['artifact'] != output_token:
                raise ValueError('QA 入口必须指向当前 FFmpeg delivery receipt 的成片。')
        gate('render_result', True)
    except (ValueError, OSError) as exc:
        gate('render_result', False, reason=str(exc))
    try:
        qa_reason = ''
        qa = read_json(contained(root, ctl.get('qa_ref') or 'qa.json'))
        checks = qa.get('checks', []) if isinstance(qa, dict) else []
        qa_ok = bool(checks) and isinstance(checks, list) and all(isinstance(row, dict)
            and row.get('status') in ('pass', 'not_applicable') and bool(row.get('method'))
            and (bool(row.get('evidence')) if row.get('status') == 'pass' else bool(row.get('finding'))) for row in checks)
        required_names = QA_NAMES | (set(production.FINAL_CHECKS) if production_enabled else set())
        qa_ok = qa_ok and required_names.issubset({row.get('name') for row in checks})
        if production_enabled:
            qa_ok = qa_ok and all(any(row.get('name') == name and row.get('status') == 'pass'
                                     for row in checks) for name in production.FINAL_CHECKS)
            ref_check = next((row for row in checks if row.get('name') == 'ReferenceCompliance'), None)
            if isinstance(ref_check, dict):
                selected_refs = production.selected_reference_ids(root, project)
                lock_ref = project['visual_pipeline']['implementation_lock_ref']
                proof_refs = production.proof_frame_refs(root, project)
                mockups = production.confirmed_visual_artifacts(root, project)
                required_refs = {x['ref'] for x in mockups} | {lock_ref, *proof_refs}
                if production.visual_stage_dir(project) is not None:
                    required_refs.add(production.visual_stage_report(root, project, 'V7-lock')['artifacts']['V7-lock']['ref'])
                evidence = ref_check.get('evidence')
                qa_ok = qa_ok and ref_check.get('status') == 'pass'
                qa_ok = qa_ok and isinstance(evidence, list) and required_refs.issubset(set(evidence))
                qa_ok = qa_ok and ref_check.get('reference_ref_ids') == selected_refs
                if production.visual_stage_dir(project) is None and len(mockups) == 1:
                    qa_ok = qa_ok and ref_check.get('mockup_sha256') == mockups[0]['sha256']
                else:
                    qa_ok = qa_ok and ref_check.get('mockup_sha256s') == {x['ref']: x['sha256'] for x in mockups}
                if len(proof_refs) == 1:
                    qa_ok = qa_ok and ref_check.get('proof_sha256') == artifact(root, proof_refs[0])['sha256']
                else:
                    expected_proof_hashes = {ref: artifact(root, ref)['sha256'] for ref in proof_refs}
                    qa_ok = qa_ok and ref_check.get('proof_sha256s') == expected_proof_hashes
                qa_ok = qa_ok and ref_check.get('implementation_lock_sha256') == artifact(root, lock_ref)['sha256']
            else:
                qa_ok = False
            if qa_ok:
                try:
                    production.validate_final_composition_qa(root, project, checks)
                except (ValueError, TypeError, KeyError, OSError) as exc:
                    qa_ok = False
                    qa_reason = str(exc)
        qa_ok = qa_ok and qa.get('final_playback_verified') is True and qa.get('blocking_issues') == []
        qa_ok = qa_ok and output_token is not None and qa.get('artifact_sha256') == output_token['sha256']
        qa_ok = qa_ok and qa.get('project_id') == project.get('project_id') and any(row.get('name') == 'ReferenceCompliance' for row in checks)
        gate('qa', bool(qa_ok), reason='' if qa_ok else (qa_reason or '当前成片的实际播放、ReferenceCompliance 或成片指纹尚未闭合。'))
    except (ValueError, TypeError, OSError) as exc:
        gate('qa', False, reason=str(exc))
    return gates


def report(root, action='resume', project=None):
    project = project if project is not None else load_project(root)
    lineage_error = None
    try:
        method_guard(root, project)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        lineage_error = str(exc)
    gates = evaluate(root, project)
    if action not in ACTIONS and action not in ('resume', 'partial_handoff'):
        raise ValueError('Unknown dependent action: ' + action)
    required = list(ACTIONS.get(action, PHASE_GATES[BLOCK[project['current_stage']]]))
    import visual_pipeline as production
    if production.enabled(project):
        if action in ('make_proof', 'build_composition'):
            required.append('method')
        elif action in ('execute_handoff', 'authorize', 'render', 'qa_start', 'deliver_complete'):
            required.extend(PRODUCTION_MANUAL)
        elif action in ('resume', 'partial_handoff') and BLOCK[project['current_stage']] >= 3:
            required.extend(PRODUCTION_MANUAL)
        order = ('source_ready', 'broad_ready', 'direction', 'detail_ready', 'audio',
                 'reference_routing', 'mockup', 'method', 'proof', 'composition', 'plan',
                 'production_lock', 'selected_ranges', 'authorization', 'render_result', 'qa')
        required = [key for key in order if key in required]
    pending = [gates[key] for key in required if gates[key]['status'] not in ('satisfied', 'not_applicable')]
    revision_diff = None
    if (project.get('workflow_control', {}).get('method_preservation') or {}).get('open_revision'):
        try:
            revision_diff = revision_preview(root, project)
        except (ValueError, TypeError, KeyError, OSError) as exc:
            revision_diff = {'status': 'LINEAGE_VIOLATION', 'error': str(exc)}
    return {'status': 'blocked' if (pending or lineage_error) and action in ACTIONS else ('open' if pending or lineage_error else 'clear'),
        'project_id': project.get('project_id'), 'current_stage': project['current_stage'], 'action': action,
        'action_allowed': not pending and not lineage_error if action in ACTIONS else True,
        'lineage_error': lineage_error, 'method_preservation': project.get('workflow_control', {}).get('method_preservation'), 'revision_diff': revision_diff,
        'next_gate': pending[0]['id'] if pending else None, 'pending_gates': pending,
        'required_gates': list(required), 'gates': list(gates.values()),
        'must_surface': bool(pending or lineage_error), 'scope': 'record and file checks; not proof of actual human approval or media observation'}


def require_action(root, action):
    project = load_project(root)
    import visual_pipeline as production
    if production.enabled(project):
        production.policy(project)
    if not enabled(project):
        # Preserve pre-1.9 legacy behavior until a project explicitly adopts the v1.4.1 production path.
        # Current self-use projects (schema 1.9+ / visual_pipeline) may not use this as an execution bypass.
        from versioning import version_at_least
        current_pipeline = 'visual_pipeline' in project
        try:
            current_pipeline = current_pipeline or version_at_least(project.get('schema_version', '0'), '1.9')
        except ValueError:
            current_pipeline = False  # let the original schema validator report malformed legacy versions
        if current_pipeline and (BLOCK.get(project.get('current_stage'), 0) >= 3 or action in ('build_composition', 'execute_handoff', 'authorize', 'render', 'qa_start', 'deliver_complete')):
            raise ValueError('Run workflow_control.py init before D2 / Execute')
        return None
    result = report(root, action, project)
    if not result['action_allowed']:
        raise ValueError((result.get('lineage_error') + '; ' if result.get('lineage_error') else '') + 'Workflow gate blocks ' + action + ': ' + '; '.join(row['id'] + ' — ' + row['reason'] for row in result['pending_gates']))
    # Reuse the existing evidence validator, rather than trusting completion flags.
    # validation_errors() above only calls report(), so this does not recurse.
    from validate_project import validate
    static = validate(root, render_checks=action in ('render', 'qa_start', 'deliver_complete'))
    if static['errors']:
        raise ValueError('Existing static validation blocks ' + action + ': ' + '; '.join(static['errors'][:8]))
    return result


def validation_errors(root, project, timeline):
    import visual_pipeline as production
    if production.enabled(project):
        try:
            production.policy(project)
        except (ValueError, TypeError, KeyError, OSError) as exc:
            return ['visual_pipeline: ' + str(exc)]
    if not enabled(project):
        return []
    try:
        control(project)
        method_guard(root, project)
        if timeline.get('status') == 'ready_for_render':
            result = report(root, 'render', project)
            return ([result['lineage_error']] if result.get('lineage_error') else []) + ['workflow_control: ' + row['id'] + ': ' + row['reason'] for row in result['pending_gates']]
    except (ValueError, TypeError, KeyError, OSError) as exc:
        return ['workflow_control: ' + str(exc)]
    return []


def confirm(root, gate_ids, actor, confirmation_ref, quote, shown_refs=None, method_change=False, base_sha256=None, diff_sha256=None):
    if not isinstance(actor, str) or not actor.strip() or actor.strip().lower() in ('assistant', 'model', 'system', 'auto', 'script', 'unknown'):
        raise ValueError('Record the actual decision maker, not an automatic confirmation')
    project = load_project(root)
    ctl = control(project)
    confirmation_text = artifact_bytes(root, confirmation_ref).decode('utf-8')
    if not isinstance(quote, str) or not quote.strip() or quote not in confirmation_text:
        raise ValueError('An exact existing confirmation excerpt is required; do not manufacture one')
    import visual_pipeline as production
    allowed = MANUAL + (PRODUCTION_MANUAL if production.enabled(project) else ())
    if not gate_ids or any(key not in allowed for key in gate_ids):
        raise ValueError('Only applicable decisions can be recorded: ' + ', '.join(allowed))
    previous = None
    if production.enabled(project):
        if (ctl.get('method_preservation') or {}).get('open_revision'):
            return _confirm_revision(root, project, gate_ids, actor, confirmation_ref, quote, shown_refs, method_change, base_sha256, diff_sha256)
        _method_require(diff_sha256 is None, 'no revision is open for this diff confirmation')
        if method_change:
            _method_require(False, 'method changes require an existing D2 scoped revise before any edits; old approval cannot unlock a new method')
        else:
            previous = method_guard(root, project)
    # Prepare the complete update in memory. Failure cannot leave half a batch saved.
    for key in gate_ids:
        current = evaluate(root, project)[key]
        if not current.get('input_digest') or current['status'] == 'not_applicable':
            raise ValueError(key + ': ' + current['reason'])
        expected_shown = required_shown_refs(root, project, key)
        shown_artifacts = []
        if expected_shown:
            if not isinstance(shown_refs, list):
                raise ValueError(key + ': --shown-ref is required for the current displayed visual artifacts')
            missing = [ref for ref in expected_shown if ref not in shown_refs]
            if missing:
                raise ValueError(key + ': missing required --shown-ref: ' + ', '.join(missing))
            shown_artifacts = [artifact(root, ref) for ref in expected_shown]
        record = {'actor': actor.strip(), 'confirmation_ref': confirmation_ref,
            'quote': quote, 'input_digest': current['input_digest']}
        if key == 'method':
            record['method_contract_digest'] = production.method_inputs(root, project)['method_contract']
            record['visual_method_digest'] = method_visual_digest(root, project)
        if shown_artifacts:
            record['shown_artifacts'] = shown_artifacts
        ctl['confirmations'][key] = record
        if key == 'direction':
            project['narrative_direction_status'] = 'confirmed'
        elif key == 'plan':
            project['execution_plan_status'] = 'confirmed'
        elif key == 'mockup':
            project['visual_gate_status'] = 'mockup_confirmed'
        elif key == 'proof':
            project['visual_gate_status'] = 'proof_confirmed'
    # Once Proof + Composition are both valid, the same decision cycle must produce an implementation lock.
    if production.enabled(project):
        post = evaluate(root, project)
        if post.get('proof', {}).get('status') == 'satisfied' and post.get('composition', {}).get('status') == 'satisfied':
            lock_inputs = production.production_lock_inputs(root, project)
            ctl['production_lock'] = {'schema_version': '1.0', 'input_digest': digest(lock_inputs),
                'actor': actor.strip(), 'confirmation_ref': confirmation_ref, 'quote': quote}
    if production.enabled(project) and ('method' in gate_ids or ('plan' in gate_ids and previous)):
        names = set(previous['artifacts'] if previous else METHOD_CORE)
        lock = read_json(contained(root, method_refs(project)['implementation-lock']))
        names.update(x['artifact'] for b in lock.get('parameter_bindings', []) for x in [b['source']] + b['targets'])
        names.update(row['artifact'] for row in lock.get('safe_adaptation', {}).get('allowed', []) if isinstance(row, dict))
        if 'plan' in gate_ids:
            names.update(method_refs(project))
        _method_write_checkpoint(root, project, sorted(names), None if method_change else previous,
                                 {'kind': 'explicit_method_change', 'parent_sha256': base_sha256, 'actor': actor, 'confirmation_ref': confirmation_ref, 'quote': quote} if method_change else None)
    save_project(root, project)
    return report(root, project=project)


def waive_proof(root, actor, confirmation_ref, quote, reason):
    if not isinstance(actor, str) or not actor.strip() or actor.strip().lower() in ('assistant','model','system','auto','script','unknown'):
        raise ValueError('Record the actual decision maker for a Proof waiver')
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError('Proof waiver requires a concrete reason')
    project = load_project(root)
    ctl = control(project)
    text = artifact_bytes(root, confirmation_ref).decode('utf-8')
    if not isinstance(quote, str) or not quote.strip() or quote not in text:
        raise ValueError('An exact existing user/human waiver excerpt is required; do not manufacture one')
    if project.get('visual_gate_status') == 'not_applicable':
        raise ValueError('not_applicable and proof_waived are different states')
    # A waiver skips only representative Proof generation/review. It does not
    # waive method, plan, selected ranges, authorization, render-result or QA.
    ctl['proof_waiver'] = {'schema_version':'1.0','actor':actor.strip(),
        'confirmation_ref':confirmation_ref,'quote':quote,'reason':reason.strip(),
        'scope':'skip_proof_generation_and_review'}
    project['visual_gate_status'] = 'proof_waived'
    ctl.get('confirmations', {}).pop('proof', None)
    ctl.get('confirmations', {}).pop('composition', None)
    ctl['production_lock'] = None
    save_project(root, project)
    return report(root, project=project)


def _walk_refs(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _walk_refs(item)


def portable_artifact_refs(root, project, handoff_output=None):
    refs = set(PORTABLE_ARTIFACTS)
    for key in PROJECT_REF_KEYS:
        refs.update(_walk_refs(project.get(key)))
    refs.update(_walk_refs(project.get('execution_reference_asset_refs')))
    if isinstance(project.get('visual_pipeline'), dict):
        for key, value in project['visual_pipeline'].items():
            if key.endswith('_ref') or key.endswith('_refs'):
                refs.update(_walk_refs(value))
    # keyframe-references may point to actual images that must travel with the handoff.
    kref = project.get('keyframe_references_ref') or 'keyframe-references.json'
    try:
        data = read_json(contained(root, kref), {})
        rows = data if isinstance(data, list) else data.get('keyframes', []) if isinstance(data, dict) else []
        for row in rows:
            if isinstance(row, dict):
                for key in ('image_ref', 'asset_ref', 'path'):
                    if isinstance(row.get(key), str) and row[key].strip():
                        refs.add(row[key])
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass
    cleaned = []
    for ref in refs:
        if not isinstance(ref, str) or not ref.strip() or '#' in ref and not ref.split('#', 1)[0].strip():
            continue
        base = ref.split('#', 1)[0]
        if handoff_output and base == handoff_output.split('#', 1)[0]:
            continue
        try:
            path = contained(root, base)
        except ValueError:
            continue
        if path.is_file() and path.name != 'project.json':
            cleaned.append(base)
    return sorted(set(cleaned))


def handoff_snapshot(root, project, handoff_output=None):
    # last_handoff is derived bookkeeping; excluding it avoids a circular digest.
    clone = json.loads(json.dumps(project, ensure_ascii=False))
    ctl = clone.get('workflow_control')
    if isinstance(ctl, dict):
        ctl.pop('last_handoff', None)
    artifacts = []
    for ref in portable_artifact_refs(root, project, handoff_output):
        try:
            token = artifact(root, ref)
            token['size_bytes'] = contained(root, ref).stat().st_size
            artifacts.append(token)
        except (OSError, ValueError):
            continue
    return {'project': clone, 'artifacts': artifacts}


def source_transfer_rows(root):
    path = root / 'sources.json'
    data = read_json(path, [])
    if isinstance(data, dict):
        rows = data.get('sources', [])
    else:
        rows = data
    out = []
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append({
            'source_id': row.get('source_id') or row.get('id') or 'unknown',
            'signature': row.get('source_signature') or row.get('signature') or row.get('version') or 'unknown',
            'time_mapping': row.get('time_mapping') or 'unknown',
            'locator': row.get('locator') or row.get('path') or row.get('url') or 'unknown',
        })
    return out


def ensure_current_handoff(root, project):
    ctl = control(project)
    record = ctl.get('last_handoff')
    if not isinstance(record, dict):
        raise ValueError('Current stage must generate a next-step handoff before advancing')
    if record.get('stage') != project.get('current_stage'):
        raise ValueError('Next-step handoff belongs to a different stage; regenerate handoff before advancing')
    ref = record.get('ref')
    if not isinstance(ref, str) or not ref.strip():
        raise ValueError('Next-step handoff has no project-relative file ref')
    path = contained(root, ref)
    if not path.is_file():
        raise ValueError('Next-step handoff file is missing: ' + ref)
    current_snapshot = digest(handoff_snapshot(root, project, ref))
    if current_snapshot != record.get('state_digest'):
        raise ValueError('Project or handoff artifacts changed after the last handoff; regenerate handoff before advancing')
    if hashlib.sha256(path.read_bytes()).hexdigest() != record.get('sha256'):
        raise ValueError('Next-step handoff file changed after generation; regenerate handoff before advancing')
    return record


def handoff(root, output):
    target = contained(root, output)
    if target.suffix.lower() != '.md' or target == root / 'project.json':
        raise ValueError('Handoff output must be a project-relative Markdown file')
    project = load_project(root)
    control(project)
    project['handoff_ref'] = output
    result = report(root, 'partial_handoff', project)
    snapshot = handoff_snapshot(root, project, output)
    state_digest = digest(snapshot)

    lines = [BEGIN, '## Workflow Checkpoints · 续接关口', '',
        '- 项目：' + str(result['project_id']), '- 当前大阶段：' + result['current_stage'],
        '- 接手方式：先读取 project.json 的 workflow_control；未完成关口随包保留，不因换主体、对话或模型自动关闭。',
        '- 下一关口：' + str(result['next_gate'] or '当前块已闭合；按原流程进入下一块'), '',
        '| 关口 | 状态 | 确认来源 / 缺口 | 下一步 |', '|---|---|---|---|']
    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')
    for row in result['gates']:
        lines.append('| ' + ' | '.join(cell(value) for value in (row['label'], row['status'], row.get('confirmation_ref') or row['reason'], row['next_action'])) + ' |')
    lines += ['', '未通过关口只阻断依赖动作；可继续无关准备。partial handoff 是交接进度，不是下一阶段的执行许可。', END]
    checkpoint_section = '\n'.join(lines)

    delivery = [DELIVERY_BEGIN, '## Next-Step Delivery · 跨模型 / 跨机器交付', '',
        '- 交付阶段：' + str(project.get('current_stage')),
        '- project.json：必须随包交付；接收方以其中 workflow_control 为机器状态源。',
        '- 状态快照 digest：`' + state_digest + '`',
        '- 续接原则：接收方只复用已记录事实与确认；不得把上一模型摘要当作直接观察。',
        '- 换机器：旧的绝对素材路径只作 locator。若路径变化，按 `source_signature + time_mapping` 重新绑定源媒体；不得仅凭旧路径继续精确执行。', '',
        '### 实际随附文件清单', '',
        '| 文件 | SHA-256 | bytes |', '|---|---|---:|']
    for row in snapshot['artifacts']:
        delivery.append('| `' + row['ref'].replace('|', '\\|') + '` | `' + row['sha256'] + '` | ' + str(row['size_bytes']) + ' |')
    if not snapshot['artifacts']:
        delivery.append('| none | n/a | 0 |')
    sources = source_transfer_rows(root)
    delivery += ['', '### 源媒体重绑定信息', '', '| source_id | source_signature | time_mapping | 当前 locator |', '|---|---|---|---|']
    if sources:
        for row in sources:
            delivery.append('| ' + ' | '.join(cell(row[key]) for key in ('source_id', 'signature', 'time_mapping', 'locator')) + ' |')
    else:
        delivery.append('| unknown | unknown | unknown | `sources.json` 未提供可解析来源；接收方不得猜测 |')
    delivery += ['', '### 下一步接手顺序', '',
        '1. 读取本 handoff 与 `project.json`，恢复当前阶段、Scope Lock、有效确认及 pending/stale 项。',
        '2. 校验随附文件可读；需要精确执行时按上表 SHA-256 核对关键文件。',
        '3. 若换机器导致源 locator 改变，先按 source signature / time mapping 重绑定，再做依赖源媒体的动作。',
        '4. 只执行 handoff 指向的下一阶段；缺文件或工具时只暂停依赖动作，不重建已确认状态。',
        DELIVERY_END]
    delivery_section = '\n'.join(delivery)

    original = target.read_text(encoding='utf-8') if target.exists() else '# Handoff\n'
    def replace_section(text, begin, end, section):
        if begin in text or end in text:
            if text.count(begin) != 1 or text.count(end) != 1 or text.index(begin) > text.index(end):
                raise ValueError('Malformed handoff markers; preserve the file and inspect')
            before, rest = text.split(begin, 1)
            _, after = rest.split(end, 1)
            return before + section + after
        return text + ('\n' if text.endswith('\n') else '\n\n') + section + '\n'
    updated = replace_section(original, BEGIN, END, checkpoint_section)
    updated = replace_section(updated, DELIVERY_BEGIN, DELIVERY_END, delivery_section)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(updated, encoding='utf-8')
    record = {'stage': project.get('current_stage'), 'ref': output,
              'state_digest': state_digest, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
    project['workflow_control']['last_handoff'] = record
    save_project(root, project)
    result['handoff'] = record
    return result

def advance(root, target_stage, reason=None):
    project = load_project(root)
    control(project)
    current = BLOCK[project['current_stage']]
    target = BLOCK[target_stage]
    if target == current + 1:
        require_action(root, EXIT_ACTIONS[current])
        # Stage completion must be portable before crossing to the next major block.
        # This is an exit invariant, not a new approval Gate.
        project = load_project(root)
        ensure_current_handoff(root, project)
    elif target < current:
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError('Returning to an earlier block requires the concrete conflict/reason')
        project['workflow_control']['return_reason'] = reason
    elif target != current:
        raise ValueError('Do not skip major blocks; provide existing evidence and confirmations instead')
    project['current_stage'] = target_stage
    save_project(root, project)
    return report(root, project=project)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('init', 'status', 'guard', 'confirm', 'waive-proof', 'handoff', 'advance', 'adapt', 'recover-adaptation', 'adopt-method', 'revise'))
    parser.add_argument('project_directory', type=Path)
    parser.add_argument('--action', choices=tuple(ACTIONS), default='render')
    parser.add_argument('--gates', nargs='+', choices=MANUAL + PRODUCTION_MANUAL)
    parser.add_argument('--actor')
    parser.add_argument('--confirmation-ref')
    parser.add_argument('--quote')
    parser.add_argument('--reason')
    parser.add_argument('--shown-ref', nargs='*')
    parser.add_argument('--output', default='handoff.md')
    parser.add_argument('--to', choices=STAGES)
    parser.add_argument('--patch', type=Path)
    parser.add_argument('--method-change', action='store_true')
    parser.add_argument('--base-sha256')
    parser.add_argument('--diff-sha256')
    parser.add_argument('--scope', type=Path)
    parser.add_argument('--cancel', action='store_true')
    args = parser.parse_args()
    try:
        root = args.project_directory.resolve()
        if args.command == 'init':
            result = report(root, project=initialize(root))
        elif args.command == 'status':
            result = report(root)
        elif args.command == 'guard':
            if not enabled(load_project(root)):
                raise ValueError('Run init to adopt workflow control before using its guard')
            result = report(root, args.action)
            if result['action_allowed']:
                require_action(root, args.action)
        elif args.command == 'confirm':
            result = confirm(root, args.gates, args.actor, args.confirmation_ref, args.quote, args.shown_ref, args.method_change, args.base_sha256, args.diff_sha256)
        elif args.command == 'waive-proof':
            result = waive_proof(root, args.actor, args.confirmation_ref, args.quote, args.reason)
        elif args.command == 'revise':
            result = revise(root, read_json(args.scope) if args.scope else None, args.cancel)
        elif args.command == 'adopt-method':
            result = adopt_confirmed_method(root)
        elif args.command == 'recover-adaptation':
            result = recover_method_patch(root)
        elif args.command == 'adapt':
            if args.patch is None:
                raise ValueError('--patch is required')
            result = adapt_method(root, read_json(args.patch))
        elif args.command == 'handoff':
            result = handoff(root, args.output)
        else:
            if args.to is None:
                raise ValueError('--to is required')
            result = advance(root, args.to, args.reason)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if result['status'] in ('blocked', 'LINEAGE_VIOLATION') else 0
    except (ValueError, TypeError, KeyError, OSError, csv.Error) as exc:
        print(json.dumps({'status': 'error', 'action_allowed': False, 'error': str(exc)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
