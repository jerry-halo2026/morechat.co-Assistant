#!/usr/bin/env python3
"""Method -> Blender engineering -> reviewed motion proof -> FFmpeg delivery.

Checks files, media and decision bindings. Never supplies aesthetic judgments
or user confirmations. All intervals are zero-based, left-closed/right-open.
"""
import argparse
import csv
import hashlib
import json
import math
import os
import re
from pathlib import Path
import shutil
import subprocess
from fractions import Fraction

POLICY = 'method_blender_demo_v1'
PACKAGE_ROOT = Path(__file__).resolve().parent.parent
# One asset library includes the preserved host-hardened V0-V7 runtime.
REFERENCE_PACKAGE = PACKAGE_ROOT / 'visual-reference' / 'visual-reference-package-v2.4.3'
VISUAL_RUNTIME_PACKAGE = REFERENCE_PACKAGE
LEGACY_REFERENCE_PACKAGE_REL = Path('visual-reference/visual-reference-package-v2.3.6')
REFERENCE_MANIFEST = REFERENCE_PACKAGE / 'manifests' / 'reference-assets.json'
LEGACY_REFERENCE_MANIFEST = REFERENCE_MANIFEST
STRUCTURE_CARD_MANIFEST = REFERENCE_PACKAGE / 'manifests' / 'reference-structure-cards.json'
EXTERNAL_REFERENCE_MANIFEST = REFERENCE_PACKAGE / 'manifests' / 'external-references.json'
VISUAL_STAGE_CHECKER = VISUAL_RUNTIME_PACKAGE / 'scripts' / 'check_visual_stage.py'
VISUAL_STAGE_ORDER = ('V0-intake', 'V1-visual-problems', 'V2-reference-selection', 'V3-candidates',
                      'V4-mockups', 'V5-design-review', 'V6-user-decision', 'V7-lock')
REVIEW_CHECKS = ('NarrativeFocus', 'Layout', 'MotionCurve', 'JoinContinuity',
                 'Timing', 'AudioContinuity', 'ReferenceCompliance')
FINAL_CHECKS = ('CompositionCompliance', 'MotionContinuity', 'DeliveryTechnical')
METHOD_FIELDS = ('narrative_role', 'visual_focus', 'source_conditions',
                 'original_frame_assessment', 'selected_treatment', 'selection_reason')


def dotted_get(value, path):
    """Resolve a dotted path inside a JSON-compatible object.

    Implementation Lock uses object keys (not array indexes) for executable
    elements so a REF can be mechanically traced to the exact parameters it
    changed. Missing/blank values are rejected by the caller.
    """
    require(isinstance(path, str) and path.strip(), 'A nonblank parameter path is required')
    current = value
    for part in path.split('.'):
        require(isinstance(current, dict) and part in current,
                'Implementation Lock parameter path is missing: ' + path)
        current = current[part]
    return current


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.writing')
    if temporary.exists():
        raise ValueError('An interrupted write must be inspected: ' + str(temporary))
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def path_at(root, ref):
    if not isinstance(ref, str) or not ref.strip():
        raise ValueError('A project-relative file path is required')
    relative = Path(ref)
    root = Path(root).resolve()
    if relative.is_absolute() or '..' in relative.parts or '#' in ref:
        raise ValueError('Use a contained file path, without a section: ' + ref)
    target = (root / relative).resolve()
    if target == root or root not in target.parents:
        raise ValueError('Path escapes the project: ' + ref)
    return target


def binding(root, ref):
    path = path_at(root, ref)
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError('Missing or empty artifact: ' + ref)
    return {'ref': ref, 'sha256': sha(path)}


def require(value, message):
    if not value:
        raise ValueError(message)


def proof_reuse_allowed(root, project, mockup_ref, proof_ref):
    """Allow an engineered Mockup to serve as Proof only with explicit bound evidence."""
    reuse = project.get('visual_proof_reuse')
    if not isinstance(reuse, dict) or reuse.get('mode') != 'reuse_engineered_mockup':
        return False
    if reuse.get('mockup_ref') != mockup_ref or reuse.get('proof_ref') != proof_ref:
        return False
    reason = reuse.get('reason')
    require(isinstance(reason, str) and len(reason.strip()) >= 10,
            'visual_proof_reuse requires a concrete reason')
    refs = reuse.get('engineering_evidence_refs')
    require(isinstance(refs, list) and refs and len(set(refs)) == len(refs),
            'visual_proof_reuse requires engineering_evidence_refs')
    assets = project.get('execution_reference_asset_refs', [])
    require(isinstance(assets, list) and all(ref in assets for ref in refs),
            'visual_proof_reuse engineering evidence must be included in execution_reference_asset_refs')
    for ref in refs:
        binding(root, ref)
    return True


def positive(value):
    return type(value) is int and value > 0


def visual_stage_dir(project):
    """Return the project-relative v2.3.6 visual-stage directory, if enabled.

    v1.4.8 projects use the embedded Visual Reference V0–V7 files as the
    authoritative visual-design record. Older v1.4.5 projects without this
    field continue through the legacy routing contract so in-flight work can be
    inspected/migrated instead of being silently reinterpreted.
    """
    value = project.get('visual_pipeline', {}).get('visual_stage_dir')
    if value is None:
        return None
    require(isinstance(value, str) and value.strip(), 'visual_pipeline.visual_stage_dir must be a nonblank project-relative directory')
    return value.strip().rstrip('/')


def visual_stage_report(root, project, required_stage=None):
    """Run the host-hardened stage checker against the current reference library.

    The checker owns V0–V7 ordering, hashes, structure-card conditions, review
    evidence and V6 user confirmation. This host wrapper only consumes its
    result; it does not duplicate or weaken those rules.
    """
    rel = visual_stage_dir(project)
    require(rel is not None, 'This project does not enable the V0–V7 visual-stage workflow')
    vdir = path_at(root, rel)
    require(vdir.is_dir(), 'Missing visual-stage directory: ' + rel)
    require(VISUAL_STAGE_CHECKER.is_file(), 'Bundled V0–V7 visual-stage checker is missing')
    proc = subprocess.run([os.sys.executable, '-I', str(VISUAL_STAGE_CHECKER), str(vdir),
                           '--package', str(REFERENCE_PACKAGE)], capture_output=True, text=True)
    output = (proc.stdout or '') + (('\n' + proc.stderr) if proc.stderr else '')
    statuses = {}
    for line in (proc.stdout or '').splitlines():
        match = re.match(r'^(V[0-7]-[A-Za-z0-9-]+)\s+(PASS|FAIL|PENDING|REVISE|MISSING|NOT_REACHED)\s*$', line.strip())
        if match:
            statuses[match.group(1)] = match.group(2)
    require(len(statuses) == len(VISUAL_STAGE_ORDER), 'Visual-stage checker returned an unreadable report:\n' + output.strip())
    if proc.returncode != 0:
        raise ValueError('Visual-stage validation failed:\n' + output.strip())
    if required_stage is not None:
        require(required_stage in VISUAL_STAGE_ORDER, 'Unknown visual stage: ' + str(required_stage))
        require(statuses.get(required_stage) == 'PASS', required_stage + ' must PASS before this action; checker says ' +
                str(statuses.get(required_stage)) + '\n' + output.strip())
    artifacts = {}
    for stage in VISUAL_STAGE_ORDER:
        fp = vdir / (stage + '.json')
        if fp.is_file():
            artifacts[stage] = {'ref': rel + '/' + stage + '.json', 'sha256': sha(fp)}
    return {'dir': rel, 'statuses': statuses, 'artifacts': artifacts, 'output': output.strip()}


def _visual_stage_json(root, project, stage):
    report = visual_stage_report(root, project, stage)
    return read(path_at(root, report['artifacts'][stage]['ref']))


def visual_stage_design(root, project, require_lock=False):
    """Return the chosen v2.3.6 design and the reference migrations it actually uses."""
    required = 'V7-lock' if require_lock else 'V2-reference-selection'
    report = visual_stage_report(root, project, required)
    vdir = report['dir']
    def load(stage):
        return read(path_at(root, vdir + '/' + stage + '.json'))
    v2 = load('V2-reference-selection')
    result = {'report': report, 'v2': v2, 'selected_reference_ids': sorted({x.get('ref_id') for x in v2.get('selections', []) if x.get('ref_id')})}
    if not require_lock:
        return result
    v3, v6, v7 = load('V3-candidates'), load('V6-user-decision'), load('V7-lock')
    require(v6.get('status') == 'confirmed', 'V6 must be confirmed before Production Lock')
    chosen = v6.get('chosen_candidate')
    candidate = next((x for x in v3.get('candidates', []) if x.get('id') == chosen), None)
    require(isinstance(candidate, dict), 'V6 chosen_candidate is missing from V3')
    selections = {(x.get('problem'), x.get('ref_id')): x for x in v2.get('selections', [])}
    chosen_migrations = []
    for trace in candidate.get('ref_trace', []):
        sel = trace.get('selection')
        require(isinstance(sel, str) and '/' in sel, 'V3 chosen candidate has an invalid ref_trace.selection')
        problem, rid = sel.rsplit('/', 1)
        selection = selections.get((problem, rid))
        require(selection is not None, 'V3 chosen candidate cites a V2 selection that does not exist: ' + sel)
        chosen_migrations.append({'problem': problem, 'ref_id': rid,
                                  'structure_card': selection.get('structure_card'),
                                  'transfer': trace.get('transfer'),
                                  'applied_to': trace.get('applied_to')})
    chosen_keys = {(x['structure_card'], x['transfer']) for x in chosen_migrations}
    v7_traces = v7.get('reference_trace', [])
    require(isinstance(v7_traces, list), 'V7 reference_trace must be an array')
    for trace in v7_traces:
        require((trace.get('structure_card'), trace.get('transfer')) in chosen_keys,
                'V7 contains a reference migration not used by the chosen V3 candidate')
    for migration in chosen_migrations:
        require(any(t.get('structure_card') == migration['structure_card'] and t.get('transfer') == migration['transfer']
                    for t in v7_traces),
                'Chosen V3 reference migration did not reach V7: ' + migration['ref_id'] + '/' + str(migration['transfer']))
    result.update({'v3': v3, 'v6': v6, 'v7': v7, 'chosen_candidate': chosen,
                   'chosen_migrations': chosen_migrations,
                   'selected_reference_ids': sorted({x['ref_id'] for x in chosen_migrations})})
    return result


def confirmed_visual_artifacts(root, project):
    """Return the exact artifacts approved in Visual Reference V6.

    V6 is the user-decision boundary, so this helper intentionally requires
    V6 PASS rather than V7. That lets the existing host Mockup confirmation
    bind the *same* shown artifacts and user decision before V7 is authored;
    V7 is then required later by Implementation Lock / Proof.
    """
    if visual_stage_dir(project) is None:
        ref = project.get('visual_mockup_ref')
        return [binding(root, ref)] if isinstance(ref, str) and ref.strip() else []
    report = visual_stage_report(root, project, 'V6-user-decision')
    v6 = read(path_at(root, report['artifacts']['V6-user-decision']['ref']))
    require(v6.get('status') == 'confirmed', 'V6 must be confirmed before binding the selected Mockup artifacts')
    chosen = v6.get('chosen_candidate')
    require(isinstance(chosen, str) and chosen.strip(), 'V6 confirmed decision requires chosen_candidate')
    rows = []
    for item in v6.get('confirmed_artifacts', []):
        if item.get('candidate') != chosen:
            continue
        file_ref = item.get('file')
        require(isinstance(file_ref, str) and file_ref.strip(), 'V6 confirmed_artifacts requires file')
        rel = file_ref if file_ref.startswith(report['dir'] + '/') else report['dir'] + '/' + file_ref
        token = binding(root, rel)
        require(token['sha256'] == item.get('sha256'), 'V6 confirmed artifact hash changed: ' + file_ref)
        rows.append(token)
    require(rows, 'V6 confirmed_artifacts must include the chosen candidate')
    require(len({row['ref'] for row in rows}) == len(rows), 'V6 confirmed_artifacts must not duplicate files')
    return rows


def selected_reference_ids(root, project):
    if visual_stage_dir(project) is not None:
        return visual_stage_design(root, project, require_lock=True)['selected_reference_ids']
    return sorted({rid for method in methods(root, project)['methods']
                   if method.get('visual_reference_status') == 'used'
                   for rid in method.get('visual_reference_refs', [])})


def visual_reference_catalog():
    require(REFERENCE_MANIFEST.is_file(), 'Bundled Visual Reference manifest is missing')
    data = read(REFERENCE_MANIFEST)
    require(isinstance(data, dict) and isinstance(data.get('assets'), list),
            'Bundled Visual Reference manifest is malformed')
    result = {}
    for row in data['assets']:
        require(isinstance(row, dict) and isinstance(row.get('asset_id'), str),
                'Visual Reference manifest contains an invalid asset row')
        ref_id = row['asset_id']
        require(ref_id not in result, 'Duplicate Visual Reference asset_id: ' + ref_id)
        local = row.get('local_path')
        expected_sha = row.get('sha256')
        require(isinstance(local, str) and local and isinstance(expected_sha, str) and expected_sha,
                ref_id + ': local_path / sha256 missing from bundled manifest')
        full = REFERENCE_PACKAGE / local
        require(full.is_file(), ref_id + ': bundled Visual Reference image is missing')
        require(sha(full) == expected_sha, ref_id + ': bundled Visual Reference image hash mismatch')
        result[ref_id] = {'asset_path': REFERENCE_PACKAGE.relative_to(PACKAGE_ROOT).as_posix() + '/' + local,
                          'sha256': expected_sha,
                          'transfer_principle': row.get('transfer_principle'),
                          'do_not_copy': row.get('do_not_copy')}
    return result


def validate_reference_routing(row, allow_not_applicable=False):
    ref_id = row.get('method_id') or '<method>'
    status = row.get('visual_reference_status')
    require(status in ('used', 'not_applicable'),
            ref_id + ': visual_reference_status must be used or not_applicable before Mockup')
    refs = row.get('visual_reference_refs')
    viewed = row.get('viewed_reference_assets')
    require(isinstance(refs, list), ref_id + ': visual_reference_refs must be an array')
    require(isinstance(viewed, list), ref_id + ': viewed_reference_assets must be an array')
    if status == 'not_applicable':
        require(allow_not_applicable, ref_id + ': not_applicable is allowed only when the project visual gate itself is not_applicable')
        require(not refs and not viewed, ref_id + ': not_applicable cannot retain viewed/selected refs')
        reason = row.get('visual_reference_not_applicable_reason')
        require(isinstance(reason, str) and reason.strip(),
                ref_id + ': visual_reference_not_applicable_reason is required')
        return {'status': status, 'reason': reason.strip(), 'refs': []}
    require(1 <= len(refs) <= 3 and len(set(refs)) == len(refs),
            ref_id + ': used Visual Reference routing requires 1-3 unique REF ids')
    catalog = visual_reference_catalog()
    require(all(isinstance(x, str) and x in catalog for x in refs),
            ref_id + ': unknown Visual Reference REF id')
    require(len(viewed) == len(refs),
            ref_id + ': each selected REF requires one viewed_reference_assets record')
    seen = set()
    for item in viewed:
        require(isinstance(item, dict), ref_id + ': viewed_reference_assets entries must be objects')
        rid = item.get('ref_id')
        require(rid in refs and rid not in seen, ref_id + ': viewed_reference_assets ref_id mismatch/duplicate')
        seen.add(rid)
        expected = catalog[rid]
        path_matches = item.get('asset_path') == expected['asset_path']
        if not path_matches:
            # Resolve old paths to the single verified image only when original/current hashes agree.
            local = Path(expected['asset_path']).relative_to(REFERENCE_PACKAGE.relative_to(PACKAGE_ROOT))
            legacy_path = (LEGACY_REFERENCE_PACKAGE_REL / local).as_posix()
            legacy_assets = {row['asset_id']: row for row in read(LEGACY_REFERENCE_MANIFEST)['assets']}
            path_matches = (item.get('asset_path') == legacy_path
                            and legacy_assets.get(rid, {}).get('sha256') == expected['sha256'])
        require(path_matches, rid + ': asset_path must bind the bundled local image')
        require(item.get('sha256') == expected['sha256'], rid + ': sha256 must bind the bundled local image')
        require(isinstance(item.get('observation'), str) and item['observation'].strip(),
                rid + ': record an actual visual observation from the reference image')
    require(seen == set(refs), ref_id + ': viewed reference set must match selected refs')
    require(isinstance(row.get('reference_selection_reason'), str) and row['reference_selection_reason'].strip(),
            ref_id + ': reference_selection_reason is required')
    for key in ('reference_transfer_principles', 'reference_do_not_copy'):
        values = row.get(key)
        require(isinstance(values, list) and bool(values)
                and all(isinstance(x, str) and x.strip() for x in values),
                ref_id + ': ' + key + ' must contain concrete entries')
    return {'status': status, 'refs': refs,
            'viewed': [{'ref_id': item['ref_id'], 'asset_path': item['asset_path'],
                        'sha256': item['sha256'], 'observation': item['observation']} for item in viewed],
            'selection_reason': row['reference_selection_reason'],
            'transfer_principles': row['reference_transfer_principles'],
            'do_not_copy': row['reference_do_not_copy']}


def enabled(project):
    from versioning import version_at_least
    if 'visual_pipeline' in project:
        return True
    try:
        return version_at_least(project.get('schema_version', '0'), '1.9')
    except ValueError:
        # validate_project reports malformed versions using the original
        # contract. Policy discovery must not pre-empt that diagnostic.
        return False


def policy(project):
    value = project.get('visual_pipeline')
    require(isinstance(value, dict) and value.get('policy') == POLICY,
            'schema 1.9+ requires visual_pipeline.policy=' + POLICY)
    require(project.get('execution_policy', {}).get('workflow_gate_control') == 'required_v4'
            and isinstance(project.get('workflow_control'), dict)
            and project['workflow_control'].get('schema_version') == '1.3',
            'Visual production requires workflow_control schema 1.3 and workflow_gate_control=required_v4; run workflow_control.py init')
    require(project.get('execution_policy', {}).get('method_preservation') == 'preserve_confirmed_v1',
            'Method preservation is required; run workflow_control.py init')
    for key in ('methods_ref', 'implementation_lock_ref', 'composition_plan_ref', 'delivery_spec_ref', 'delivery_receipt_ref'):
        require(isinstance(value.get(key), str) and bool(value[key].strip()), 'visual_pipeline.' + key + ' is required')
    return value


def methods(root, project):
    ctl = policy(project)
    data = read(path_at(root, ctl['methods_ref']))
    require(isinstance(data, dict) and data.get('schema_version') == '1.0'
            and data.get('project_id') == project.get('project_id'), 'Method project/schema mismatch')
    rows = data.get('methods')
    require(isinstance(rows, list) and bool(rows), 'At least one actual visual method is required')
    timeline = read(path_at(root, 'timeline.json'))
    events = {r.get('event_id') for r in timeline.get('events', []) if isinstance(r, dict)}
    ids = set()
    known_evidence = set()
    for filename, key in [('deep-observations.csv', 'observation_id'), ('frame-observations.csv', 'frame_id')]:
        path = root / filename
        if path.is_file():
            with path.open(encoding='utf-8-sig', newline='') as handle:
                known_evidence.update(row.get(key) for row in csv.DictReader(handle))
    for filename, key in [('units.jsonl', 'unit_id'), ('reviews.jsonl', 'review_id'), ('frames.jsonl', 'frame_id')]:
        path = root / filename
        if path.is_file():
            known_evidence.update(json.loads(line).get(key) for line in path.read_text(encoding='utf-8').splitlines() if line.strip())
    for row in rows:
        require(isinstance(row, dict) and isinstance(row.get('method_id'), str)
                and row['method_id'] and row['method_id'] not in ids, 'Unique method_id required')
        ids.add(row['method_id'])
        for key in METHOD_FIELDS:
            require(isinstance(row.get(key), str) and bool(row[key].strip()), row['method_id'] + ': missing ' + key)
        for key in ('event_ids', 'source_evidence_refs', 'failure_modes', 'demo_checks'):
            require(isinstance(row.get(key), list) and bool(row[key])
                    and all(isinstance(x, str) and x.strip() for x in row[key]), row['method_id'] + ': missing ' + key)
        require(set(row['event_ids']).issubset(events), row['method_id'] + ': unknown timeline event')
        require(set(row['source_evidence_refs']).issubset(known_evidence), row['method_id'] + ': unknown source evidence reference')
        require(isinstance(row.get('parameters'), dict) and bool(row['parameters']), 'Concrete method parameters required')
        require(type(row.get('composition_required')) is bool, 'composition_required must be explicit')
        for key, pattern in (('library_refs', r'^M(?:0[1-9]|1[0-4])$'), ('fallback_refs', r'^F0[1-9]$')):
            values = row.get(key)
            if values is not None:
                require(isinstance(values, list) and all(isinstance(x, str) and re.fullmatch(pattern, x) for x in values),
                        row['method_id'] + ': invalid ' + key)
        if row.get('visual_problem') is not None:
            require(isinstance(row.get('visual_problem'), str) and bool(row['visual_problem'].strip()),
                    row['method_id'] + ': visual_problem must be non-empty when provided')
        if visual_stage_dir(project) is None:
            validate_reference_routing(row, project.get('visual_gate_status') == 'not_applicable')
        candidates = row.get('candidate_treatments')
        if candidates is not None:
            require(isinstance(candidates, list) and all(isinstance(x, dict) for x in candidates),
                    row['method_id'] + ': candidate_treatments must be an array of objects')
    return data


def reference_routing_inputs(root, project):
    # Lightweight pre-Mockup check. v1.4.8 delegates reference selection to the
    # embedded v2.3.6 V0–V2 contract; legacy v1.4.5 projects keep the old path.
    ctl = policy(project)
    if visual_stage_dir(project) is not None:
        design = visual_stage_design(root, project, require_lock=False)
        report = design['report']
        return {
            'mode': 'visual_stage_v2.3.6',
            'methods': binding(root, ctl['methods_ref']),
            'reference_manifest_sha256': sha(REFERENCE_MANIFEST),
            'structure_cards_sha256': sha(STRUCTURE_CARD_MANIFEST),
            'external_references_sha256': sha(EXTERNAL_REFERENCE_MANIFEST),
            'visual_stage': {stage: report['artifacts'][stage] for stage in ('V0-intake','V1-visual-problems','V2-reference-selection')},
            'selected_reference_ids': design['selected_reference_ids'],
        }
    data = read(path_at(root, ctl['methods_ref']))
    require(isinstance(data, dict) and data.get('schema_version') == '1.0'
            and data.get('project_id') == project.get('project_id'), 'Method project/schema mismatch')
    rows = data.get('methods')
    require(isinstance(rows, list) and bool(rows), 'At least one visual method draft is required for reference routing')
    routing = []
    for row in rows:
        require(isinstance(row, dict) and isinstance(row.get('method_id'), str) and row['method_id'],
                'Reference routing requires method_id')
        routing.append(validate_reference_routing(row, project.get('visual_gate_status') == 'not_applicable'))
    return {'mode': 'legacy_v1.4.5', 'methods': binding(root, ctl['methods_ref']),
            'reference_manifest_sha256': sha(REFERENCE_MANIFEST),
            'routing': routing}


def implementation_lock(root, project):
    """Validate the machine-readable construction contract for the confirmed Mockup.

    The lock is intentionally stricter than prose execution-reference. It makes
    the selected Mockup executable by naming concrete elements, renderers and
    parameters, and it requires every selected REF to leave a trace into those
    parameters. Merely recording that a REF was viewed is not enough.
    """
    ctl = policy(project)
    ref = ctl.get('implementation_lock_ref')
    require(isinstance(ref, str) and ref.strip(), 'visual_pipeline.implementation_lock_ref is required')
    data = read(path_at(root, ref))
    require(isinstance(data, dict) and data.get('schema_version') == '1.0'
            and data.get('project_id') == project.get('project_id'),
            'Implementation Lock project/schema mismatch')
    mockup_ref = project.get('visual_mockup_ref')
    require(isinstance(mockup_ref, str) and mockup_ref.strip(),
            'Implementation Lock requires the selected visual_mockup_ref')
    require(data.get('selected_mockup_ref') == mockup_ref,
            'Implementation Lock must bind the current selected Mockup')
    mockup = binding(root, mockup_ref)
    require(data.get('selected_mockup_sha256') == mockup['sha256'],
            'Implementation Lock selected_mockup_sha256 must bind the current Mockup bytes')
    require(data.get('output') == project.get('output'),
            'Implementation Lock output must match project.output exactly')

    renderer_lock = data.get('renderer_lock')
    require(isinstance(renderer_lock, dict) and renderer_lock,
            'Implementation Lock requires renderer_lock')
    require(isinstance(renderer_lock.get('toolchain'), list) and renderer_lock['toolchain'],
            'Implementation Lock renderer_lock.toolchain must list the actual execution tools')
    require(all(isinstance(row, dict) and row.get('role') and row.get('actual_tool') and row.get('entrypoint')
                for row in renderer_lock['toolchain']),
            'Each locked renderer requires role + actual_tool + entrypoint')
    require(isinstance(renderer_lock.get('final_execute_entrypoint'), str)
            and renderer_lock['final_execute_entrypoint'].strip(),
            'Implementation Lock requires final_execute_entrypoint')

    elements = data.get('elements')
    require(isinstance(elements, dict) and elements,
            'Implementation Lock requires concrete executable elements')
    for element_id, element in elements.items():
        require(isinstance(element_id, str) and element_id.strip() and isinstance(element, dict),
                'Implementation Lock element ids/values are invalid')
        for key in ('role', 'renderer', 'implementation_method'):
            require(isinstance(element.get(key), str) and element[key].strip(),
                    element_id + ': Implementation Lock element requires ' + key)
        require(isinstance(element.get('parameters'), dict) and element['parameters'],
                element_id + ': Implementation Lock element requires concrete parameters')
        event_ids = element.get('event_ids', [])
        require(isinstance(event_ids, list) and all(isinstance(x, str) and x for x in event_ids),
                element_id + ': event_ids must be an array of event ids')

    method_index = {row['method_id']: row for row in methods(root, project)['methods']}
    traces = data.get('reference_trace')
    require(isinstance(traces, list), 'Implementation Lock reference_trace must be an array')

    if visual_stage_dir(project) is not None:
        design = visual_stage_design(root, project, require_lock=True)
        report = design['report']
        v7_ref = report['artifacts']['V7-lock']['ref']
        stage_binding = data.get('visual_stage_binding')
        require(isinstance(stage_binding, dict), 'Implementation Lock requires visual_stage_binding for the V0–V7 visual-stage workflow')
        require(stage_binding.get('v7_ref') == v7_ref and stage_binding.get('v7_sha256') == report['artifacts']['V7-lock']['sha256'],
                'Implementation Lock visual_stage_binding must bind the current V7-lock bytes')
        require(stage_binding.get('chosen_candidate') == design['chosen_candidate'],
                'Implementation Lock visual_stage_binding chosen_candidate must match V6/V7')

        confirmed = confirmed_visual_artifacts(root, project)
        expected_mockups = confirmed
        actual_mockups = data.get('confirmed_mockups')
        require(isinstance(actual_mockups, list) and actual_mockups == expected_mockups,
                'Implementation Lock confirmed_mockups must exactly bind the V6-confirmed chosen artifacts')
        require(any(x['ref'] == mockup_ref and x['sha256'] == mockup['sha256'] for x in confirmed),
                'project.visual_mockup_ref must be one of the V6-confirmed chosen artifacts')

        selected_refs = set(design['selected_reference_ids'])
        expected_stage = {(t.get('structure_card'), t.get('transfer'), t.get('element'), t.get('parameter_path'))
                          for t in design['v7'].get('reference_trace', [])}
        if design['chosen_migrations']:
            require(expected_stage, 'Chosen visual design must retain V7 reference_trace rows for every chosen reference migration')
        else:
            require(not expected_stage and not traces, 'No-reference chosen design must not invent V7 / Implementation Lock reference traces')
        seen_stage = set()
        for trace in traces:
            require(isinstance(trace, dict), 'Implementation Lock reference_trace rows must be objects')
            require(trace.get('method_id') in method_index, 'Implementation Lock reference_trace method_id is unknown')
            require(trace.get('ref_id') in selected_refs, 'Implementation Lock reference_trace ref_id is not used by the chosen V3 candidate')
            stage_trace = trace.get('stage_trace')
            require(isinstance(stage_trace, dict), 'V0–V7 reference traces require stage_trace')
            stage_key = (stage_trace.get('structure_card'), stage_trace.get('transfer'),
                         stage_trace.get('element'), stage_trace.get('parameter_path'))
            require(stage_key in expected_stage and stage_key not in seen_stage,
                    'Implementation Lock stage_trace must map each V7 reference trace exactly once')
            seen_stage.add(stage_key)
            matching_migrations = [m for m in design['chosen_migrations']
                                   if m['ref_id'] == trace.get('ref_id')
                                   and m['structure_card'] == stage_key[0]
                                   and m['transfer'] == stage_key[1]]
            require(matching_migrations,
                    'Implementation Lock ref_id / structure_card / transfer must come from the chosen V3 reference migration')
            targets = trace.get('target_element_ids')
            require(isinstance(targets, list) and targets and len(set(targets)) == len(targets)
                    and all(isinstance(x, str) and x in elements for x in targets),
                    'reference_trace target_element_ids must point to real Implementation Lock elements')
            paths = trace.get('parameter_paths')
            require(isinstance(paths, list) and paths and len(set(paths)) == len(paths),
                    'reference_trace parameter_paths are required')
            for parameter_path in paths:
                value = dotted_get(data, parameter_path)
                require(value is not None and value != '' and value != [] and value != {},
                        'reference_trace applied parameter is blank: ' + parameter_path)
            for key, message in (('proof_checks', 'proof_checks must make the migrated design observable in Proof'),
                                 ('do_not_copy_checks', 'do_not_copy_checks are required')):
                checks = trace.get(key)
                require(isinstance(checks, list) and checks and all(isinstance(x, str) and x.strip() for x in checks), message)
        require(seen_stage == expected_stage,
                'Every V7 reference trace must reach the executable Implementation Lock; stage-only traces do not count as implemented')
    else:
        expected_pairs = {(mid, rid) for mid, method in method_index.items()
                          if method.get('visual_reference_status') == 'used'
                          for rid in method.get('visual_reference_refs', [])}
        seen_pairs = set()
        for trace in traces:
            require(isinstance(trace, dict), 'Implementation Lock reference_trace rows must be objects')
            pair = (trace.get('method_id'), trace.get('ref_id'))
            require(pair in expected_pairs and pair not in seen_pairs,
                    'Implementation Lock reference_trace must map each selected REF exactly once per method')
            seen_pairs.add(pair)
            method = method_index[pair[0]]
            require(trace.get('mockup_ref') == mockup_ref,
                    pair[0] + '/' + pair[1] + ': reference trace must bind the current Mockup')
            principles = trace.get('applied_principles')
            require(isinstance(principles, list) and principles
                    and all(isinstance(x, str) and x in method.get('reference_transfer_principles', []) for x in principles),
                    pair[0] + '/' + pair[1] + ': applied_principles must come from the routed transfer principles')
            targets = trace.get('target_element_ids')
            require(isinstance(targets, list) and targets and len(set(targets)) == len(targets)
                    and all(isinstance(x, str) and x in elements for x in targets),
                    pair[0] + '/' + pair[1] + ': target_element_ids must point to real Implementation Lock elements')
            paths = trace.get('parameter_paths')
            require(isinstance(paths, list) and paths and len(set(paths)) == len(paths),
                    pair[0] + '/' + pair[1] + ': parameter_paths are required')
            for parameter_path in paths:
                value = dotted_get(data, parameter_path)
                require(value is not None and value != '' and value != [] and value != {},
                        pair[0] + '/' + pair[1] + ': applied parameter is blank: ' + parameter_path)
            checks = trace.get('proof_checks')
            require(isinstance(checks, list) and checks
                    and all(isinstance(x, str) and x.strip() for x in checks),
                    pair[0] + '/' + pair[1] + ': proof_checks must make REF use observable in the Proof')
            do_not_copy = trace.get('do_not_copy_checks')
            require(isinstance(do_not_copy, list) and do_not_copy
                    and all(isinstance(x, str) and x.strip() for x in do_not_copy),
                    pair[0] + '/' + pair[1] + ': do_not_copy_checks are required')
        require(seen_pairs == expected_pairs,
                'Every selected Visual Reference must reach Implementation Lock; viewed-only REF records do not count as used')
    return data


def reference_application_inputs(root, project, element_ids=None, method_ids=None):
    """Bind the full Reference -> approved visual design -> executable-parameter chain."""
    ctl = policy(project)
    routing = reference_routing_inputs(root, project)
    lock = implementation_lock(root, project)
    lock_binding = binding(root, ctl['implementation_lock_ref'])
    traces = lock['reference_trace']
    if element_ids is not None:
        selected = set(element_ids)
        lock_scope = {key: value for key, value in lock.items() if key not in ('elements', 'reference_trace', 'parameter_bindings', 'safe_adaptation')}
        lock_scope['elements'] = {key: value for key, value in lock['elements'].items() if key in selected}
        traces = [row for row in traces if set(row.get('target_element_ids', [])) & selected]
        lock_scope['reference_trace'] = traces
        lock_binding = {'ref': ctl['implementation_lock_ref'], 'scope_digest': digest(lock_scope)}
        if method_ids is not None:
            rows = [row for row in methods(root, project)['methods'] if row['method_id'] in set(method_ids)]
            routing['methods'] = {'ref': ctl['methods_ref'], 'scope_digest': digest(rows)}
            if 'routing' in routing:
                all_methods = methods(root, project)['methods']
                routing['routing'] = [row for method, row in zip(all_methods, routing['routing']) if method['method_id'] in set(method_ids)]
    result = {
        'routing': routing,
        'mockup': binding(root, project.get('visual_mockup_ref')),
        'mockups': confirmed_visual_artifacts(root, project),
        'implementation_lock': lock_binding,
        'reference_trace': traces,
    }
    if visual_stage_dir(project) is not None:
        report = visual_stage_report(root, project, 'V7-lock')
        result['visual_stage_lock'] = report['artifacts']['V7-lock']
        result['selected_reference_ids'] = selected_reference_ids(root, project)
    return result


def production_lock_inputs(root, project):
    ctl = policy(project)
    workflow = project.get('workflow_control', {})
    spec_refs = workflow.get('production_spec_refs')
    require(isinstance(spec_refs, list) and bool(spec_refs),
            'workflow_control.production_spec_refs must bind the shown Production Lock specification')
    from workflow_control import artifact
    production_specs = [artifact(root, ref) for ref in spec_refs]
    require(path_at(root, ctl['delivery_spec_ref']).is_file(),
            'Production Lock requires a completed delivery-spec.json before Execute')
    delivery = binding(root, ctl['delivery_spec_ref'])
    for field in ('text_policy', 'voiceover_policy'):
        require(isinstance(project.get(field), dict), 'Production Lock requires project.' + field)
    script_dir = Path(__file__).resolve().parent
    renderer_scripts = []
    for filename in ('render_blender_composition.py', 'blender_composite_worker.py', 'finish_ffmpeg.py'):
        target = script_dir / filename
        require(target.is_file(), 'Missing locked renderer script: ' + filename)
        renderer_scripts.append({'ref': 'scripts/' + filename, 'sha256': sha(target)})
    payload = {
        'production_specs': production_specs,
        'reference_routing': reference_routing_inputs(root, project),
        'reference_application': reference_application_inputs(root, project),
        'implementation_lock': binding(root, ctl['implementation_lock_ref']),
        'methods': binding(root, ctl['methods_ref']),
        'composition': composition_inputs(root, project),
        'composition_plan': binding(root, ctl['composition_plan_ref']),
        'delivery_spec': delivery,
        'capability_map': binding(root, 'capability-map.json'),
        'mockup': binding(root, project.get('visual_mockup_ref')),
        'mockups': confirmed_visual_artifacts(root, project),
        'proofs': [] if project.get('visual_gate_status') == 'proof_waived' else [binding(root, ref) for ref in proof_frame_refs(root, project)],
        'output': project.get('output'),
        'text_policy': project.get('text_policy'),
        'voiceover_policy': project.get('voiceover_policy'),
        'renderer_scripts': renderer_scripts,
        'pipeline_policy': POLICY,
    }
    if visual_stage_dir(project) is not None:
        payload['visual_stage_lock'] = visual_stage_report(root, project, 'V7-lock')['artifacts']['V7-lock']
    return payload


def legacy_method_inputs(root, project):
    data = methods(root, project)
    return {'methods': binding(root, policy(project)['methods_ref']),
            'sources': binding(root, 'sources.json'), 'output': project.get('output'),
            'direction_ref': binding(root, project['narrative_direction_ref']),
            'selected_events': [r.get('event_ids') for r in data['methods']],
            'reference_application': reference_application_inputs(root, project)}


def method_inputs(root, project):
    # Current Narrative and approved parameter values do not redefine the method.
    methods(root, project)
    implementation_lock(root, project)
    from workflow_control import method_inputs as preserved_method_inputs
    return preserved_method_inputs(root, project)


def proof_composition_ids(plan):
    """Return the declared representative Proof set.

    v1.4.5 uses proof_composition_ids. A single legacy proof_composition_id is
    still accepted for in-flight v1.4.3 projects, but ambiguous dual
    declarations are rejected.
    """
    plural = plan.get('proof_composition_ids')
    legacy = plan.get('proof_composition_id')
    if plural is None:
        require(isinstance(legacy, str) and legacy.strip(),
                'proof_composition_ids must contain at least one representative risk-based proof composition')
        return [legacy]
    require(isinstance(plural, list) and bool(plural)
            and all(isinstance(value, str) and value.strip() for value in plural)
            and len(plural) == len(set(plural)),
            'proof_composition_ids must be a nonempty unique list of composition IDs')
    if legacy is not None:
        require(isinstance(legacy, str) and legacy == plural[0],
                'legacy proof_composition_id, when present, must equal the first proof_composition_ids entry')
    return plural


def proof_frame_refs(root, project):
    plan = composition_plan(root, project)
    jobs = {row['composition_id']: row for row in plan['compositions']}
    return [jobs[cid]['proof_ref'] for cid in proof_composition_ids(plan)]


def composition_covers(proof_job, job):
    """Return whether one reviewed Proof mechanically covers another composition.

    This intentionally checks only executable dimensions that the runtime can
    prove from the plan. Material/content-specific difficulty is not inferred;
    a redundant extra Proof for such a risk needs an explicit, shown exception.
    """
    if proof_job.get('mode', 'layers') != job.get('mode', 'layers'):
        return False
    if not set(job.get('implementation_element_ids', [])).issubset(
            set(proof_job.get('implementation_element_ids', []))):
        return False
    if not set(job.get('method_ids', [])).issubset(set(proof_job.get('method_ids', []))):
        return False
    if job.get('joins') and not proof_job.get('joins'):
        return False
    if job.get('mode', 'layers') == 'native_blend':
        if job.get('native_scene_ref') != proof_job.get('native_scene_ref'):
            return False
        if set(job.get('native_dependency_refs', [])) != set(proof_job.get('native_dependency_refs', [])):
            return False
    return True


def _additional_proof_exception(root, job):
    exception = job.get('additional_proof_exception')
    require(isinstance(exception, dict),
            'Redundant Proof is blocked; make it a production composition with proof_covered_by, '
            'or declare additional_proof_exception for a material-specific risk that machine coverage cannot see')
    require(exception.get('kind') == 'material_specific_unmodeled_risk',
            'additional_proof_exception.kind must be material_specific_unmodeled_risk')
    require(isinstance(exception.get('reason'), str) and exception['reason'].strip(),
            'additional_proof_exception requires a nonblank reason')
    refs = exception.get('evidence_refs')
    require(isinstance(refs, list) and refs and len(refs) == len(set(refs))
            and all(isinstance(ref, str) and ref.strip() for ref in refs),
            'additional_proof_exception requires unique nonblank evidence_refs')
    for ref in refs:
        binding(root, ref)
    return exception


def composition_plan(root, project):
    data = read(path_at(root, policy(project)['composition_plan_ref']))
    require(isinstance(data, dict) and data.get('schema_version') == '1.0'
            and data.get('project_id') == project.get('project_id'), 'Composition project/schema mismatch')
    profile = data.get('output', {})
    require(isinstance(profile, dict), 'Composition output must be an object')
    require(profile == project.get('output'), 'Composition and project output profiles must match exactly')
    for key in ('width', 'height', 'fps_num', 'fps_den'):
        require(positive(profile.get(key)), 'Invalid output ' + key)
    rows = data.get('compositions')
    require(isinstance(rows, list) and bool(rows), 'Composition plan must contain actual shots')
    proof_policy = data.get('proof_scope_policy')
    require(proof_policy in (None, 'representative_risk_based_v1', 'representative_risk_based_v2'), 'Unknown proof_scope_policy')
    proof_ids = proof_composition_ids(data)
    proof_set = set(proof_ids)
    method_index = {r['method_id']: r for r in methods(root, project)['methods']}
    ctl = policy(project)
    require(data.get('implementation_lock_ref') == ctl['implementation_lock_ref'],
            'Composition plan must bind the current visual_pipeline.implementation_lock_ref')
    lock = implementation_lock(root, project)
    lock_elements = lock['elements']
    known_events = {r.get('event_id') for r in read(path_at(root, 'timeline.json')).get('events', [])}
    ids, outputs, covered, job_index = set(), set(), set(), {}
    for job in rows:
        require(isinstance(job, dict) and job.get('composition_id') and job['composition_id'] not in ids,
                'Unique composition_id required')
        ids.add(job['composition_id'])
        job_index[job['composition_id']] = job
        is_proof = job['composition_id'] in proof_set
        delivery_role = job.get('delivery_role', 'delivery')
        require(delivery_role in ('delivery', 'proof_only'), 'delivery_role must be delivery or proof_only')
        if proof_policy == 'representative_risk_based_v2':
            require((delivery_role == 'proof_only') == is_proof,
                    'v2 proof policy requires proof_composition_ids to be proof_only and all other jobs to be delivery')
            if is_proof:
                fps = profile['fps_num'] / profile['fps_den']
                max_frames = max(1, int(round(fps * 3.0)))
                if job['frame_count'] > max_frames:
                    exception = job.get('full_length_proof_exception')
                    require(isinstance(exception, dict)
                            and exception.get('kind') == 'full_length_required_for_unmodeled_dynamic_risk'
                            and isinstance(exception.get('reason'), str) and exception['reason'].strip(),
                            f'Proof exceeds default 3-second budget ({max_frames} frames); shorten it or declare a concrete full_length_proof_exception')
        require(job.get('backend') == 'blender', 'This pipeline requires an actual Blender composition backend')
        require(job.get('mode', 'layers') in ('layers', 'native_blend'), 'Unknown Blender composition mode')
        require(positive(job.get('frame_count')), 'Positive composition frame_count required')
        require(type(job.get('local_start_frame')) is int and job['local_start_frame'] >= 0,
                'local_start_frame must be a nonnegative integer')
        require(job.get('anchor_event_id') in known_events, 'Composition anchor must be an actual event')
        require(isinstance(job.get('event_ids'), list) and bool(job['event_ids'])
                and set(job['event_ids']).issubset(known_events), 'Composition event scope is required')
        require(isinstance(job.get('method_ids'), list) and bool(job['method_ids'])
                and set(job['method_ids']).issubset(method_index), 'Composition must reference actual methods')
        element_ids = job.get('implementation_element_ids')
        require(isinstance(element_ids, list) and element_ids and len(set(element_ids)) == len(element_ids)
                and all(isinstance(x, str) and x in lock_elements for x in element_ids),
                'Composition must bind concrete Implementation Lock elements')
        for method_id in job['method_ids']:
            require(set(method_index[method_id]['event_ids']).issubset(set(job['event_ids'])),
                    'Composition must cover all events of its method')
        covered.update(job['method_ids'])
        artifact_keys = ['scene_ref', 'video_ref', 'receipt_ref', 'readback_ref']
        if is_proof:
            artifact_keys += ['demo_ref', 'proof_ref', 'review_ref']
        for key in artifact_keys:
            ref = job.get(key)
            resolved = path_at(root, ref)
            require(resolved not in outputs, 'Composition artifact paths must be distinct: ' + str(ref))
            outputs.add(resolved)
        if not is_proof:
            for key in ('demo_ref', 'proof_ref', 'review_ref'):
                if job.get(key):
                    resolved = path_at(root, job[key])
                    require(resolved not in outputs, 'Composition artifact paths must be distinct: ' + str(job[key]))
                    outputs.add(resolved)
            covered_by = job.get('proof_covered_by')
            require(isinstance(covered_by, str) and covered_by in proof_set,
                    'Every non-proof composition must explicitly name proof_covered_by from proof_composition_ids')
            reason = job.get('proof_coverage_reason')
            require(isinstance(reason, str) and reason.strip(),
                    'Every non-proof composition requires a nonblank proof_coverage_reason')
        require(job['scene_ref'].lower().endswith('.blend'), 'An editable .blend scene is required')
        joins = job.get('joins')
        require(isinstance(joins, list), 'Explicit joins array required; use [] only with a documented reason')
        require(bool(joins) or bool(job.get('no_join_reason')), 'Explain why this composition contains no join')
        for join in joins:
            require(isinstance(join, dict) and type(join.get('frame')) is int
                    and 0 < join['frame'] < job['frame_count'], 'Join must be inside the composition window')
            require(positive(join.get('before_frames')) and positive(join.get('after_frames'))
                    and join['frame'] >= join['before_frames']
                    and join['frame'] + join['after_frames'] <= job['frame_count'], 'Join coverage must include both sides')
            for key in ('from_event_id', 'to_event_id'):
                require(join.get(key) in job['event_ids'], 'Join must reference scoped events')
            for key in ('cut_intent', 'outgoing_state', 'incoming_state', 'motion_handoff'):
                require(isinstance(join.get(key), str) and bool(join[key].strip()), 'Join requires ' + key)
        if job.get('mode', 'layers') == 'native_blend':
            binding(root, job.get('native_scene_ref'))
            dependencies = job.get('native_dependency_refs', [])
            require(isinstance(dependencies, list) and len(dependencies) == len(set(dependencies))
                    and all(isinstance(ref, str) and ref.strip() for ref in dependencies),
                    'native_dependency_refs must be a unique array of project refs')
            for ref in dependencies:
                binding(root, ref)
            require(all(lock_elements[element_id].get('renderer') == 'blender_native_blend'
                        for element_id in element_ids),
                    'native_blend composition cannot replace an Implementation Lock renderer')
        else:
            require(isinstance(job.get('layers'), list) and bool(job['layers']), 'Actual compositing layers required')
            require(all(lock_elements[element_id].get('renderer') == 'blender_layers'
                        for element_id in element_ids),
                    'layers composition cannot replace an Implementation Lock renderer')
        if is_proof:
            if job.get('preview_audio_ref'):
                binding(root, job['preview_audio_ref'])
            else:
                require(job.get('silent_demo') is True and bool(job.get('silent_reason')),
                        'Supply the relevant audio, or explicitly justify a silent representative demo')
    required = {mid for mid, row in method_index.items() if row['composition_required']}
    require(required.issubset(covered), 'Some selected methods are missing from the Blender compositions')
    require(proof_set.issubset(ids), 'proof_composition_ids must select actual compositions')

    # Mechanical coverage: a free-text reason is documentation, not evidence.
    # Every deferred composition must point to one proof whose executable
    # implementation is at least as broad in the risk dimensions we can check.
    for job in rows:
        if job['composition_id'] in proof_set:
            continue
        proof_job = job_index[job['proof_covered_by']]
        if not composition_covers(proof_job, job):
            mode_ok = job.get('mode', 'layers') == proof_job.get('mode', 'layers')
            elements_ok = set(job['implementation_element_ids']).issubset(set(proof_job['implementation_element_ids']))
            methods_ok = set(job['method_ids']).issubset(set(proof_job['method_ids']))
            joins_ok = not job['joins'] or bool(proof_job['joins'])
            native_ok = (job.get('mode', 'layers') != 'native_blend' or
                         (job.get('native_scene_ref') == proof_job.get('native_scene_ref') and
                          set(job.get('native_dependency_refs', [])) == set(proof_job.get('native_dependency_refs', []))))
            if not mode_ok:
                raise ValueError('Deferred composition renderer/mode is not covered by its Proof; return to D2')
            if not elements_ok:
                raise ValueError('Deferred composition uses Implementation Lock elements not covered by its Proof; return to D2')
            if not methods_ok:
                raise ValueError('Deferred composition uses methods not covered by its Proof; return to D2')
            if not joins_ok:
                raise ValueError('Deferred composition contains a join not exercised by its Proof; return to D2')
            if not native_ok:
                raise ValueError('Deferred native_blend composition uses a different native_scene_ref or native_dependency_refs; return to D2 or add a distinct Proof')
            raise ValueError('Deferred composition is not covered by its Proof; return to D2')

    # Minimal-sufficient Proof rule. Compare each Proof with every other Proof,
    # not only earlier list entries. A Proof is redundant when another Proof
    # mechanically covers it and either that covering Proof appears earlier, or
    # it is strictly broader. Equivalent Proofs keep the earlier list entry.
    for i, proof_id in enumerate(proof_ids):
        job = job_index[proof_id]
        redundant = any(
            composition_covers(job_index[other], job)
            and (j < i or not composition_covers(job, job_index[other]))
            for j, other in enumerate(proof_ids) if j != i)
        if redundant:
            _additional_proof_exception(root, job)
        else:
            require(job.get('additional_proof_exception') is None,
                    'additional_proof_exception is only valid when another Proof mechanically covers this Proof')
    from workflow_control import _method_documents, _method_rules, method_refs
    names = {'visual-methods', 'implementation-lock', 'composition-plan'}
    names.update(x['artifact'] for b in lock.get('parameter_bindings', []) for x in [b['source']] + b['targets'])
    names.update(row['artifact'] for row in lock.get('safe_adaptation', {}).get('allowed', []) if isinstance(row, dict))
    _method_rules(_method_documents(root, project, sorted(names)))
    return data

def proof_display_refs(root, project):
    """Artifacts that must actually be shown before Proof can be confirmed."""
    plan = composition_plan(root, project)
    jobs = {row['composition_id']: row for row in plan['compositions']}
    proof_ids = proof_composition_ids(plan)
    proof_refs = [jobs[cid]['proof_ref'] for cid in proof_ids]
    require(project.get('visual_proof_ref') == proof_refs[0],
            'project.visual_proof_ref must be the first proof frame from proof_composition_ids')
    if len(proof_refs) > 1:
        require(project.get('visual_proof_refs') == proof_refs,
                'project.visual_proof_refs must list every current representative proof frame in order')
    result = []
    for cid in proof_ids:
        job = jobs[cid]
        result.extend([job['proof_ref'], job['demo_ref']])
        exception = job.get('additional_proof_exception')
        if isinstance(exception, dict):
            result.extend(exception.get('evidence_refs', []))
    return list(dict.fromkeys(result))


def job_input(root, project, plan, job, scoped=True):
    from workflow_control import artifact
    method_index = {row['method_id']: row for row in methods(root, project)['methods']}
    resources = []
    for layer in job.get('layers', []):
        for key in ('asset_ref', 'font_ref'):
            if layer.get(key):
                resources.append(binding(root, layer[key]))
    for key in ('native_scene_ref', 'preview_audio_ref'):
        if job.get(key):
            resources.append(binding(root, job[key]))
    selected = set(job['event_ids'])
    timeline = read(path_at(root, 'timeline.json'))
    event_fields = ('event_id', 'source_id', 'unit_id', 'source_in_ms', 'source_out_ms',
                    'speed', 'd2_selection_snapshot', 'source_signature', 'time_mapping_digest')
    scoped_events = [{key: row.get(key) for key in event_fields}
                     for row in timeline.get('events', []) if row.get('event_id') in selected]
    resources.extend(binding(root, ref) for ref in job.get('native_dependency_refs', []))
    control = project['workflow_control']
    audio_choice = control.get('audio_choice') or {}
    reference_inputs = {'audio_choice': audio_choice,
                        'visual_specs': [artifact(root, ref) for ref in control.get('visual_spec_refs', [])]}
    if audio_choice.get('ref'):
        reference_inputs['audio_spec'] = artifact(root, audio_choice['ref'])
    application = reference_application_inputs(root, project, job['implementation_element_ids'] if scoped else None, job['method_ids'] if scoped else None)
    return {'job': job, 'output': plan['output'], 'project_id': project['project_id'],
            'methods': [method_index[mid] for mid in job['method_ids']], 'resources': resources,
            'event_scope': scoped_events, 'sources': binding(root, 'sources.json'),
            'audio_policy': project.get('audio_policy'), 'reference_inputs': reference_inputs,
            'implementation_lock': application['implementation_lock'],
            'reference_application': application,
            'worker_sha256': sha(Path(__file__).with_name('blender_composite_worker.py'))}


def tool(name):
    resolved = shutil.which(name)
    require(resolved is not None, name + ' is required for actual media validation')
    return resolved


def run(command, timeout=600, cwd=None):
    result = subprocess.run([str(x) for x in command], stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, cwd=cwd)
    require(result.returncode == 0, 'Command failed: ' + str(command[0]) + '\n' + result.stderr.decode(errors='replace')[-4000:])
    return result.stdout


def probe(path, count=True):
    command = [tool('ffprobe'), '-v', 'error']
    if count:
        command += ['-count_frames']
    command += ['-show_streams', '-show_format', '-of', 'json', str(path)]
    return json.loads(run(command))


def verify_video(path, profile, frames, audio_required=False):
    media = probe(path)
    videos = [r for r in media.get('streams', []) if r.get('codec_type') == 'video']
    audio = [r for r in media.get('streams', []) if r.get('codec_type') == 'audio']
    require(len(videos) == 1, 'Exactly one video stream required')
    video = videos[0]
    require((video.get('width'), video.get('height')) == (profile['width'], profile['height']), 'Rendered dimensions differ')
    require(Fraction(video.get('avg_frame_rate', '0/1')) == Fraction(profile['fps_num'], profile['fps_den']), 'Rendered frame rate differs')
    require(int(video.get('nb_read_frames', -1)) == frames, 'Rendered frame count differs')
    require(not audio_required or bool(audio), 'Expected audio stream is missing')
    run([tool('ffmpeg'), '-v', 'error', '-xerror', '-i', str(path), '-f', 'null', '-'])
    return {'width': video['width'], 'height': video['height'], 'frames': frames,
            'fps_num': profile['fps_num'], 'fps_den': profile['fps_den'],
            'audio_streams': len(audio), 'full_decode': 'pass'}


def validate_job_receipt(root, project, plan, job, require_proof=False):
    receipt = read(path_at(root, job['receipt_ref']))
    require(receipt.get('status') == 'rendered_not_reviewed'
            and receipt.get('backend') == 'blender' and bool(receipt.get('backend_version')),
            'A real Blender render receipt is required, not an engineering file alone')
    require(receipt.get('project_id') == project['project_id']
            and receipt.get('composition_id') == job['composition_id'], 'Render receipt scope differs')
    current_input = digest(job_input(root, project, plan, job))
    adopted = (project.get('workflow_control', {}).get('method_preservation') or {}).get('adopted_receipts', {}).get(job['composition_id'], {})
    unchanged_adopted = (adopted.get('legacy_input_digest') == receipt.get('input_digest')
                         and adopted.get('scope_digest') == current_input
                         and adopted.get('receipt_sha256') == sha(path_at(root, job['receipt_ref'])))
    require(receipt.get('input_digest') == current_input or unchanged_adopted, 'Composition inputs changed; rebuild and review')
    purpose = receipt.get('purpose', 'proof')
    require(purpose in ('proof', 'production'), 'Unknown Blender receipt purpose')
    if require_proof:
        require(job['composition_id'] in set(proof_composition_ids(plan)),
                'Only proof_composition_ids may satisfy the pre-Execute composition proof gate')
        require(purpose == 'proof', 'Representative proof requires a proof render receipt')
    expected_keys = ['scene_ref', 'video_ref', 'demo_ref', 'proof_ref', 'readback_ref'] if purpose == 'proof' else ['scene_ref', 'video_ref', 'readback_ref']
    expected = [binding(root, job[key]) for key in expected_keys]
    require(receipt.get('artifacts') == expected, 'Composition render artifacts changed or are incomplete')
    require(receipt.get('technical', {}).get('frames') == job['frame_count']
            and receipt.get('technical', {}).get('full_decode') == 'pass', 'Composition technical verification missing')
    return receipt

def validate_review(root, project, job, receipt):
    review = read(path_at(root, job['review_ref']))
    require(review.get('composition_id') == job['composition_id']
            and review.get('demo_sha256') == binding(root, job['demo_ref'])['sha256']
            and review.get('engineering_sha256') == binding(root, job['scene_ref'])['sha256']
            and review.get('render_input_digest') == receipt['input_digest'], 'Review must bind the current demo and engineering')
    require(review.get('playback_verified') is True and review.get('blocking_issues') == [],
            'Actual continuous playback and zero unresolved blocking issues required')
    require(isinstance(review.get('reviewer'), str) and bool(review['reviewer'].strip())
            and review['reviewer'].strip().lower() not in ('auto', 'script', 'unknown'), 'An actual reviewer is required')
    checks = review.get('checks')
    require(isinstance(checks, list) and REVIEW_CHECKS == tuple(row.get('name') for row in checks),
            'Every required composition check must be recorded in the supplied order')
    for check in checks:
        require(check.get('status') in ('pass', 'not_applicable')
                and bool(check.get('method')) and bool(check.get('finding'))
                and bool(check.get('evidence')), 'Unreviewed/failed composition check: ' + str(check.get('name')))
        require(isinstance(check['evidence'], list) and bool(check['evidence']), 'Review evidence must be file references')
        for ref in check['evidence']:
            binding(root, ref)
        if check.get('name') == 'ReferenceCompliance' and project.get('visual_gate_status') != 'not_applicable':
            require(check.get('status') == 'pass', 'ReferenceCompliance cannot be not_applicable when Visual References are used')
            ctl = policy(project)
            mockups = confirmed_visual_artifacts(root, project)
            required_evidence = {x['ref'] for x in mockups} | {job.get('proof_ref'), ctl['implementation_lock_ref']}
            if visual_stage_dir(project) is not None:
                required_evidence.add(visual_stage_report(root, project, 'V7-lock')['artifacts']['V7-lock']['ref'])
            require(required_evidence.issubset(set(check['evidence'])),
                    'ReferenceCompliance must compare all V6-confirmed Mockups + V7 (when enabled) + Proof + Implementation Lock')
            selected_refs = selected_reference_ids(root, project)
            require(check.get('reference_ref_ids') == selected_refs,
                    'ReferenceCompliance must name every reference used by the chosen implementation')
            current_lock_sha = binding(root, ctl['implementation_lock_ref'])['sha256']
            declared_scope = check.get('implementation_scope_digest')
            application = reference_application_inputs(root, project, job['implementation_element_ids'], job['method_ids'])
            current_scope = application['implementation_lock']['scope_digest']
            if declared_scope is not None:
                require(declared_scope == current_scope, 'ReferenceCompliance implementation scope changed')
            cached = (project.get('workflow_control', {}).get('method_preservation') or {}).get('review_scopes', {}).get(job['composition_id'], {})
            unchanged_review = (cached.get('review_sha256') == sha(path_at(root, job['review_ref']))
                                and cached.get('job_digest') == digest(job_input(root, project, composition_plan(root, project), job))
                                and cached.get('implementation_lock_sha256') == check.get('implementation_lock_sha256'))
            require(check.get('implementation_lock_sha256') == current_lock_sha or declared_scope == current_scope or unchanged_review,
                    'ReferenceCompliance must bind the current Implementation Lock bytes or unchanged verified scope')
            expected_mockup_hashes = {x['ref']: x['sha256'] for x in mockups}
            if visual_stage_dir(project) is None and len(mockups) == 1:
                require(check.get('mockup_sha256') == mockups[0]['sha256'],
                        'ReferenceCompliance must bind the current Mockup bytes')
            else:
                require(check.get('mockup_sha256s') == expected_mockup_hashes,
                        'ReferenceCompliance must bind every V6-confirmed Mockup byte-for-byte')
            require(check.get('proof_sha256') == binding(root, job['proof_ref'])['sha256'],
                    'ReferenceCompliance must bind the current Proof bytes')
    require(any(row.get('name') == 'JoinContinuity' and row.get('status') == 'pass' for row in checks)
            or not job['joins'], 'A join-containing demo requires a passed continuous join review')
    return review


def composition_inputs(root, project):
    """Pre-Execute Production Proof Lock inputs.

    Only the explicitly selected representative proof set is rendered/reviewed
    here. The full composition plan is frozen now; covered production windows
    are rendered once after final authorization and then inspected in final QA.
    """
    plan = composition_plan(root, project)
    jobs = {row['composition_id']: row for row in plan['compositions']}
    if project.get('visual_gate_status') == 'proof_waived':
        waiver = (project.get('workflow_control') or {}).get('proof_waiver')
        require(isinstance(waiver, dict) and waiver.get('scope') == 'skip_proof_generation_and_review',
                'proof_waived requires a bound workflow_control.proof_waiver')
        return {'proof_plan': {'output': plan['output'], 'compositions': [jobs[cid] for cid in proof_composition_ids(plan)]},
                'proof_composition_ids': proof_composition_ids(plan), 'proof_receipts': [],
                'proof_waiver': waiver, 'additional_proof_exceptions': []}
    proofs = []
    for composition_id in proof_composition_ids(plan):
        job = jobs[composition_id]
        receipt = validate_job_receipt(root, project, plan, job, require_proof=True)
        validate_review(root, project, job, receipt)
        proofs.append({'composition_id': composition_id,
                       'job_digest': receipt['input_digest'], 'artifacts': receipt['artifacts'],
                       'review': binding(root, job['review_ref'])})
    exceptions = []
    for composition_id in proof_composition_ids(plan):
        exception = jobs[composition_id].get('additional_proof_exception')
        if isinstance(exception, dict):
            exceptions.append({'composition_id': composition_id, **exception})
    return {'proof_plan': {'output': plan['output'], 'compositions': [jobs[cid] for cid in proof_composition_ids(plan)]},
            'proof_composition_ids': proof_composition_ids(plan),
            'proof_receipts': proofs, 'additional_proof_exceptions': exceptions}

def manifest_compositions(root, project, manifest):
    if not enabled(project):
        return []
    delivery_spec(root, project)
    plan = composition_plan(root, project)
    events = {row['event_id']: row for row in manifest['events']}
    result = []
    for job in plan['compositions']:
        # Proof-only jobs validate implementation risk and never become delivery
        # windows. This prevents representative demos from being expanded into
        # near-full-video renders just to satisfy manifest tiling.
        if job.get('delivery_role', 'delivery') == 'proof_only':
            continue
        receipt = validate_job_receipt(root, project, plan, job, require_proof=False)
        event = events[job['anchor_event_id']]
        start = event['out_in_frame'] + job['local_start_frame']
        end = start + job['frame_count']
        require(0 <= start < end <= manifest['total_frames'], 'Composition exceeds final output')
        actual_scope = {item['event_id'] for item in manifest['events']
                        if item['out_in_frame'] < end and item['out_out_frame'] > start}
        require(actual_scope == set(job['event_ids']), 'Composition delivery window must match its declared event scope')
        result.append({'composition_id': job['composition_id'], 'start_frame': start, 'end_frame': end,
                       'video': binding(root, job['video_ref']), 'scene': binding(root, job['scene_ref']),
                       'receipt': binding(root, job['receipt_ref']), 'input_digest': receipt['input_digest']})
    result.sort(key=lambda row: row['start_frame'])
    require(all(a['end_frame'] <= b['start_frame'] for a, b in zip(result, result[1:])),
            'Composition delivery windows must not overlap')
    return result

def delivery_spec(root, project):
    ctl = policy(project)
    spec = read(path_at(root, ctl['delivery_spec_ref']))
    require(spec.get('schema_version') == '1.0' and spec.get('project_id') == project['project_id'],
            'Delivery project/schema mismatch')
    require(type(spec.get('crf', 18)) is int and 0 <= spec.get('crf', 18) <= 51, 'CRF must be an integer from 0 to 51')
    output = path_at(root, spec.get('output_ref'))
    require(output.suffix.lower() == '.mp4', 'The delivery adapter requires an MP4 output path')
    require(project['workflow_control'].get('render_output_ref') == spec['output_ref'],
            'Declare the same final output in delivery-spec and workflow_control before authorization')
    paths = [spec.get('base_video_ref')]
    paths += [spec[key] for key in ('mixed_audio_ref', 'subtitles_ref') if spec.get(key)]
    require(isinstance(spec.get('font_refs', []), list), 'font_refs must be an array')
    paths += spec.get('font_refs', [])
    require(all(path_at(root, ref) != output for ref in paths), 'Final output must not overwrite an input')
    return spec


def delivery_inputs(root, project):
    ctl = policy(project)
    spec = delivery_spec(root, project)
    paths = [spec['base_video_ref']]
    paths += [spec[key] for key in ('mixed_audio_ref', 'subtitles_ref') if spec.get(key)]
    paths += spec.get('font_refs', [])
    return {'spec': binding(root, ctl['delivery_spec_ref']), 'assets': [binding(root, ref) for ref in paths]}


def verify_delivery_receipt(root, project):
    ctl = policy(project)
    receipt = read(path_at(root, ctl['delivery_receipt_ref']))
    manifest = read(path_at(root, 'render-manifest.json'))
    require(receipt.get('status') == 'rendered_not_reviewed' and receipt.get('backend') == 'ffmpeg', 'Actual FFmpeg delivery receipt required')
    require(receipt.get('project_id') == project['project_id']
            and receipt.get('manifest_digest') == manifest.get('manifest_digest'), 'Delivery is from a different manifest')
    from execution_integrity import project_inputs_digest
    require(manifest.get('input_digest') == project_inputs_digest(root), 'Final delivery input snapshot is stale')
    require(receipt.get('delivery_input_digest') == digest(delivery_inputs(root, project)), 'Final delivery assets changed')
    require(receipt.get('artifact') == binding(root, receipt.get('output_ref')), 'Final output was replaced or deleted')
    require(receipt.get('technical', {}).get('full_decode') == 'pass'
            and receipt.get('technical', {}).get('frames') == manifest.get('total_frames'), 'Final decode/frame verification missing')
    return receipt


def validate_final_composition_qa(root, project, checks):
    """Bind final CompositionCompliance to every compiled Blender window."""
    manifest = read(path_at(root, 'render-manifest.json'))
    compositions = manifest.get('compositions')
    require(isinstance(compositions, list) and bool(compositions),
            'Final CompositionCompliance requires compiled composition windows')
    check = next((row for row in checks if row.get('name') == 'CompositionCompliance'), None)
    require(isinstance(check, dict) and check.get('status') == 'pass',
            'CompositionCompliance must pass for the final movie')
    actual = check.get('composition_windows')
    require(isinstance(actual, list),
            'CompositionCompliance must list every composition window explicitly')
    expected = [{'composition_id': row['composition_id'],
                 'start_frame': row['start_frame'], 'end_frame': row['end_frame'],
                 'video_sha256': row['video']['sha256']} for row in compositions]
    require(len(actual) == len(expected) and all(isinstance(row, dict) for row in actual),
            'CompositionCompliance must contain one per-composition conclusion for every render-manifest window')
    actual_core = [{key: row.get(key) for key in ('composition_id', 'start_frame', 'end_frame', 'video_sha256')}
                   for row in actual]
    require(actual_core == expected,
            'CompositionCompliance composition_windows must match render-manifest IDs, frame windows and video SHA-256')
    plan_jobs = {row['composition_id']: row for row in composition_plan(root, project)['compositions']}
    for row in actual:
        require(row.get('status') == 'pass',
                str(row.get('composition_id')) + ': final composition window requires status=pass')
        require(isinstance(row.get('finding'), str) and row['finding'].strip(),
                str(row.get('composition_id')) + ': final composition window requires a nonblank finding')
        job = plan_jobs.get(row.get('composition_id'))
        require(job is not None, 'Final QA names a composition absent from composition-plan.json')
        if job.get('joins'):
            require(isinstance(row.get('join_finding'), str) and row['join_finding'].strip(),
                    str(row.get('composition_id')) + ': join-containing composition requires a nonblank join_finding')
    evidence = check.get('evidence')
    required_refs = {'render-manifest.json'} | {row['video']['ref'] for row in compositions}
    require(isinstance(evidence, list) and required_refs.issubset(set(evidence)),
            'CompositionCompliance evidence must include render-manifest.json and every production composition video')
    for ref in required_refs:
        binding(root, ref)
    return check


def tracked_refs(root, project):
    ctl = policy(project)
    result = [ctl['methods_ref'], ctl['implementation_lock_ref'], ctl['composition_plan_ref'], ctl['delivery_spec_ref']]
    if path_at(root, ctl['composition_plan_ref']).is_file():
        plan = read(path_at(root, ctl['composition_plan_ref']))
        proof_ids = set(proof_composition_ids(plan))
        for job in plan.get('compositions', []):
            # Inputs for every production composition are authorization inputs.
            result.extend(layer[k] for layer in job.get('layers', []) for k in ('asset_ref', 'font_ref') if layer.get(k))
            result.extend(job[k] for k in ('preview_audio_ref', 'native_scene_ref') if job.get(k))
            result.extend(job.get('native_dependency_refs', []))
            # Only the representative proof artifacts exist before authorization
            # and therefore belong in the pre-render project input digest.
            if job.get('composition_id') in proof_ids:
                result.extend(job.get(k) for k in ('scene_ref', 'video_ref', 'demo_ref', 'proof_ref',
                                                   'receipt_ref', 'readback_ref', 'review_ref') if job.get(k))
    if visual_stage_dir(project) is not None:
        vdir = path_at(root, visual_stage_dir(project))
        for stage in VISUAL_STAGE_ORDER:
            fp = vdir / (stage + '.json')
            if fp.is_file():
                result.append(visual_stage_dir(project) + '/' + stage + '.json')
    baseline = (project.get('workflow_control', {}).get('method_preservation') or {}).get('baseline')
    if isinstance(baseline, dict) and baseline.get('ref'):
        result.append(baseline['ref'])
    # Production-only scene/video/receipt outputs and base video/mixed audio are
    # generated *after* authorization. They are bound in the render manifest /
    # delivery receipt, not in the pre-render authorization digest.
    return sorted(set(result))

def initialize(root):
    from workflow_control import initialize as init_workflow, save_project
    project = init_workflow(root)
    project['schema_version'] = '1.9'
    project.setdefault('visual_pipeline', {'policy': POLICY, 'methods_ref': 'visual-methods.json',
        'implementation_lock_ref': 'implementation-lock.json',
        'composition_plan_ref': 'composition-plan.json', 'delivery_spec_ref': 'delivery-spec.json',
        'delivery_receipt_ref': 'delivery-receipt.json', 'visual_stage_dir': 'visual'})
    project['visual_pipeline'].setdefault('implementation_lock_ref', 'implementation-lock.json')
    if not project['workflow_control'].get('render_output_ref'):
        project['workflow_control']['render_output_ref'] = 'render/final.mp4'
    policy(project)
    lock_path = path_at(root, project['visual_pipeline']['implementation_lock_ref'])
    if not lock_path.exists():
        template = read(Path(__file__).resolve().parent.parent / 'assets' / 'implementation-lock-template.json')
        template['project_id'] = project.get('project_id')
        template['output'] = project.get('output')
        mockup_ref = project.get('visual_mockup_ref')
        if isinstance(mockup_ref, str) and mockup_ref.strip():
            mockup_path = path_at(root, mockup_ref)
            if mockup_path.is_file():
                template['selected_mockup_ref'] = mockup_ref
                template['selected_mockup_sha256'] = sha(mockup_path)
        write(lock_path, template)
    save_project(root, project)
    return project


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('init', 'status'))
    parser.add_argument('project_directory', type=Path)
    args = parser.parse_args()
    try:
        root = args.project_directory.resolve()
        project = initialize(root) if args.command == 'init' else read(root / 'project.json')
        from workflow_control import report
        result = report(root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc), 'render_allowed': False}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
