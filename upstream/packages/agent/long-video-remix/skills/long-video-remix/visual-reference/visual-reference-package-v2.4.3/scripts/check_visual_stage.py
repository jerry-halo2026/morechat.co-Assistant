#!/usr/bin/env python3
"""Visual stage gate checker (V0–V7) for long-video-remix Direct 2 (evidence-bound review + engineering hardening
+ external references XR-* / MR-* in a research queue: queued / principle / measured; routes default / special_case / fallback).

Usage:
    python3 -I check_visual_stage.py <visual_dir> [--package <reference_package_root>] [--case]

<visual_dir> holds the stage files V0-intake.json … V7-lock.json.
--package   reference package root (default: this script's parent's parent)
--case      worked-example mode: keyframe / mockup images may be absent (third-party frames are
            not shipped); their checks become warnings instead of failures.

Output: one line per stage (PASS / FAIL / PENDING / MISSING / NOT_REACHED) with reasons,
then `NEXT_ALLOWED:` — the only step the executing model may work on next.
Exit code 1 if any stage FAILs.
"""
import sys, os, json, hashlib, re, argparse, random

STAGES = ['V0-intake', 'V1-visual-problems', 'V2-reference-selection', 'V3-candidates',
          'V4-mockups', 'V5-design-review', 'V6-user-decision', 'V7-lock']
PUNCT = '，。、；：！？「」『』《》（）“”,.!?;: ·'
DIM_ENUMS = {
    'text_direction': {'horizontal', 'vertical', 'mixed'},
    'placement_logic': {'fixed_slot', 'auto_slot', 'bespoke'},
    'image_text_relation': {'in_frame_clean_zone', 'anchored_to_action', 'edge_column', 'separate_field'},
    'polarity_strategy': {'auto_dark_or_light', 'light_with_protection', 'dark_only'},
    'geometry': {'crop', 'crop_with_punch_in', 'letterbox'},
}
REVIEW_KEYS = ['thesis_delivered', 'first_read', 'image_integration', 'typography', 'color', 'narrative_detail', 'strip_decoration_test', 'template_risk']

DIRECTION_IDS = {f'VD-{i:02d}' for i in range(1, 8)}
ATTENTION_OWNERS = {'face','action','relationship','text','environment'}
TEXT_ROLES = {'observer_comment','relationship_annotation','detail_label','ironic_second_voice','emotional_afterimage','punchline','segment_marker'}
SPATIAL_RELATIONS = {'adjacent','axis_bound','negative_space','surface_bound','counterweight','dominant_field','separate_field'}
TYPOGRAPHY_VOICES = {'neutral_observer','warm_editorial','dry_wit','playful_light','assertive'}
TIMING_MODES = {'fact_sync','reaction_echo','two_step_relation','afterimage_hold','cut_definition','sound_bound'}
LEGACY_TIMING_ALIASES = {'appear_with_fact':'fact_sync','build_with_speech':'two_step_relation','hold_as_afterimage':'afterimage_hold','enter_on_cut':'cut_definition'}
EMPHASIS_BUDGETS = {'low','medium','high','low-medium'}
DIRECTION_DIFF_FIELDS = ('primary_direction','text_role','spatial_relation','timing_mode','emphasis_budget')
# Measured does not mean applicable to text design. Expand this registry only
# when a new measured case explicitly establishes its supported text context.
MEASURED_TEXT_LAYOUT_REFS = {}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def decoded_pixel_sha(p):
    """Hash decoded display pixels, ignoring file/container metadata.

    File SHA remains the provenance/integrity identity. This digest is only for visual-identity
    checks such as controlled A/B: two PNGs with different ancillary metadata but identical
    decoded pixels are the same visual result and cannot prove a visible change.
    """
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(p)).convert('RGBA')
    h = hashlib.sha256()
    h.update(f'{im.width}x{im.height}|RGBA|'.encode('ascii'))
    h.update(im.tobytes())
    return h.hexdigest()


def norm(t):
    return ''.join(c for c in t if c not in PUNCT)


class Ctx:
    def __init__(self, vdir, pkg, case):
        self.vdir, self.pkg, self.case = vdir, pkg, case
        self.data, self.errors, self.warns, self.flags = {}, {}, {}, {}
        ra = json.load(open(os.path.join(pkg, 'manifests/reference-assets.json'), encoding='utf-8'))
        self.refs = {a['asset_id'] for a in ra['assets']}
        # v2.3: external references (link + locator + card only; no third-party frames in the package)
        xp = os.path.join(pkg, 'manifests/external-references.json')
        self.xr = {}
        if os.path.exists(xp):
            self.xr = {r['ref_id']: r for r in json.load(open(xp, encoding='utf-8'))['references']}
            self.refs |= set(self.xr)
        sc = json.load(open(os.path.join(pkg, 'manifests/reference-structure-cards.json'), encoding='utf-8'))
        self.cards = {c['card_id']: c for c in sc['cards']}

    def load(self, st):
        p = os.path.join(self.vdir, st + '.json')
        if not os.path.exists(p): return None
        try:
            self.data[st] = json.load(open(p, encoding='utf-8'))
        except Exception as e:
            self.data[st] = {'_parse_error': str(e)}
        return self.data[st]

    def err(self, st, m): self.errors.setdefault(st, []).append(m)
    def warn(self, st, m): self.warns.setdefault(st, []).append(m)

    def path(self, rel):
        return rel if os.path.isabs(rel) else os.path.join(self.vdir, rel)


NON_DESIGN_KEYS = {
    'inputs_sha256', 'inputs_design_sha256', '_说明', 'note', 'notes',
    'comment', 'comments', 'record_note', 'record_notes', 'created_at', 'updated_at'
}


def design_payload(value):
    """Canonical design-bearing content used for stage invalidation.

    JSON formatting and record-only notes do not invalidate downstream design work. Artifact
    hashes, source signatures, copy, measurements, choices, parameters and user decisions remain
    inside the digest, so actual design/evidence changes still reopen dependent stages.
    """
    if isinstance(value, dict):
        return {k: design_payload(v) for k, v in sorted(value.items())
                if k not in NON_DESIGN_KEYS and not k.startswith('_record_')}
    if isinstance(value, list):
        return [design_payload(v) for v in value]
    return value


def design_sha_path(path):
    data = json.load(open(path, encoding='utf-8'))
    blob = json.dumps(design_payload(data), ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(blob).hexdigest()


def check_chain(c, st, d):
    """Invalidate only on design/evidence changes; keep legacy byte-chain compatibility."""
    i = STAGES.index(st)
    design_rec = d.get('inputs_design_sha256')
    raw_rec = d.get('inputs_sha256', {})
    if design_rec is not None and not isinstance(design_rec, dict):
        c.err(st, 'inputs_design_sha256 必须是对象'); return
    for prev in STAGES[:i]:
        p = os.path.join(c.vdir, prev + '.json')
        if not os.path.exists(p):
            continue
        name = prev + '.json'
        if design_rec is not None:
            if name not in design_rec:
                c.err(st, f'inputs_design_sha256 缺少 {name}（记录前序设计指纹）')
                continue
            actual_design = design_sha_path(p)
            if design_rec[name] != actual_design:
                c.err(st, f'{name} 的设计/证据输入已变化：从 {prev} 起重新检查受影响步骤')
                continue
            if name in raw_rec and raw_rec[name] != sha(p):
                c.warn(st, f'{name} 文件字节已变化，但设计指纹未变（格式/备注类变化不使后续设计失效）')
        else:
            # Legacy v2.3.6 records remain strict so old cases are not silently reinterpreted.
            if name not in raw_rec:
                c.err(st, f'inputs_sha256 缺少 {name}（旧记录必须保存全部前序文件哈希；新记录建议改用 inputs_design_sha256）')
            elif raw_rec[name] != sha(p):
                c.err(st, f'{name} 在本步之后被改动（旧 byte-chain 哈希不符）：从 {prev} 起重新检查并重写后续步骤')


def source_geometry(v0):
    g = (v0.get('source') or {}).get('geometry')
    if isinstance(g, (list, tuple)) and len(g) == 2:
        w, h = g
    elif isinstance(g, dict):
        w, h = g.get('width'), g.get('height')
    else:
        raise ValueError('source.geometry 必须是 [width,height] 或 {width,height}')
    if not isinstance(w, int) or not isinstance(h, int) or w <= 0 or h <= 0:
        raise ValueError(f'source.geometry 非法: {g}')
    return w, h


def luma_stats(frame_path, source_geom, rect_src):
    from PIL import Image
    import numpy as np
    sw, sh = source_geom
    im0 = Image.open(frame_path).convert('L')
    im = im0 if im0.size == (sw, sh) else im0.resize((sw, sh), Image.LANCZOS)
    if not (isinstance(rect_src, (list, tuple)) and len(rect_src) == 4):
        raise ValueError(f'rect_src 非法: {rect_src}')
    x0, y0, x1, y1 = map(int, rect_src)
    if not (0 <= x0 < x1 <= sw and 0 <= y0 < y1 <= sh):
        raise ValueError(f'rect_src 越界: {rect_src}, source={sw}x{sh}')
    a = np.asarray(im.crop((x0,y0,x1,y1))).astype(float)
    return float(a.mean()), float(a.std())

_PATH_TOKEN = re.compile(r'([A-Za-z_][A-Za-z0-9_-]*)|\[(\d+)\]')

def resolve_json_path(obj, path):
    """Resolve a restricted JSON path like elements[0].polarity. No eval, no wildcards."""
    if not isinstance(path, str) or not path:
        raise KeyError('empty path')
    pos, cur = 0, obj
    while pos < len(path):
        if path[pos] == '.': pos += 1
        m = _PATH_TOKEN.match(path, pos)
        if not m: raise KeyError(f'bad token at {path[pos:]}')
        key, idx = m.group(1), m.group(2)
        if key is not None:
            if not isinstance(cur, dict) or key not in cur: raise KeyError(key)
            cur = cur[key]
        else:
            i = int(idx)
            if not isinstance(cur, list) or i >= len(cur): raise KeyError(f'[{i}]')
            cur = cur[i]
        pos = m.end()
    return cur

def verify_artifact(c, st, art, label):
    if not isinstance(art, dict):
        c.err(st, f'{label} 必须是对象'); return False
    rel, want = art.get('file'), art.get('sha256')
    if not rel or not want:
        c.err(st, f'{label} 缺 file/sha256'); return False
    fp = c.path(rel)
    if not os.path.exists(fp):
        (c.warn if c.case else c.err)(st, f'{label} 文件不存在: {rel}'); return c.case
    if sha(fp) != want:
        c.err(st, f'{label} 哈希不符: {rel}'); return False
    return True


REUSE_MATERIAL_CHANGE_KEYS = {'text_image_relation', 'motion_language', 'geometry_strategy'}
DEFERRED_RISK_TAGS = {'long_text', 'multi_person', 'complex_background', 'tight_clean_zone', 'subtitle_conflict', 'moving_subject', 'other'}


def verify_reuse_basis(c, st, ds):
    """A reuse path is only valid when it binds a prior real V6 confirmation + V7 lock + shown artifact."""
    ev = ds.get('reuse_evidence') or {}
    if not ev:
        c.err(st, 'reuse_confirmed 必须提供 reuse_evidence，不能只写一段 basis 说明')
        return
    decision = ev.get('decision'); lock = ev.get('lock'); art = ev.get('confirmed_artifact')
    okd = verify_artifact(c, st, decision, 'design_scope.reuse_evidence.decision')
    okl = verify_artifact(c, st, lock, 'design_scope.reuse_evidence.lock')
    oka = verify_artifact(c, st, art, 'design_scope.reuse_evidence.confirmed_artifact')
    if okd and okl:
        try:
            vd=json.load(open(c.path(decision['file']),encoding='utf-8'))
            vl=json.load(open(c.path(lock['file']),encoding='utf-8'))
            if vd.get('stage')!='V6' or vd.get('status')!='confirmed': c.err(st, 'reuse_evidence.decision 必须是已 confirmed 的 V6')
            if vl.get('stage')!='V7': c.err(st, 'reuse_evidence.lock 必须是 V7 lock')
            if vd.get('chosen_candidate') != vl.get('chosen_candidate'): c.err(st, 'reuse_evidence 的 V6/V7 chosen_candidate 不一致')
            shown={(x.get('file'),x.get('sha256'),x.get('candidate')) for x in vd.get('confirmed_artifacts',[])}
            if oka and (art.get('file'),art.get('sha256'),art.get('candidate')) not in shown:
                c.err(st, 'reuse_evidence.confirmed_artifact 必须来自该 V6 的 confirmed_artifacts')
        except Exception as e:
            c.err(st, f'reuse_evidence 无法读取/核验: {e}')
    changes=ds.get('material_changes') or []
    if not isinstance(changes,list):
        c.err(st, 'design_scope.material_changes 必须是数组'); changes=[]
    unknown=set(changes)-REUSE_MATERIAL_CHANGE_KEYS
    if unknown: c.err(st, f'design_scope.material_changes 包含未知项 {sorted(unknown)}')
    if changes:
        c.err(st, '图文关系 / 动效语言 / 几何策略发生实质变化时不能走 reuse_confirmed；改用 explore_new')


def qa_elements(c, st, elements, tp, tag):
    if not elements:
        c.err(st, f'{tag}: 没有元素 QA'); return
    copy={norm(x.get('text','')) for x in c.data['V0-intake']['confirmed_from_d2'].get('copy_lines',[])}
    for e in elements:
        et=f"{tag}/{e.get('id')}"
        if norm(e.get('text','')) not in copy: c.err(st, f'{et}: 文字不在 V0 登记文案里')
        if e.get('min_hanzi_ink_px',0) < tp['glyph_floor_px'] and not e.get('floor_exempt'): c.err(st, f"{et}: 字高 {e.get('min_hanzi_ink_px')} < {tp['glyph_floor_px']}")
        if e.get('contrast_median',0) < tp['contrast_median_min'] or e.get('contrast_worst',0) < tp['contrast_worst_min']:
            c.err(st, f"{et}: 对比度 {e.get('contrast_median')}/{e.get('contrast_worst')} 未达标")
        if e.get('min_clearance_px',0) < tp['clearance_px']: c.err(st, f"{et}: 距保护区 {e.get('min_clearance_px')}px < {tp['clearance_px']}")
        if e.get('subtitle_overlap'): c.err(st, f'{et}: 压到烧录字幕带')


# ------------------------------------------------------------------ stages
def V0(c, d):
    st = 'V0-intake'
    for k in ('project_id', 'source', 'confirmed_from_d2', 'text_policy', 'keyframes'):
        if k not in d: c.err(st, f'缺字段 {k}')
    src = d.get('source', {})
    for k in ('source_id', 'signature', 'geometry', 'time_mapping'):
        if not src.get(k): c.err(st, f'source.{k} 为空')
    cf = d.get('confirmed_from_d2', {})
    if cf.get('copy_status') not in ('confirmed', 'working'): c.err(st, 'confirmed_from_d2.copy_status 必须是 confirmed 或 working')
    if cf.get('copy_status') == 'working': c.warn(st, '文案为 working（未经用户确认），V6 前必须确认')
    drp=d.get('design_review_policy') or {}
    irm=drp.get('independent_review','optional')
    if irm not in ('optional','required','disabled'):
        c.err(st, 'design_review_policy.independent_review 必须是 optional / required / disabled')
    if 'small_screen_width_px' in drp and (not isinstance(drp.get('small_screen_width_px'), int) or drp['small_screen_width_px'] < 240):
        c.err(st, 'design_review_policy.small_screen_width_px 必须是 >=240 的整数')
    ds=d.get('design_scope') or {'mode':'explore_new'}
    mode=ds.get('mode','explore_new')
    if mode not in ('explore_new','reuse_confirmed','simple_text'):
        c.err(st, 'design_scope.mode 必须是 explore_new / reuse_confirmed / simple_text')
    if mode in ('reuse_confirmed','simple_text') and len(str(ds.get('basis','')).strip()) < 6:
        c.err(st, '复用/简单文字路径必须在 design_scope.basis 说明已确认方案或简化依据')
    if mode == 'reuse_confirmed':
        verify_reuse_basis(c, st, ds)
    lines = cf.get('copy_lines', [])
    if not lines: c.err(st, 'copy_lines 为空：没有登记文案就不能做视觉')
    for l in lines:
        if l.get('role') not in ('act', 'say'): c.err(st, f"文案 {l.get('id')} 的 role 必须是 act（动作/结论）或 say（说法/引用）")
    tp = d.get('text_policy', {})
    for k in ('glyph_floor_px', 'contrast_median_min', 'contrast_worst_min', 'clearance_px'):
        if not isinstance(tp.get(k), (int, float)): c.err(st, f'text_policy.{k} 缺失')
    kfs = d.get('keyframes', [])
    if not kfs: c.err(st, 'keyframes 为空')
    for k in kfs:
        if k.get('full_frame') is not True and k['id'] not in d.get('blocked_keyframes', []):
            c.err(st, f"关键帧 {k['id']} 不是完整源帧，必须列入 blocked_keyframes 并说明缺什么")
        if k.get('full_frame') and not os.path.exists(c.path(k.get('file', ''))):
            (c.warn if c.case else c.err)(st, f"关键帧文件不存在：{k.get('file')}")


def _canon_timing(v):
    return LEGACY_TIMING_ALIASES.get(v, v)


def _validate_direction_record(c, st, rec, label, *, require_typography=False):
    if not isinstance(rec, dict):
        c.err(st, f'{label} 必须是对象'); return
    if rec.get('primary_direction') not in DIRECTION_IDS:
        c.err(st, f'{label}.primary_direction 必须是 VD-01…VD-07')
    sec=rec.get('secondary_direction')
    if sec not in (None,'') and sec not in DIRECTION_IDS:
        c.err(st, f'{label}.secondary_direction 必须为空或 VD-01…VD-07')
    if rec.get('attention_owner') is not None and rec.get('attention_owner') not in ATTENTION_OWNERS:
        c.err(st, f'{label}.attention_owner 非法')
    if rec.get('text_role') not in TEXT_ROLES:
        c.err(st, f'{label}.text_role 非法')
    if rec.get('spatial_relation') not in SPATIAL_RELATIONS:
        c.err(st, f'{label}.spatial_relation 非法')
    timing=rec.get('timing_mode', rec.get('motion_relation'))
    if _canon_timing(timing) not in TIMING_MODES:
        c.err(st, f'{label}.timing_mode 非法')
    if rec.get('emphasis_budget') not in EMPHASIS_BUDGETS:
        c.err(st, f'{label}.emphasis_budget 非法')
    if require_typography and rec.get('typography_voice') not in TYPOGRAPHY_VOICES:
        c.err(st, f'{label}.typography_voice 非法')
    seq=rec.get('attention_sequence')
    if seq is not None and (not isinstance(seq,list) or len(seq)<2 or any(len(str(x).strip())<2 for x in seq)):
        c.err(st, f'{label}.attention_sequence 至少两步且必须具体')
    why=rec.get('why') or rec.get('why_this_direction') or rec.get('why_this_candidate')
    if why is not None and len(str(why).strip()) < 10:
        c.err(st, f'{label} 的方向依据过短')


def _candidate_direction_signature(cd):
    ds=cd.get('direction_strategy') or {}
    sig={k:_canon_timing(ds.get(k)) if k=='timing_mode' else ds.get(k) for k in DIRECTION_DIFF_FIELDS}
    sig['attention_sequence']=tuple(ds.get('attention_sequence') or [])
    shots=[]
    for ps in sorted(cd.get('per_shot',[]), key=lambda x:str(x.get('keyframe'))):
        du=ps.get('direction_use') or {}
        shots.append((ps.get('keyframe'), du.get('primary_direction'), tuple(du.get('attention_sequence') or []), du.get('text_role'), du.get('spatial_relation'), _canon_timing(du.get('timing_mode')), du.get('emphasis_budget')))
    sig['per_shot']=tuple(shots)
    return sig

def V1(c, d):
    st = 'V1-visual-problems'
    v0 = c.data['V0-intake']
    try:
        src_geom = source_geometry(v0)
    except Exception as e:
        c.err(st, str(e)); src_geom = (1,1)
    usable = {k['id']: k for k in v0['keyframes'] if k.get('full_frame') and k['id'] not in v0.get('blocked_keyframes', [])}
    shots = {s.get('keyframe'): s for s in d.get('shots', [])}
    for kid in usable:
        if kid not in shots: c.err(st, f'关键帧 {kid} 没有视觉问题定义')
    for kid, s in shots.items():
        if kid not in usable: c.err(st, f'{kid} 不在 V0 可用关键帧里（blocked 或未登记）'); continue
        g = s.get('geometry', {})
        if g.get('mode') == 'crop' and g.get('scale', 1.0) <= 0: c.err(st, f'{kid} geometry.scale 非法')
        ids = set()
        for p in s.get('protect', []):
            if p.get('class') not in ('face', 'hand', 'object', 'body'): c.err(st, f"{kid} 保护区 {p.get('id')} class 非法")
            ids.add(p.get('id'))
        if not s.get('protect'): c.warn(st, f'{kid} 没有保护区（确认画面里确实没有人和关键物件）')
        zones = s.get('zones', [])
        if not zones: c.err(st, f'{kid} 没有测量任何区域（zones）：问题必须基于测量')
        fp = c.path(usable[kid].get('file', ''))
        for z in zones:
            ids.add(z.get('id'))
            if not isinstance(z.get('luma_mean'), (int, float)) or not isinstance(z.get('luma_std'), (int, float)):
                c.err(st, f"{kid}.{z.get('id')} 缺 luma_mean / luma_std"); continue
            if os.path.exists(fp):
                try:
                    m, sd = luma_stats(fp, src_geom, z['rect_src'])
                except Exception as e:
                    c.err(st, f"{kid}.{z.get('id')} 重测失败: {e}")
                    continue
                if abs(m - z['luma_mean']) > 10 or abs(sd - z['luma_std']) > 10:
                    c.err(st, f"{kid}.{z['id']} 测量值与重测不符（声明 {z['luma_mean']}/{z['luma_std']}，重测 {m:.0f}/{sd:.0f}）")
            else:
                (c.warn if c.case else c.err)(st, f"{kid}.{z['id']} 无法重测（关键帧文件不可用）")
        if s.get('narrative_anchor'): ids.add(s['narrative_anchor'].get('id'))
        probs = s.get('problems', [])
        if not probs: c.err(st, f'{kid} 没有写视觉问题')
        for pr in probs:
            ev = pr.get('evidence', [])
            if not ev: c.err(st, f"{kid}.{pr.get('id')} 没有证据引用")
            for e in ev:
                if e not in ids: c.err(st, f"{kid}.{pr.get('id')} 引用了不存在的区域/保护区 {e}")

    # v1.4.10: direction hypothesis is formed AFTER V1 visual facts and BEFORE V2 reference selection.
    hyp=d.get('direction_hypothesis')
    if hyp is None:
        c.warn(st, 'legacy V1 没有 direction_hypothesis；新项目必须在 V2 前先做方向初判')
    else:
        if hyp.get('analysis_order') != 'after_visual_problem_before_reference':
            c.err(st, 'direction_hypothesis.analysis_order 必须是 after_visual_problem_before_reference')
        gb=hyp.get('global_baseline') or {}
        _validate_direction_record(c, st, gb, 'direction_hypothesis.global_baseline')
        if 'REF-' in json.dumps(hyp,ensure_ascii=False) or 'XR-' in json.dumps(hyp,ensure_ascii=False) or 'MR-' in json.dumps(hyp,ensure_ascii=False):
            c.err(st, 'V1 direction_hypothesis 不得引用 REF/XR/MR；方向初判必须先于参考选择')
        rows=hyp.get('per_shot') or []
        by={x.get('keyframe'):x for x in rows if isinstance(x,dict)}
        for kid in usable:
            if kid not in by:
                c.err(st, f'direction_hypothesis.per_shot 缺 {kid}')
            else:
                _validate_direction_record(c, st, by[kid], f'direction_hypothesis.per_shot[{kid}]')


def _v1_index(c):
    """Everything V1 defines, keyed 'M01.Z1' etc., plus zone geometry/measurements for condition tests."""
    ids, zones, per_shot = set(), {}, {}
    for s in c.data['V1-visual-problems'].get('shots', []):
        k = s['keyframe']; per_shot[k] = set()
        for z in s.get('zones', []):
            key = f"{k}.{z['id']}"; ids.add(key); per_shot[k].add(key)
            r = z['rect_src']
            zones[key] = {'luma_mean': z.get('luma_mean'), 'luma_std': z.get('luma_std'),
                          'width_src': r[2] - r[0], 'height_src': r[3] - r[1], 'aspect_hw': (r[3] - r[1]) / max(1, r[2] - r[0])}
        for p in s.get('protect', []):
            ids.add(f"{k}.{p['id']}"); per_shot[k].add(f"{k}.{p['id']}")
        if s.get('narrative_anchor'):
            a = f"{k}.{s['narrative_anchor']['id']}"; ids.add(a); per_shot[k].add(a)
    return ids, zones, per_shot


OPS = {'<=': lambda a, b: a <= b, '>=': lambda a, b: a >= b, '<': lambda a, b: a < b, '>': lambda a, b: a > b, '==': lambda a, b: a == b}


def eligible_measured_text_selections(c, v2):
    """Return verified layout selections by keyframe; timing/rhythm cannot waive text A/B."""
    v0 = c.data['V0-intake']
    shots = {row.get('keyframe'): row for row in c.data['V1-visual-problems'].get('shots', [])}
    keyframes = {row.get('id'): row for row in v0.get('keyframes', [])
                 if row.get('full_frame') and row.get('id') not in v0.get('blocked_keyframes', [])}
    v1ids, zones, per_shot = _v1_index(c)
    result = {}
    for selection in v2.get('selections', []):
        rid = selection.get('ref_id')
        policy = MEASURED_TEXT_LAYOUT_REFS.get(rid)
        reference = c.xr.get(rid) or {}
        # Use only the official measured card; a project-local replacement cannot grant a waiver.
        if not policy or reference.get('status') != 'measured' or selection.get('structure_card') != policy['card_id']:
            continue
        if any(row.get('card_id') == policy['card_id'] for row in v2.get('new_structure_cards', [])):
            continue
        card = c.cards.get(policy['card_id']) or {}
        if rid not in card.get('ref_ids', []) or card.get('measured', {}).get('status') != 'measured':
            continue
        problem = selection.get('problem') or ''
        kid = problem.split('.', 1)[0]
        shot = shots.get(kid) or {}
        if kid not in keyframes or problem not in {kid + '.' + str(row.get('id')) for row in shot.get('problems', [])}:
            continue
        context = shot.get('text_reference_context') or {}
        faces = [row for row in shot.get('protect', []) if row.get('class') == 'face']
        bodies = [row for row in shot.get('protect', []) if row.get('class') == 'body']
        if (context.get('purpose') != policy['purpose']
                or type(context.get('person_count')) is not int
                or context['person_count'] != policy['person_count']
                or len(faces) != 1 or len(bodies) > 1
                or context.get('referent') != faces[0].get('id')):
            continue
        copy = [row for row in v0.get('confirmed_from_d2', {}).get('copy_lines', [])
                if row.get('unit') == keyframes[kid].get('unit')]
        if not copy or any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9 .,'’()/\-]*", str(row.get('text', '')))
                           or len(norm(str(row.get('text', '')))) > policy['max_label_characters'] for row in copy):
            continue
        copy_ids = {row.get('id') for row in copy}
        conditions = {row['id']: row for row in card.get('conditions', [])}
        transfers = {row['id']: row for row in card.get('transfer', [])}
        valid = set()
        for tid in selection.get('transfer', []):
            transfer = transfers.get(tid)
            if tid not in policy['layout_transfers'] or not transfer or not transfer.get('requires'):
                continue
            matches = True
            for cid in transfer['requires']:
                condition = conditions.get(cid) or {}
                evidence = (selection.get('conditions') or {}).get(cid) or {}
                evidence_ids = {re.split('[:：]', str(value), 1)[0].strip() for value in evidence.get('evidence', [])}
                if evidence.get('status') != 'met' or not evidence_ids or not evidence_ids <= (per_shot.get(kid, set()) | copy_ids):
                    matches = False; break
                test = condition.get('test')
                if test:
                    zone_id = evidence.get('zone')
                    actual = zones.get(zone_id, {}).get(test['metric'].split('.', 1)[-1])
                    if zone_id not in per_shot.get(kid, set()) or actual is None or not OPS[test['op']](actual, test['value']):
                        matches = False; break
            if matches:
                valid.add(tid)
        if valid:
            result.setdefault(kid, {})[problem + '/' + rid] = {
                'transfers': valid, 'referent': kid + '.' + context['referent'],
                'copy': {norm(row['text']) for row in copy},
            }
    return result


def measured_text_covered_keyframes(c, v5):
    """A waiver covers only the actual candidate elements using a matched selection."""
    eligible = eligible_measured_text_selections(c, c.data['V2-reference-selection'])
    candidates = {row.get('id'): row for row in c.data['V3-candidates'].get('candidates', [])}
    rejected = {row.get('candidate') for row in v5.get('rejected', [])}
    mocks = [row for row in c.data['V4-mockups'].get('mockups', []) if row.get('candidate') not in rejected]
    covered_pairs = set()
    for mock in mocks:
        cid, kid = mock.get('candidate'), mock.get('keyframe')
        candidate = candidates.get(cid) or {}
        shot = next((row for row in candidate.get('per_shot', []) if row.get('keyframe') == kid), {})
        actual_elements = {row.get('id'): row for row in mock.get('elements', [])}
        planned_elements = {row.get('id'): row for row in shot.get('elements', [])}
        expected, shot_ids = set(actual_elements), set(planned_elements)
        applied = set()
        for trace in candidate.get('ref_trace', []):
            selection = eligible.get(kid, {}).get(trace.get('selection'))
            targets = trace.get('target_element_ids')
            if (not selection or trace.get('transfer') not in selection['transfers']
                    or trace.get('keyframe') != kid or not trace.get('applied_to')
                    or not isinstance(targets, list) or not targets
                    or any(not isinstance(value, str) for value in targets)
                    or not set(targets) <= (expected & shot_ids)
                    or any(norm(actual_elements[value].get('text', '')) not in selection['copy']
                           or norm(planned_elements[value].get('text', '')) != norm(actual_elements[value].get('text', ''))
                           for value in targets)
                    or shot.get('composition_grammar', {}).get('primary_subject') != selection['referent']):
                continue
            applied.update(targets)
        if expected and expected <= applied:
            covered_pairs.add((cid, kid))
    return {kid for kid in {row.get('keyframe') for row in mocks}
            if all((row.get('candidate'), kid) in covered_pairs for row in mocks if row.get('keyframe') == kid)}


def V2(c, d):
    st = 'V2-reference-selection'
    probs = {f"{s['keyframe']}.{p['id']}" for s in c.data['V1-visual-problems'].get('shots', []) for p in s.get('problems', [])}
    v1ids, zones, _ = _v1_index(c)
    copy_ids = {l['id'] for l in c.data['V0-intake']['confirmed_from_d2']['copy_lines']}
    hyp=(c.data['V1-visual-problems'].get('direction_hypothesis') or {})
    dctx=d.get('direction_context')
    if hyp:
        if not isinstance(dctx,dict):
            c.err(st, '新方向契约要求 V2.direction_context：参考选择必须发生在 V1 方向初判之后')
        else:
            expected=(hyp.get('global_baseline') or {}).get('primary_direction')
            if dctx.get('source') != 'V1.direction_hypothesis': c.err(st, 'direction_context.source 必须是 V1.direction_hypothesis')
            if dctx.get('global_primary_direction') != expected: c.err(st, 'direction_context.global_primary_direction 必须与 V1 初判一致')
            if len(str(dctx.get('reference_goal','')).strip()) < 10: c.err(st, 'direction_context.reference_goal 过短')
    cards = dict(c.cards)
    for nc in d.get('new_structure_cards', []):
        for k in ('card_id', 'ref_ids', 'conditions', 'measured', 'transfer', 'do_not_transfer'):
            if k not in nc: c.err(st, f"新结构卡 {nc.get('card_id')} 缺 {k}")
        cards[nc.get('card_id')] = nc
    covered = set(d.get('no_ref_needed', {}).keys())
    per_prob = {}
    for i, s in enumerate(d.get('selections', [])):
        tag = f"selection[{i}] {s.get('problem')}/{s.get('ref_id')}"
        if s.get('problem') not in probs: c.err(st, f'{tag}: problem 不在 V1 里')
        if hyp:
            fit=s.get('direction_fit')
            if not isinstance(fit,dict): c.err(st, f'{tag}: 新方向契约下必须写 direction_fit，说明参考如何校准初步方向')
            else:
                if not fit.get('supports'): c.err(st, f'{tag}: direction_fit.supports 不能为空')
                if len(str(fit.get('calibration_role','')).strip()) < 10: c.err(st, f'{tag}: direction_fit.calibration_role 过短')
        if s.get('ref_id') not in c.refs: c.err(st, f'{tag}: ref_id 不在参考库里')
        card = cards.get(s.get('structure_card'))
        if not card: c.err(st, f'{tag}: 没有结构卡（先在 new_structure_cards 里补卡）'); continue
        if s.get('ref_id') not in card['ref_ids']: c.err(st, f'{tag}: 结构卡 {card["card_id"]} 不对应这张 REF')
        xr = c.xr.get(s.get('ref_id'))
        if xr and xr.get('status') == 'queued':
            c.warn(st, f"{tag}: 外部参考 {xr['ref_id']} 还在待确认队列（{'；'.join(xr.get('needs_viewing', []))}），自补的卡只能当假设")
        if card.get('measured', {}).get('status') == 'pending':
            c.warn(st, f"{tag}: 参考实测未完成（原则可用），迁移项只按原则使用，不得引用参考的具体数值")
        route = card.get('route') or (xr or {}).get('route')
        if route == 'special_case':
            c.warn(st, f"{tag}: 特殊情况参考（{card.get('route_note', '')}），不进入默认视觉路径；在 note 里写明本镜头为什么属于这种情况")
        elif route == 'fallback':
            c.warn(st, f"{tag}: 退路参考（{card.get('route_note', '')}），只在文字不能压画面时使用")
        conds = {x['id']: x for x in card['conditions']}
        ev = s.get('conditions', {})
        status = {}
        for cid_, cd_ in conds.items():
            e = ev.get(cid_)
            if not e: c.err(st, f'{tag}: 条件 {cid_}（{cd_["name"]}）没有逐条判定'); continue
            stt = e.get('status')
            if stt not in ('met', 'not_met', 'created_by_design'):
                c.err(st, f'{tag}: {cid_} 的 status 必须是 met / not_met / created_by_design（没有 partial）'); continue
            status[cid_] = stt
            refs = e.get('evidence', [])
            if not refs: c.err(st, f'{tag}: {cid_} 没有证据')
            for r in refs:
                key = re.split('[:：]', r)[0].strip()
                if key not in v1ids and key not in copy_ids: c.err(st, f'{tag}: {cid_} 的证据 {r} 没有引用 V1 区域 / 保护区或 V0 文案 id')
            if stt == 'created_by_design':
                if not cd_.get('creatable_by'): c.err(st, f'{tag}: {cid_} 不能由设计创造，只能是 met 或 not_met')
                if not e.get('how'): c.err(st, f'{tag}: {cid_} created_by_design 必须写 how（用什么几何手段创造、代价是什么）')
            t = cd_.get('test')
            if t and stt == 'met':
                z = e.get('zone')
                if z not in zones: c.err(st, f'{tag}: {cid_} 有可测条件，status=met 时必须指定 V1 区域 zone'); continue
                val = zones[z].get(t['metric'].split('.', 1)[1])
                if val is None or not OPS[t['op']](val, t['value']):
                    c.err(st, f"{tag}: {cid_} 声称满足，但 {z} 的 {t['metric'].split('.', 1)[1]}={val} 不满足 {t['op']} {t['value']}")
        tmap = {x['id']: x for x in card['transfer']}
        for tid in s.get('transfer', []):
            tr = tmap.get(tid)
            if not tr: c.err(st, f'{tag}: 迁移项 {tid} 不在结构卡 transfer 里'); continue
            for req in tr['requires']:
                if status.get(req) not in ('met', 'created_by_design'):
                    c.err(st, f'{tag}: 迁移项 {tid}「{tr["item"]}」需要 {req}（{conds[req]["name"]}），但该条件未满足')
        missing = set(card['do_not_transfer']) - set(s.get('do_not_transfer', []))
        if missing: c.err(st, f'{tag}: do_not_transfer 必须包含结构卡全部不迁项，缺 {sorted(missing)}')
        per_prob.setdefault(s.get('problem'), []).append(s)
    for p in probs:
        n = len(per_prob.get(p, []))
        if p not in covered and n == 0: c.err(st, f'{p} 没有选参考，也没有在 no_ref_needed 里说明原因')
        if n > 3: c.err(st, f'{p} 选了 {n} 张参考（上限 3）')
    eligible = eligible_measured_text_selections(c, d)
    c.flags['eligible_measured_text_keyframes'] = set(eligible)
    if (c.data['V0-intake'].get('design_scope') or {}).get('mode','explore_new')=='explore_new':
        c.warn(st, '公开版无预置已测豁免项；V5 新风格探索需要代表性 same_source_ab')


TEXT_SHAPES = {'single_line', 'stacked_block', 'split_pair', 'column', 'column_pair', 'band'}


def V3(c, d):
    st = 'V3-candidates'
    v0 = c.data['V0-intake']; v2 = c.data['V2-reference-selection']
    copy = {norm(l['text']) for l in v0['confirmed_from_d2']['copy_lines']}
    copy_ids = {l['id'] for l in v0['confirmed_from_d2']['copy_lines']}
    v1ids, zones, per_shot_ids = _v1_index(c)
    shots = set(per_shot_ids)
    sels = {f"{s['problem']}/{s['ref_id']}": s for s in v2.get('selections', [])}
    cards = dict(c.cards); cards.update({x['card_id']: x for x in v2.get('new_structure_cards', [])})
    cands = d.get('candidates', [])
    v1hyp=(c.data['V1-visual-problems'].get('direction_hypothesis') or {})
    global_dir=d.get('direction_read')
    if v1hyp:
        if not isinstance(global_dir,dict):
            c.err(st, 'V3.direction_read 缺失：必须在 V1 初判 + V2 参考校准后深化全局方向')
        else:
            _validate_direction_record(c, st, global_dir, 'direction_read', require_typography=True)
            if global_dir.get('source_hypothesis') not in (None,'V1.direction_hypothesis'):
                c.err(st, 'direction_read.source_hypothesis 必须指向 V1.direction_hypothesis')
    design_mode=(v0.get('design_scope') or {}).get('mode','explore_new')
    if design_mode == 'explore_new':
        if not 2 <= len(cands) <= 3: c.err(st, f'新风格探索必须 2–3 个候选，现在 {len(cands)} 个')
    elif not 1 <= len(cands) <= 3:
        c.err(st, f'{design_mode} 允许 1–3 个候选，现在 {len(cands)} 个')

    scope=d.get('validation_scope') or {'mode':'full'}
    scope_mode=scope.get('mode','full')
    if scope_mode not in ('full','representative_first'):
        c.err(st, 'validation_scope.mode 必须是 full / representative_first')
        required_shots=shots
    elif scope_mode == 'representative_first':
        reps=set(scope.get('representative_keyframes',[]))
        if not reps: c.err(st, 'representative_first 必须列 representative_keyframes')
        if reps - shots: c.err(st, f'representative_keyframes 包含未登记镜头 {sorted(reps-shots)}')
        rr=scope.get('representative_reason') or {}
        for k in reps:
            if len(str(rr.get(k,'')).strip()) < 8:
                c.err(st, f'{k}: representative_reason 过短；说明它代表的版式/困难条件')
        deferred=scope.get('deferred_keyframes') or {}
        if isinstance(deferred, list): deferred={k:'' for k in deferred}
        if not isinstance(deferred, dict):
            c.err(st, 'deferred_keyframes 必须是 {keyframe: metadata}'); deferred={}
        expected=shots-reps
        if set(deferred) != expected:
            c.err(st, f'deferred_keyframes 必须恰好覆盖未验证镜头：{sorted(expected)}')
        difficult=set()
        for k in expected:
            meta=deferred.get(k,'')
            if isinstance(meta,str):
                if len(meta.strip()) < 8: c.err(st, f'{k}: deferred_keyframes 必须说明将由哪个代表条件覆盖/何时展开')
                c.warn(st, f'{k}: 使用 legacy deferred 字符串；新项目建议标 difficulty / risk_tags')
                continue
            if not isinstance(meta,dict): c.err(st, f'{k}: deferred metadata 必须是对象'); continue
            if len(str(meta.get('reason','')).strip()) < 8: c.err(st, f'{k}: deferred.reason 过短')
            if meta.get('covered_by') not in reps: c.err(st, f'{k}: deferred.covered_by 必须指向已验证代表帧')
            diff=meta.get('difficulty','standard')
            if diff not in ('standard','difficult'): c.err(st, f'{k}: difficulty 必须 standard / difficult')
            tags=set(meta.get('risk_tags') or [])
            if tags-DEFERRED_RISK_TAGS: c.err(st, f'{k}: risk_tags 包含未知项 {sorted(tags-DEFERRED_RISK_TAGS)}')
            if diff=='difficult':
                difficult.add(k)
                if not tags: c.err(st, f'{k}: difficult 镜头必须写 risk_tags（长文字/多人/复杂背景等）')
        c.flags['difficult_deferred_keyframes']=difficult
        required_shots=reps
    else:
        required_shots=shots
    for cd in cands:
        cid = cd.get('id')
        if v1hyp:
            ds=cd.get('direction_strategy')
            if not isinstance(ds,dict): c.err(st, f'{cid}: 缺 direction_strategy（候选必须声明自己的观看逻辑）')
            else: _validate_direction_record(c, st, ds, f'{cid}.direction_strategy')
        # --- Art Direction layer
        th = cd.get('art_direction_thesis', {})
        if len(th.get('statement', '')) < 20: c.err(st, f'{cid}: art_direction_thesis.statement 缺失或过短（一句话说清这版设计怎样参与叙事）')
        if not set(th.get('copy_refs', [])) & copy_ids: c.err(st, f'{cid}: thesis 必须引用至少一句 V0 文案（copy_refs）')
        if not set(th.get('image_refs', [])) & v1ids: c.err(st, f'{cid}: thesis 必须引用至少一个 V1 画面元素（image_refs）')
        for r in th.get('copy_refs', []):
            if r not in copy_ids: c.err(st, f'{cid}: thesis.copy_refs {r} 不存在')
        for r in th.get('image_refs', []):
            if r not in v1ids: c.err(st, f'{cid}: thesis.image_refs {r} 不存在')
        fc = cd.get('failure_condition', [])
        if not fc: c.err(st, f'{cid}: failure_condition 为空（成熟的方案要知道自己在什么情况下不成立）')
        for f in fc:
            if len(f.get('condition', '')) < 8: c.err(st, f'{cid}: failure_condition 条目过短')
            m = f.get('measure')
            if m and m.get('zone') not in zones: c.err(st, f"{cid}: failure_condition.measure 引用了不存在的区域 {m.get('zone')}")
        # --- structure
        dims = cd.get('dimensions', {})
        for k, en in DIM_ENUMS.items():
            if dims.get(k) not in en: c.err(st, f'{cid}: dimensions.{k} 必须是 {sorted(en)} 之一')
        sty = cd.get('style', {})
        for k in ('fonts', 'roles', 'ink'):
            if k not in sty: c.err(st, f'{cid}: style 缺 {k}（必须给出可执行参数，不是形容词）')
        for rn, r in sty.get('roles', {}).items():
            if r.get('font') not in sty.get('fonts', {}): c.err(st, f'{cid}: role {rn} 的字体未在 fonts 里声明')
        tr = cd.get('ref_trace', [])
        if v2.get('selections') and not tr:
            c.err(st, f'{cid}: V2 已使用参考时 ref_trace 不能为空')
        if not v2.get('selections') and tr:
            c.err(st, f'{cid}: V2 全部为 no_ref_needed 时不得虚构 ref_trace')
        for t in tr:
            s = sels.get(t.get('selection'))
            if not s: c.err(st, f"{cid}: ref_trace 引用了不存在的 selection {t.get('selection')}"); continue
            if t.get('transfer') not in s.get('transfer', []): c.err(st, f"{cid}: 迁移项 {t.get('transfer')} 不在该 selection 的 transfer 里")
            if not t.get('applied_to'): c.err(st, f'{cid}: ref_trace 缺 applied_to（落到哪个维度或元素）')
            card = cards.get(s.get('structure_card'))
            if card:
                tr_ = next((x for x in card['transfer'] if x['id'] == t.get('transfer')), None)
                for req in (tr_ or {}).get('requires', []):
                    e = s.get('conditions', {}).get(req, {})
                    if e.get('status') == 'created_by_design':
                        allowed = next(x for x in card['conditions'] if x['id'] == req).get('creatable_by', [])
                        if dims.get('geometry') not in allowed:
                            c.err(st, f"{cid}: 依赖“由设计创造”的条件 {req}，但方案几何 {dims.get('geometry')} 不在 {allowed} 里")
        covered = set()
        for ps in cd.get('per_shot', []):
            kf = ps.get('keyframe'); covered.add(kf)
            if v1hyp:
                du=ps.get('direction_use')
                if not isinstance(du,dict): c.err(st, f'{cid}/{kf}: 缺 direction_use（同一视频不同镜头允许不同方向，但必须说清）')
                else: _validate_direction_record(c, st, du, f'{cid}/{kf}.direction_use')
            el_ids = set()
            for e in ps.get('elements', []):
                el_ids.add(e.get('id'))
                if norm(e.get('text', '')) not in copy: c.err(st, f"{cid}: 元素 {e.get('id')} 的文字「{e.get('text')}」不在 V0 登记文案里（不得自行改写）")
                if e.get('role') not in sty.get('roles', {}): c.err(st, f"{cid}: 元素 {e.get('id')} 的 role 未在 style.roles 里")
            g = ps.get('composition_grammar', {})
            tag = f'{cid}/{kf}'
            if g.get('primary_subject') not in per_shot_ids.get(kf, set()): c.err(st, f'{tag}: composition_grammar.primary_subject 必须是本镜头 V1 元素')
            if g.get('text_shape') not in TEXT_SHAPES: c.err(st, f'{tag}: text_shape 必须是 {sorted(TEXT_SHAPES)} 之一')
            ns = g.get('negative_space')
            if ns != 'none' and ns not in per_shot_ids.get(kf, set()): c.err(st, f'{tag}: negative_space 必须是本镜头 V1 区域或 "none"')
            if len(g.get('visual_axis', '')) < 8: c.err(st, f'{tag}: visual_axis 缺失')
            if len(g.get('visual_weight', '')) < 8: c.err(st, f'{tag}: visual_weight 缺失')
            ro = g.get('reading_order', [])
            if len(ro) < 3: c.err(st, f'{tag}: reading_order 至少 3 步')
            if not el_ids <= set(ro): c.err(st, f'{tag}: reading_order 必须包含本镜头全部文字元素')
            if not (set(ro) & per_shot_ids.get(kf, set())): c.err(st, f'{tag}: reading_order 必须包含画面元素，不能只排文字')
            for r in ro:
                if r not in el_ids and r not in per_shot_ids.get(kf, set()): c.err(st, f'{tag}: reading_order 的 {r} 不是本镜头元素')
            sd = ps.get('shot_dependency', {})
            dep = set(sd.get('depends_on', []))
            if not dep: c.err(st, f'{tag}: shot_dependency.depends_on 为空（说不出依赖本镜头什么，就可能是模板）')
            if dep - per_shot_ids.get(kf, set()): c.err(st, f'{tag}: shot_dependency 引用了不属于本镜头的元素 {sorted(dep - per_shot_ids.get(kf, set()))}')
            if len(sd.get('if_moved', '')) < 10: c.err(st, f'{tag}: shot_dependency.if_moved 缺失（换到别的镜头会怎样）')
        for s_ in required_shots - covered: c.err(st, f'{cid}: 没有覆盖本轮验证镜头 {s_}')
        extra=covered-shots
        if extra: c.err(st, f'{cid}: per_shot 包含未登记镜头 {sorted(extra)}')
    for i in range(len(cands)):
        for j in range(i + 1, len(cands)):
            ca, cb = cands[i], cands[j]
            a, b = ca.get('dimensions', {}), cb.get('dimensions', {})
            formal_axes=[k for k in DIM_ENUMS if a.get(k) != b.get(k)]
            narrative_axes=[]
            if v1hyp:
                sa,sb=_candidate_direction_signature(ca),_candidate_direction_signature(cb)
                for k in ('primary_direction','text_role','spatial_relation','timing_mode','emphasis_budget','attention_sequence','per_shot'):
                    if sa.get(k) != sb.get(k): narrative_axes.append(k)
            total=len(formal_axes)+len(narrative_axes)
            if total < 2:
                c.err(st, f"{ca.get('id')} 与 {cb.get('id')} 只有 {total} 个实质差异轴（形式 {formal_axes}；叙事 {narrative_axes}）。至少 2 个；注意力顺序/文字角色/空间关系/timing 可以成立，不要求为了比稿硬改画幅或文字方向。")


def V4(c, d):
    st = 'V4-mockups'
    tp = c.data['V0-intake']['text_policy']
    v3 = c.data['V3-candidates']
    copy = {norm(l['text']) for l in c.data['V0-intake']['confirmed_from_d2']['copy_lines']}
    need = {(cd['id'], ps['keyframe']) for cd in v3.get('candidates', []) for ps in cd.get('per_shot', [])}
    have = set()
    if not d.get('renderer'): c.err(st, '缺 renderer（必须记录用什么工具渲染）')
    for m in d.get('mockups', []):
        key = (m.get('candidate'), m.get('keyframe')); have.add(key); tag = f'{key[0]}/{key[1]}'
        if m.get('scale_x_equals_scale_y') is not True: c.err(st, f'{tag}: 必须等比缩放（scale_x == scale_y）')
        f = c.path(m.get('file', ''))
        if os.path.exists(f):
            if sha(f) != m.get('sha256'): c.err(st, f'{tag}: 文件哈希与记录不符')
        else:
            (c.warn if c.case else c.err)(st, f'{tag}: Mockup 文件不可用 {m.get("file")}')
        bs = m.get('burned_subtitle_glyph_px')
        if bs is None and (m.get('geometry', {}).get('mode') == 'letterbox' or m.get('geometry', {}).get('scale', 1.0) < 1.0):
            c.err(st, f'{tag}: 画面被缩小时必须记录 burned_subtitle_glyph_px')
        if isinstance(bs, (int, float)) and bs < tp['glyph_floor_px']:
            c.warn(st, f'{tag}: 烧录字幕缩到 {bs}px，低于 {tp["glyph_floor_px"]}px —— V5 必须否决该方案或给出解决办法')
            c.flags.setdefault('subtitle_shrink', set()).add(m.get('candidate'))
        els = m.get('elements', [])
        qa_elements(c, st, els, tp, tag)
    for k in need - have:
        if f'{k[0]}/{k[1]}' not in d.get('skipped', {}): c.err(st, f'缺 Mockup：{k[0]}/{k[1]}（或在 skipped 里写原因）')


def V5(c, d):
    st = 'V5-design-review'
    if d.get('quality_claim') != 'not_automated':
        c.err(st, 'quality_claim 必须是 not_automated：V5 只证明证据链完整，不自动证明“高级感”')

    cands = {cd['id'] for cd in c.data['V3-candidates']['candidates']}
    v3map = {x['id']: x for x in c.data['V3-candidates'].get('candidates', [])}
    v2sels = {f"{x.get('problem')}/{x.get('ref_id')}": x for x in c.data['V2-reference-selection'].get('selections', [])}
    cards = dict(c.cards); cards.update({x['card_id']: x for x in c.data['V2-reference-selection'].get('new_structure_cards', [])})
    v4list = c.data['V4-mockups'].get('mockups', [])
    v4map = {(m.get('candidate'), m.get('keyframe')): m for m in v4list}
    v4_ev = {(m.get('candidate'), m.get('keyframe')): {e.get('id') for e in m.get('elements', [])} for m in v4list}

    # Subjective design explanations are useful context but are not a machine-enforced beauty gate.
    ev_ids = set()
    for shot in c.data['V1-visual-problems']['shots']:
        ev_ids |= {f"{shot['keyframe']}.{z['id']}" for z in shot.get('zones', [])} | {f"{shot['keyframe']}.{p['id']}" for p in shot.get('protect', [])}
    for m in v4list: ev_ids |= {e['id'] for e in m.get('elements', [])}
    reviewed=set()
    for r in d.get('reviews', []):
        cid=r.get('candidate'); reviewed.add(cid)
        if cid not in cands: c.warn(st, f'设计论证引用未知候选 {cid}')
        for k in REVIEW_KEYS:
            q=r.get(k)
            if not q or len(q.get('answer',''))<15:
                c.warn(st, f'{cid}.{k}: 设计论证缺失或过短（不会自动判审美失败，但建议补全）'); continue
            for e in q.get('evidence',[]):
                if e not in ev_ids: c.warn(st, f'{cid}.{k}: 论证证据 {e} 未绑定到 V1/V4')
    for cid in cands-reviewed: c.warn(st, f'候选 {cid} 没有主观设计论证；V5 仍只按机械证据 Gate')
    rec=d.get('recommendation') or {}
    if rec and rec.get('candidate') not in cands: c.warn(st, 'recommendation.candidate 不是有效候选')

    rejected={x.get('candidate') for x in d.get('rejected',[]) if x.get('candidate')}
    for rj in d.get('rejected',[]):
        if rj.get('candidate') not in cands: c.err(st, f"否决了不存在的候选 {rj.get('candidate')}")
        if not rj.get('evidence'): c.warn(st, f"否决 {rj.get('candidate')} 没有 evidence")
    for cid in c.flags.get('subtitle_shrink', set()) - rejected:
        c.err(st, f'候选 {cid} 在 V4 把烧录字幕缩到底线以下，V5 必须否决或回 V4 修复')

    # Hard check: do-not-transfer checks must be complete and evidence must come from the same candidate+shot V4.
    review_map={r.get('candidate'):r for r in d.get('reviews',[])}
    for cid in cands:
        expected=set()
        for tr in (v3map.get(cid) or {}).get('ref_trace', []):
            sel=v2sels.get(tr.get('selection'))
            if not sel: continue
            card=cards.get(sel.get('structure_card'))
            for item in (card or {}).get('do_not_transfer', []): expected.add((tr.get('selection'), item))
        rr=review_map.get(cid) or {}
        checks=rr.get('do_not_transfer_checks', [])
        seen=set(); got={}
        for x in checks:
            key=(x.get('selection'),x.get('item'))
            if key in seen: c.err(st, f'{cid}: do_not_transfer_check 重复 {key[0]} / {key[1]}')
            seen.add(key); got[key]=x
        for key in expected:
            x=got.get(key)
            if not x:
                c.err(st, f'{cid}: 缺 do_not_transfer_check {key[0]} / {key[1]}'); continue
            status=x.get('status')
            if status not in ('pass','fail'): c.err(st, f'{cid}: do_not_transfer_check.status 必须 pass/fail')
            if status=='fail' and cid not in rejected:
                c.err(st, f'{cid}: 如实发现 do_not_transfer 违规可以写 fail，但该候选必须列入 rejected，或回 V4 修改后重做 V5')
            if len(x.get('finding',''))<10: c.err(st, f'{cid}: do_not_transfer_check finding 过短 {key[1]}')
            problem=key[0].split('/',1)[0]
            kf=problem.split('.',1)[0]
            allowed=v4_ev.get((cid,kf),set())
            evidence=x.get('evidence') or []
            if not evidence: c.err(st, f'{cid}: do_not_transfer_check 缺 evidence {key[1]}')
            for e in evidence:
                if e not in allowed:
                    c.err(st, f'{cid}: do_not_transfer_check 证据 {e} 必须属于同一候选 {cid}、对应镜头 {kf} 的 V4 元素')

    # Reference coverage is local to actual rendered text elements, never a whole-video flag.
    mode=(c.data['V0-intake'].get('design_scope') or {}).get('mode','explore_new')
    covered_kfs = measured_text_covered_keyframes(c, d)
    review_kfs = {row.get('keyframe') for row in v4list if row.get('candidate') not in rejected}
    uncovered_kfs = review_kfs - covered_kfs
    c.flags['measured_text_covered_keyframes'] = covered_kfs
    needs_ab = bool(uncovered_kfs) or not review_kfs
    if mode=='explore_new' and (needs_ab or d.get('same_source_ab')):
        ab=d.get('same_source_ab') or {}
        if not isinstance(ab, dict):
            c.err(st, 'same_source_ab 必须是对象'); ab = {}
        controls=ab.get('controls') or {}
        if not ab: c.err(st, f'缺 same_source_ab：关键帧 {sorted(uncovered_kfs)} 未被适用且实际迁移的 measured 文字设计参考覆盖，仍需同素材 A/B')
        else:
            kf=controls.get('keyframe')
            valid_kfs={m.get('keyframe') for m in v4list}
            if kf not in valid_kfs: c.err(st, 'same_source_ab.controls.keyframe 必须是本轮 V4 已渲染关键帧')
            if needs_ab and uncovered_kfs and kf not in uncovered_kfs:
                c.err(st, f'same_source_ab 必须选未覆盖的代表关键帧 {sorted(uncovered_kfs)}，不能用已豁免镜头替其他镜头通过')
            expected_copy={x['id'] for x in c.data['V0-intake']['confirmed_from_d2'].get('copy_lines',[]) if x.get('unit') in {y.get('unit') for y in c.data['V0-intake'].get('keyframes',[]) if y.get('id')==kf}}
            got_copy=set(controls.get('copy_ids') or [])
            all_copy={x['id'] for x in c.data['V0-intake']['confirmed_from_d2'].get('copy_lines',[])}
            if not got_copy or not got_copy <= all_copy:
                c.err(st, 'same_source_ab.controls.copy_ids 必须引用 V0 文案 id')
            elif got_copy != expected_copy:
                c.err(st, f'same_source_ab.controls.copy_ids 必须精确等于当前关键帧 {kf} 所属 unit 的文案 {sorted(expected_copy)}，不能借用其他段落文案')
            if controls.get('same_source') is not True or controls.get('same_canvas') is not True or controls.get('same_copy') is not True:
                c.err(st, 'same_source_ab 必须明确 same_source / same_canvas / same_copy = true')
            # exact source-frame binding: same_source=true is not enough by itself.
            sf=controls.get('source_frame') or {}
            krow=next((y for y in c.data['V0-intake'].get('keyframes',[]) if y.get('id')==kf),None)
            if not krow or sf.get('keyframe')!=kf or sf.get('file')!=krow.get('file'):
                c.err(st, 'same_source_ab.controls.source_frame 必须精确绑定 V0 当前 keyframe 的 file/id')
            elif krow.get('file'):
                fp=c.path(krow['file'])
                if os.path.exists(fp):
                    actual=sha(fp)
                    if sf.get('sha256')!=actual: c.err(st, 'same_source_ab.controls.source_frame.sha256 与当前源帧不一致')
                elif not c.case: c.err(st, 'same_source_ab 当前源帧文件不存在，无法证明 same_source')
            baseline_ok=verify_artifact(c, st, ab.get('baseline'), 'same_source_ab.baseline')
            cand_art=ab.get('candidate') or {}
            cand_ok=verify_artifact(c, st, cand_art, 'same_source_ab.candidate')
            key=(cand_art.get('candidate'),cand_art.get('keyframe'))
            src=v4map.get(key)
            if not src or cand_art.get('file')!=src.get('file') or cand_art.get('sha256')!=src.get('sha256') or cand_art.get('keyframe')!=kf:
                c.err(st, 'same_source_ab.candidate 必须精确绑定当前 V4 同一关键帧的候选 Mockup')
            # canvas is evidence, not a boolean claim: compare declared canvas and actual PNG dimensions.
            canvas=controls.get('canvas')
            if not (isinstance(canvas,list) and len(canvas)==2 and all(isinstance(x,int) and x>0 for x in canvas)):
                c.err(st, 'same_source_ab.controls.canvas 必须是 [width,height]')
            baseline_path=c.path((ab.get('baseline') or {}).get('file',''))
            candidate_path=c.path(cand_art.get('file',''))
            decoded_same=None
            if baseline_ok and cand_ok and os.path.exists(baseline_path) and os.path.exists(candidate_path):
                try:
                    from PIL import Image
                    bs=Image.open(baseline_path).size; cs=Image.open(candidate_path).size
                    if list(bs)!=canvas or list(cs)!=canvas: c.err(st, f'same_source_ab 实际画布必须都等于 controls.canvas {canvas}，当前 baseline={bs}, candidate={cs}')
                    decoded_same = decoded_pixel_sha(baseline_path) == decoded_pixel_sha(candidate_path)
                except Exception as e: c.err(st, f'same_source_ab 无法读取实际画布/解码像素: {e}')
            result=ab.get('result') or {}
            same_file=bool(ab.get('baseline',{}).get('sha256') and ab.get('baseline',{}).get('sha256')==cand_art.get('sha256'))
            same_visual = same_file or decoded_same is True
            if same_visual:
                if result.get('status')!='no_visible_change' or result.get('evidence_use')!='not_visual_improvement_evidence':
                    reason='文件 SHA 相同' if same_file else '解码后像素完全相同（文件元数据/编码差异不构成视觉变化）'
                    c.err(st, f'same_source_ab baseline 与 candidate 视觉相同：{reason}；只能记录 no_visible_change + not_visual_improvement_evidence，不能充当视觉提升证据')
                if cand_art.get('candidate') not in rejected:
                    c.err(st, 'same_source_ab 同图/同像素/无可见变化的候选必须 rejected 或回 V4 产生真实差异')
            elif result:
                if result.get('status') not in ('visible_change','no_visible_change'):
                    c.err(st, 'same_source_ab.result.status 必须 visible_change / no_visible_change')
                if result.get('status')=='no_visible_change' and cand_art.get('candidate') not in rejected:
                    c.err(st, 'same_source_ab 记录 no_visible_change 时，该候选不能作为有效视觉提升证据，必须 rejected 或回 V4')
            else:
                c.warn(st, 'same_source_ab.result 缺失；新项目应明确 visible_change / no_visible_change')
            obs=ab.get('observations') or {}
            for key in ('hierarchy','person_text_relation','typography_voice'):
                if len(str(obs.get(key,'')).strip()) < 12: c.err(st, f'same_source_ab.observations.{key} 过短')
            if controls.get('audio_unchanged') is not True:
                c.warn(st, '静态 V5 无法验证音频；建议记录 audio_unchanged=true，并在 Dynamic Proof 验证文字时机')

    # Small-screen evidence is always useful. Blur/squint is problem-driven; blind-map is only
    # required when an actual blind/independent review is used.
    ra=d.get('review_artifacts') or {}
    if not verify_artifact(c, st, ra.get('small_screen_board'), 'review_artifacts.small_screen_board'):
        c.err(st, '请运行 scripts/prepare_design_review.py <visual_dir> 生成 small-screen board')
    review_scope=d.get('review_scope')
    if review_scope is None and isinstance(ra.get('blur_squint_board'),dict) and ra['blur_squint_board'].get('file'):
        # Legacy v2.3.6 records generated blur+blind unconditionally; preserve them as an explicit used path.
        review_scope={'blur_squint':{'status':'used','reason':'existing review artifact'}}
    review_scope=review_scope or {}
    blur=review_scope.get('blur_squint') or {'status':'not_needed','reason':'未声明需要模糊/眯眼检查'}
    blur_status=blur.get('status','not_needed')
    if blur_status not in ('used','not_needed'):
        c.err(st, 'review_scope.blur_squint.status 必须是 used / not_needed')
    if blur_status == 'used':
        if not verify_artifact(c, st, ra.get('blur_squint_board'), 'review_artifacts.blur_squint_board'):
            c.err(st, 'blur_squint=used 时必须生成 blur/squint board')
    elif len(str(blur.get('reason','')).strip()) < 8:
        c.err(st, 'blur_squint=not_needed 时说明为什么本次不需要')

    bm=None; bmp=None
    blind_declared=isinstance(ra.get('blind_map'),dict) and bool(ra['blind_map'].get('file'))
    if blind_declared:
        if verify_artifact(c, st, ra.get('blind_map'), 'review_artifacts.blind_map'):
            bmp=c.path(ra['blind_map']['file'])
            try:
                bm=json.load(open(bmp,encoding='utf-8'))
            except Exception as e: c.err(st, f'blind-map 无法读取: {e}')
    if bm:
        if bm.get('v4_design_sha256'):
            if bm.get('v4_design_sha256') != design_sha_path(os.path.join(c.vdir,'V4-mockups.json')):
                c.err(st, 'blind-map 绑定的 V4 设计输入已变化；重新生成')
        elif bm.get('v4_sha256') != sha(os.path.join(c.vdir,'V4-mockups.json')):
            c.err(st, 'blind-map 绑定的 V4 已变化；重新生成')
        if not isinstance(bm.get('random_seed'),int) or bm.get('mapping_algorithm')!='python_random_shuffle_aliases_v1':
            c.err(st, 'blind-map 缺随机 seed / mapping_algorithm')
        else:
            sorted_c=sorted(cands); labels=[f'X{i+1}' for i in range(len(sorted_c))]
            shuffled=labels[:]; random.Random(bm['random_seed']).shuffle(shuffled)
            if len(sorted_c)>1 and shuffled==labels: shuffled=shuffled[1:]+shuffled[:1]
            expected_alias={cid:al for cid,al in zip(sorted_c,shuffled)}
            if bm.get('aliases') != expected_alias: c.err(st, 'blind-map aliases 与记录的随机 seed 不一致')
        if (bm.get('small_screen_board') or {}).get('sha256') != (ra.get('small_screen_board') or {}).get('sha256'):
            c.err(st, 'V5 small-screen board 与 blind-map 记录不一致；重新生成 blind review board')
        bm_blur=bm.get('blur_squint_board')
        if bm_blur:
            if blur_status != 'used': c.err(st, 'blind-map 包含 blur board，但 review_scope 未声明 blur_squint=used')
            elif bm_blur.get('sha256') != (ra.get('blur_squint_board') or {}).get('sha256'):
                c.err(st, 'V5 blur/squint board 与 blind-map 记录不一致；重新生成')
        records={(x.get('candidate'),x.get('keyframe')):x for x in bm.get('records',[])}
        for key,m in v4map.items():
            rec=records.get(key)
            if not rec: c.err(st, f'blind-map 缺 V4 source {key[0]}/{key[1]}'); continue
            if rec.get('source_kind')=='wireframe':
                if not c.case: c.err(st, f'{key[0]}/{key[1]} review board 使用 wireframe；正式项目禁止')
                wf=m.get('wireframe'); wfp=c.path(wf or '')
                if rec.get('source') != wf or not wf or not os.path.exists(wfp) or rec.get('source_sha256') != sha(wfp):
                    c.err(st, f'{key[0]}/{key[1]} synthetic wireframe source 没有绑定 V4.wireframe + 当前 SHA')
            elif rec.get('source') != m.get('file') or rec.get('source_sha256') != m.get('sha256'):
                c.err(st, f'blind-map {key[0]}/{key[1]} 没有绑定当前 V4 Mockup file+sha')

    # Independent review is conditional. Binding is hard if it is used; independence itself is only declared, not machine-proven.
    policy=(c.data['V0-intake'].get('design_review_policy') or {}).get('independent_review','optional')
    ir=d.get('independent_review') or {}
    irst=ir.get('status')
    if irst not in ('not_used','completed'):
        c.err(st, 'independent_review.status 必须是 not_used / completed')
    elif irst=='not_used':
        if len(ir.get('reason',''))<8: c.err(st, 'independent_review.status=not_used 时必须说明原因')
        if policy=='required': c.err(st, '项目要求 independent_review=required，但当前未执行独立评审')
    else:
        if not bm:
            c.err(st, '独立评审存在时必须有 blind-map；未做真实盲审不要生成 blind-map')
        if not verify_artifact(c, st, ir, 'independent_review'):
            c.err(st, '独立评审文件无效；重新运行 finalize_independent_review.py')
        else:
            try:
                data=json.load(open(c.path(ir['file']),encoding='utf-8'))
                if bm:
                    if data.get('source_blind_map_sha256') != sha(bmp): c.err(st, '独立评审绑定旧 blind-map；重新评审')
                    if data.get('small_screen_board_sha256') != (bm.get('small_screen_board') or {}).get('sha256'): c.err(st, '独立评审绑定旧 small-screen board')
                    bm_blur=bm.get('blur_squint_board')
                    if bm_blur and data.get('blur_squint_board_sha256') != bm_blur.get('sha256'): c.err(st, '独立评审绑定旧 blur/squint board')
                    if not bm_blur and data.get('blur_squint_board_sha256') not in (None,''): c.err(st, '本次 blind review 未使用 blur board，不应绑定 blur hash')
                gotc={x.get('candidate') for x in data.get('results',[])}
                if gotc != cands: c.err(st, f'independent_review 候选覆盖不完整: {sorted(gotc)} != {sorted(cands)}')
                req={'first_read','image_integration','typography','narrative_detail','template_risk_inverse','overall'}
                for x in data.get('results',[]):
                    if set((x.get('scores') or {}).keys()) != req: c.err(st, f"independent_review {x.get('candidate')} 评分项不完整")
                rv=data.get('reviewer') or {}
                for k in ('id','type','origin'):
                    if not str(rv.get(k,'')).strip(): c.err(st, f'independent_review reviewer.{k} 为空')
                if not isinstance(rv.get('independence_declared'),bool): c.err(st, 'independent_review reviewer.independence_declared 必须布尔值')
                elif rv.get('independence_declared') is not True:
                    if policy=='required': c.err(st, 'required 独立评审必须由 reviewer 声明独立；注意：代码只能验证声明，不能证明事实')
                    else: c.warn(st, 'reviewer 未声明独立；该评审仅作 advisory，不作为独立审查证据')
            except Exception as e: c.err(st, f'independent_review 无法读取/校验: {e}')

    pu=d.get('presented_to_user') or {}
    context=pu.get('context','user')
    if context!='user' and not (c.case and context=='synthetic_test'):
        c.err(st, 'presented_to_user.context 正式项目必须是 user；synthetic_test 仅允许 --case 测试夹具')
    if not pu.get('what'): c.err(st, 'presented_to_user.what 为空：必须把比较结果交给用户后才算完成')
    arts=pu.get('artifacts',[])
    if not arts: c.err(st, 'presented_to_user.artifacts 为空：必须记录用户实际看到的文件与哈希')
    for i,a in enumerate(arts):
        verify_artifact(c, st, a, f'presented_to_user.artifacts[{i}]')
        if a.get('candidate') not in cands | {'comparison'}: c.err(st, f'presented_to_user.artifacts[{i}].candidate 无效')

def V6(c, d):
    st = 'V6-user-decision'
    stt = d.get('status')
    if stt not in ('pending', 'confirmed', 'revise'): c.err(st, 'status 必须是 pending / confirmed / revise'); return 'fail'
    if stt == 'confirmed':
        cands={cd['id'] for cd in c.data['V3-candidates']['candidates']}
        chosen=d.get('chosen_candidate')
        if chosen not in cands: c.err(st, 'chosen_candidate 无效')
        if len(d.get('user_message_verbatim', '')) < 2: c.err(st, 'confirmed 必须附用户原话（模型不能替用户确认）')
        # If copy was only working at V0, a separate exact copy confirmation is mandatory here.
        cf=c.data['V0-intake']['confirmed_from_d2']
        if cf.get('copy_status') == 'working':
            cc=d.get('copy_confirmation') or {}
            if cc.get('status') != 'confirmed': c.err(st, 'V0 文案仍是 working；V6 confirmed 必须附 copy_confirmation.status=confirmed')
            line_map={x['id']:x['text'] for x in cf.get('copy_lines',[])}
            if cc.get('lines') != line_map: c.err(st, 'copy_confirmation.lines 必须逐字等于 V0 工作文案')
            if len(cc.get('user_message_verbatim','')) < 2: c.err(st, 'copy_confirmation 必须附用户逐字确认原话')
        # bind the approval to the exact artifacts shown in V5
        shown={(x.get('file'),x.get('sha256'),x.get('candidate')) for x in c.data['V5-design-review'].get('presented_to_user',{}).get('artifacts',[])}
        ca=d.get('confirmed_artifacts',[])
        if not ca: c.err(st, 'confirmed 必须附 confirmed_artifacts（用户实际确认的文件 + SHA）')
        has_chosen=False
        for i,a in enumerate(ca):
            tup=(a.get('file'),a.get('sha256'),a.get('candidate'))
            if tup not in shown: c.err(st, f'confirmed_artifacts[{i}] 不在 V5 实际展示清单或哈希不一致')
            verify_artifact(c, st, a, f'confirmed_artifacts[{i}]')
            if a.get('candidate') == chosen: has_chosen=True
        if not has_chosen: c.err(st, 'confirmed_artifacts 至少包含一个 chosen_candidate 的实际 Mockup/比较产物')
    return stt

def V7(c, d):
    st = 'V7-lock'
    v6 = c.data['V6-user-decision']
    ch = v6.get('chosen_candidate')
    if d.get('chosen_candidate') != ch: c.err(st, 'chosen_candidate 与 V6 不一致')
    cand = next((x for x in c.data['V3-candidates']['candidates'] if x['id'] == ch), None)
    if cand and d.get('style') != cand.get('style'): c.err(st, 'style 与 V3 选定方案不一致（建议用 sync_visual_stage.py 自动同步，不手填重复参数）')
    v4rows=[m for m in c.data['V4-mockups']['mockups'] if m['candidate'] == ch]
    v4els = {e['id']: e for m in v4rows for e in m['elements']}
    mockup_kfs={m.get('keyframe') for m in v4rows}
    scope=c.data['V3-candidates'].get('validation_scope') or {'mode':'full'}
    representative=scope.get('mode') == 'representative_first'
    valid_kfs={s.get('keyframe') for s in c.data['V1-visual-problems'].get('shots',[])}
    copy={norm(x.get('text','')) for x in c.data['V0-intake']['confirmed_from_d2'].get('copy_lines',[])}
    canvas=d.get('canvas')
    if not (isinstance(canvas,list) and len(canvas)==2 and all(isinstance(x,(int,float)) and x>0 for x in canvas)):
        c.err(st, 'canvas 必须是 [width,height] 正数'); canvas=[1,1]
    ids = set()
    for e in d.get('elements', []):
        ids.add(e.get('id'))
        eid=e.get('id')
        if eid in v4els:
            if norm(e.get('text', '')) != norm(v4els[eid].get('text', '')): c.err(st, f'元素 {eid} 文字与已验证 Mockup 不一致')
        elif representative:
            basis=e.get('validation_basis')
            if basis not in mockup_kfs: c.err(st, f'扩展元素 {eid} 必须用 validation_basis 指向已验证代表关键帧')
            if e.get('keyframe') not in valid_kfs: c.err(st, f'扩展元素 {eid} 的 keyframe 未登记')
            if norm(e.get('text','')) not in copy: c.err(st, f'扩展元素 {eid} 文字不在 V0 登记文案里')
            if cand and e.get('role') not in (cand.get('style') or {}).get('roles',{}): c.err(st, f'扩展元素 {eid} role 不在选定 style.roles')
            if len(str(e.get('adaptation','')).strip()) < 8: c.err(st, f'扩展元素 {eid} 必须说明从代表帧如何适配（adaptation）')
        else:
            c.err(st, f'元素 {eid} 不在已确认的 Mockup 里；full 验证模式禁止未验证扩展')
        rect=e.get('rect')
        if not (isinstance(rect,list) and len(rect)==4 and all(isinstance(x,(int,float)) for x in rect)):
            c.err(st, f'元素 {eid} rect 必须是 [x0,y0,x1,y1]')
        else:
            x0,y0,x1,y1=rect; W,H=canvas
            if not (0 <= x0 < x1 <= W and 0 <= y0 < y1 <= H):
                c.err(st, f'元素 {eid} rect 越界: {rect}, canvas={canvas}')
        for k in ('t_in', 't_out', 'motion'):
            if k not in e: c.err(st, f'元素 {eid} 缺 {k}')
    if representative:
        difficult=set(c.flags.get('difficult_deferred_keyframes') or [])
        checks={x.get('keyframe'):x for x in d.get('expansion_checks',[]) if isinstance(x,dict)}
        tp=c.data['V0-intake']['text_policy']
        for kf in difficult:
            x=checks.get(kf)
            if not x:
                c.err(st, f'困难扩展镜头 {kf} 缺 expansion_checks 实际成图；代表帧通过不能替代困难镜头适配')
                continue
            if x.get('candidate') != ch: c.err(st, f'{kf}: expansion_check.candidate 必须是 V6 选定方案')
            if not verify_artifact(c, st, x, f'expansion_checks[{kf}]'): continue
            try:
                from PIL import Image
                im=Image.open(c.path(x['file']))
                if list(im.size) != [int(canvas[0]),int(canvas[1])]: c.err(st, f'{kf}: expansion_check 成图尺寸 {list(im.size)} != canvas {canvas}')
            except Exception as ex:
                c.err(st, f'{kf}: expansion_check 无法读取图像尺寸: {ex}')
            if x.get('scale_x_equals_scale_y') is not True: c.err(st, f'{kf}: expansion_check 必须等比缩放')
            qa_elements(c, st, x.get('elements',[]), tp, f'expansion/{kf}')

    cards = dict(c.cards)
    cards.update({x['card_id']:x for x in c.data['V2-reference-selection'].get('new_structure_cards',[])})
    traces=d.get('reference_trace',[])
    if not c.data['V2-reference-selection'].get('selections') and traces:
        c.err(st, 'V2 全部 no_ref_needed 时 V7 reference_trace 必须为空')
    for t in traces:
        card = cards.get(t.get('structure_card'))
        if not card: c.err(st, f"reference_trace 结构卡 {t.get('structure_card')} 不存在"); continue
        if t.get('transfer') not in {x['id'] for x in card['transfer']}: c.err(st, f"reference_trace 迁移项 {t.get('transfer')} 不在结构卡 {card['card_id']} 里")
        if t.get('element') not in ids: c.err(st, f"reference_trace 元素 {t.get('element')} 不存在")
        pp=t.get('parameter_path')
        if not pp: c.err(st, 'reference_trace 缺 parameter_path')
        else:
            try:
                resolve_json_path(d, pp)
            except Exception as e:
                c.err(st, f'reference_trace parameter_path 无法解析: {pp} ({e})')


CHECKS = [V0, V1, V2, V3, V4, V5, V6, V7]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('visual_dir'); ap.add_argument('--package'); ap.add_argument('--case', action='store_true')
    a = ap.parse_args()
    pkg = a.package or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    c = Ctx(os.path.abspath(a.visual_dir), pkg, a.case)
    status, nxt, blocked = {}, None, False
    for st, fn in zip(STAGES, CHECKS):
        if blocked: status[st] = 'NOT_REACHED'; continue
        d = c.load(st)
        if d is None:
            later = [s2 for s2 in STAGES[STAGES.index(st) + 1:] if os.path.exists(os.path.join(c.vdir, s2 + '.json'))]
            if later:
                c.err(st, f'跳步：{", ".join(later)} 已存在，但本步文件缺失。删除后续文件，从本步重新开始')
                status[st] = 'FAIL'; nxt = nxt or f'从 {st} 重新开始'
            else:
                status[st] = 'MISSING'; nxt = nxt or st
            blocked = True; continue
        if '_parse_error' in d: c.err(st, 'JSON 解析失败：' + d['_parse_error'])
        else:
            if d.get('stage') != st.split('-')[0]: c.err(st, f"stage 字段应为 {st.split('-')[0]}")
            check_chain(c, st, d)
            r = fn(c, d)
            if st.startswith('V6') and r in ('pending', 'revise') and not c.errors.get(st):
                status[st] = 'PENDING' if r == 'pending' else 'REVISE'
                nxt = '等待用户在 V6 选定方案（模型必须停在这里）' if r == 'pending' else '回到 V3/V4 按用户意见修改'
                blocked = True; continue
        if c.errors.get(st):
            status[st] = 'FAIL'; nxt = nxt or f'修正 {st}'; blocked = True
        else:
            status[st] = 'PASS'
    for st in STAGES:
        print(f'{st:<24} {status[st]}')
        for e in c.errors.get(st, []): print(f'    ✗ {e}')
        for w in c.warns.get(st, []): print(f'    ! {w}')
    if nxt is None: nxt = '视觉阶段完成：进入 Proof / Execute'
    print(f'NEXT_ALLOWED: {nxt}')
    sys.exit(1 if any(v == 'FAIL' for v in status.values()) else 0)


if __name__ == '__main__':
    main()
