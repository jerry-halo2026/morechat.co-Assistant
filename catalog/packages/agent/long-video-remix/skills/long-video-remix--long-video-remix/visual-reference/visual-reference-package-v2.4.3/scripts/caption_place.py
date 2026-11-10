#!/usr/bin/env python3
"""IR-12 · Caption Slot & Adaptive Protection — project-agnostic placement + QA tool.

The tool has NO built-in look. Fonts, sizes, ink colours, protection colour and
slot grid all come from the project's chosen visual scheme (`style` in the cue
sheet). The tool only decides, per text moment: which slot, light or dark ink
(if the scheme defines both), how much edge protection, anchor snap — and then
measures glyph height, contrast and clearance on the rendered result.

Usage:
    python3 -I caption_place.py cue-sheet.json out_dir

Cue sheet schema: caption-place/1.0 (see templates/caption-placement.json). Same input -> same pixels.
"""
import sys, os, json, hashlib, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

W, H = 1920, 1080
BASE_DIR = '.'
OPEN = '「『《（“'
CLOSE = '」』》）”'
MID_HALF = '，、；：'
TRAIL = '，。、；：！？」』》）”'
DEFAULT_POLICY = {'glyph_floor_px': 59.4, 'contrast_median_min': 4.5, 'contrast_worst_min': 3.0,
                  'clearance_px': 24, 'safe_margin': [96, 54]}
DEFAULT_GRID = {'mx': 96, 'top': 84, 'bottom': 888, 'upper_max': 560, 'lower_min': 400, 'v_top': 120, 'v_col_gap': 40}


def hex2rgb(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rel_lum(rgb):
    c = np.asarray(rgb, dtype=float) / 255.0
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def contrast(a, b):
    hi, lo = max(a, b), min(a, b); return (hi + 0.05) / (lo + 0.05)


class Scheme:
    """The project's chosen visual scheme, as passed in the cue sheet."""
    def __init__(self, style, policy):
        self.s = style; self.p = {**DEFAULT_POLICY, **(policy or {})}
        self.grid = {**DEFAULT_GRID, **style.get('grid', {})}
        self.font_dir = os.environ.get('CAPTION_FONT_DIR', style.get('font_dir', '/usr/share/fonts/opentype/noto/'))
        self._fc = {}
        self.polarities = [p for p in ('dark', 'light') if p in style['ink']]

    def role(self, r):
        return self.s['roles'][r]

    def font(self, fkey, size):
        k = (fkey, size)
        if k not in self._fc:
            f = self.s['fonts'][fkey]
            path = f['file'] if os.path.isabs(f['file']) else os.path.join(self.font_dir, f['file'])
            self._fc[k] = ImageFont.truetype(path, size, index=f.get('index', 0))
        return self._fc[k]

    def ink(self, polarity, role):
        return hex2rgb(self.s['ink'][polarity][self.role(role)['ink']])

    @property
    def prot_color(self): return hex2rgb(self.s.get('protection', {}).get('color', '#0A0908'))

    @property
    def prot_cap(self): return self.s.get('protection', {}).get('cap', 0.6)


# ------------------------------------------------------------------ frame
def build_frame(fr):
    g = fr.get('geometry', {'mode': 'none'})
    sf = fr['source_frame']
    if not os.path.isabs(sf): sf = os.path.join(BASE_DIR, sf)
    src = Image.open(sf).convert('RGB')
    if g['mode'] == 'none':
        canvas = src.resize((W, H), Image.LANCZOS) if src.size != (W, H) else src
        tf = lambda x, y: (x, y)
    elif g['mode'] == 'crop':
        source_size = fr.get('source_geometry', src.size)
        if (not isinstance(source_size, (list, tuple)) or len(source_size) != 2
                or any(type(value) is not int or value <= 0 for value in source_size)):
            raise ValueError('source_geometry must contain positive integer width and height')
        full = src if src.size == tuple(source_size) else src.resize(tuple(source_size), Image.LANCZOS)
        s = g.get('scale', 1.0); cx, cy = g['crop_x'], g.get('crop_y', 0)
        canvas = full.crop((cx, cy, cx + W / s, cy + H / s)).resize((W, H), Image.LANCZOS)
        tf = lambda x, y: ((x - cx) * s, (y - cy) * s)
    else:
        raise ValueError(g['mode'])

    def mr(r):
        a = tf(r[0], r[1]); b = tf(r[2], r[3])
        return [int(round(max(0, a[0]))), int(round(max(0, a[1]))), int(round(min(W, b[0]))), int(round(min(H, b[1])))]
    prot = [{'id': p['id'], 'class': p['class'], 'rect': mr(p['rect_src'])} for p in fr.get('protect', [])]
    prot = [p for p in prot if p['rect'][2] > p['rect'][0] and p['rect'][3] > p['rect'][1]]
    sub = mr(fr['subtitle_band_src']) if fr.get('subtitle_band_src') else None
    anchors = {k: tf(*v) for k, v in fr.get('anchors_src', {}).items()}
    return canvas, prot, sub, anchors


# ------------------------------------------------------------------ layout
def line_layout(sc, text, role):
    r = sc.role(role); size, tr = r['size'], r.get('tracking', 0.0)
    f = sc.font(r['font'], size)
    out = []; x = 0.0; n = len(text)
    for i, ch in enumerate(text):
        em = f.getlength(ch)
        if i == 0 and ch in OPEN:
            out.append((ch, -size, em)); continue
        if ch in OPEN:
            out.append((ch, x - size * 0.5, em)); x += size * 0.5 + size * tr; continue
        out.append((ch, x, em))
        x += (size * 0.5 if (ch in MID_HALF + CLOSE and i < n - 1) else em) + size * tr
    body = len(text.rstrip(TRAIL))
    bw = max([gx + em for (ch, gx, em), i in zip(out, range(n)) if i < body] or [0])
    return out, bw, f, size


def block_layout(sc, lines):
    laid = []; y = 0.0; prev = None
    for ln in lines:
        g, bw, f, size = line_layout(sc, ln['text'], ln['role'])
        if prev is not None:
            y += ln['gap'] if ln.get('gap') is not None else prev * 0.36
        laid.append({'glyphs': g, 'body_w': bw, 'font': f, 'size': size, 'y': y, 'role': ln['role'], 'text': ln['text']})
        y += size; prev = size
    return laid, max(l['body_w'] for l in laid), y


def vertical_layout(sc, columns):
    cols = []
    for c in columns:
        r = sc.role(c['role']); size, tr = r['size'], r.get('tracking', 0.0)
        txt = ''.join(ch for ch in c['text'] if ch not in TRAIL + OPEN + ' ')
        cols.append({'text': txt, 'role': c['role'], 'font': sc.font(r['font'], size), 'size': size,
                     'h': len(txt) * size * (1 + tr) - size * tr, 'adv': size * (1 + tr)})
    return cols


def candidate_rect(G, slot, bw, bh, anchor_y=None, lead_off=0.0):
    if slot in ('UL', 'UR'):
        y0 = G['top'] if anchor_y is None else min(max(anchor_y - lead_off, G['top']), G['upper_max'] - bh)
    else:
        y0 = G['bottom'] - bh if anchor_y is None else min(max(anchor_y - lead_off, G['lower_min']), G['bottom'] - bh)
    x0 = G['mx'] if slot in ('UL', 'LL') else W - G['mx'] - bw
    return [int(x0), int(y0), int(x0 + bw), int(y0 + bh)]


def v_rect(G, slot, cols):
    tw = sum(c['size'] for c in cols) + G['v_col_gap'] * (len(cols) - 1)
    x0 = G['mx'] if slot == 'VL' else W - G['mx'] - tw
    return [int(x0), G['v_top'], int(x0 + tw), int(G['v_top'] + max(c['h'] for c in cols))]


def overlap(a, b, pad=0):
    return not (a[2] + pad <= b[0] or b[2] + pad <= a[0] or a[3] + pad <= b[1] or b[3] + pad <= a[1])


def inter_area(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def shade_mask(rect, slot):
    """Protection falls off softly from the text block toward the nearest frame edge (vignette-like, never a box)."""
    if slot == 'FULL':
        return Image.new('L', (W, H), 255)
    x0, y0, x1, y1 = rect
    xe = (-60, x1 + 190) if slot in ('UL', 'LL', 'VL') else (x0 - 190, W + 60)
    ye = (-60, y1 + 150) if slot in ('UL', 'UR') else ((y0 - 150, H + 60) if slot in ('LL', 'LR') else (y0 - 150, y1 + 150))
    m = Image.new('L', (W, H), 0)
    ImageDraw.Draw(m).rounded_rectangle((xe[0], ye[0], xe[1], ye[1]), radius=120, fill=255)
    return m.filter(ImageFilter.GaussianBlur(110))


def apply_shade(img, mask, alpha, color):
    if alpha <= 0: return img
    return Image.composite(Image.new('RGB', img.size, color), img, mask.point(lambda v: int(v * alpha)))


def glyph_masks_block(probe, laid):
    x0, y0, x1, y1 = probe['rect']; right = probe['slot'] in ('UR', 'LR')
    items = []
    for l in laid:
        m = Image.new('L', (W, H), 0); d = ImageDraw.Draw(m)
        bx = (x1 - l['body_w']) if right else x0
        for ch, gx, em in l['glyphs']:
            d.text((bx + gx + em / 2, y0 + l['y'] + l['size'] / 2), ch, font=l['font'], fill=255, anchor='mm')
        items.append((l, m))
    return items


def glyph_masks_vertical(probe, cols, gap):
    x0, y0, x1, y1 = probe['rect']; items = []; xr = x1
    for c in cols:  # reading order: first column is rightmost
        m = Image.new('L', (W, H), 0); d = ImageDraw.Draw(m)
        for i, ch in enumerate(c['text']):
            d.text((xr - c['size'] / 2, y0 + i * c['adv'] + c['size'] / 2), ch, font=c['font'], fill=255, anchor='mm')
        items.append((c, m)); xr -= c['size'] + gap
    return items


def ring(masks):
    r = np.zeros((H, W), bool)
    for m in masks:
        a = np.asarray(m) > 128
        r |= (np.asarray(m.filter(ImageFilter.MaxFilter(9))) > 0) & ~a
    return r


def needed_alpha(sc, img, masks, rect, slot, polarity, weakest_role, cap, min_alpha=0.0):
    ink = float(rel_lum(np.array(sc.ink(polarity, weakest_role))))
    rg = ring(masks)
    rgb = np.asarray(img)[rg].astype(float)
    w = np.asarray(shade_mask(rect, slot))[rg].astype(float) / 255.0
    col = np.array(sc.prot_color, float)
    steps = [0.0] if polarity == 'dark' else np.arange(min_alpha, cap + 1e-6, 0.05)
    for a in steps:
        k = (w * a)[:, None]
        lum = rel_lum(rgb * (1 - k) + col * k)
        med = contrast(ink, float(np.median(lum)))
        worst = contrast(ink, float(np.percentile(lum, 90 if polarity == 'light' else 10)))
        if med >= sc.p['contrast_median_min'] and worst >= sc.p['contrast_worst_min']:
            return float(round(a, 2)), med, worst
    return None, None, None


def detail_std(img, rect):
    x0, y0, x1, y1 = rect
    return float(np.asarray(img.convert('L').crop((max(0, x0), max(0, y0), min(W, x1), min(H, y1)))).astype(float).std())


# ------------------------------------------------------------------ decide
def decide(sc, cue, img, prot, sub, anchors, taken, prev_side):
    G = sc.grid
    is_v = cue['type'] == 'vertical'
    if is_v:
        laid = vertical_layout(sc, cue['columns'])
        roles = [c['role'] for c in cue['columns']]
    else:
        laid, bw, bh = block_layout(sc, cue['lines'])
        roles = [l['role'] for l in cue['lines']]
        lead_i = next((i for i, l in enumerate(cue['lines']) if l.get('lead')), 0)
        lead_off = laid[lead_i]['y'] + laid[lead_i]['size'] / 2
    # weakest ink = the role whose ink is closest to mid-grey under light polarity (checked conservatively per polarity)
    cap = cue.get('protection_cap', sc.prot_cap)
    anchor = anchors.get(cue.get('anchor')) if cue.get('anchor') else None
    allowed = cue.get('slots_allowed') or (['VL', 'VR'] if is_v else ['UL', 'UR', 'LL', 'LR'])
    slots = allowed if cue.get('slot', 'auto') == 'auto' else [cue['slot']]
    cand = []
    for s in slots:
        if is_v:
            cand.append((s, v_rect(G, s, laid), 'default'))
        else:
            cand.append((s, candidate_rect(G, s, bw, bh, None, lead_off), 'default'))
            if anchor:
                r2 = candidate_rect(G, s, bw, bh, anchor[1], lead_off)
                if r2 != cand[-1][1]: cand.append((s, r2, 'anchor_snap'))
    hard = [p for p in prot if p['class'] in ('face', 'hand', 'object')]
    soft = [p for p in prot if p['class'] == 'body']
    mx, my = sc.p['safe_margin']
    log, best = [], None
    for s, rect, pos in cand:
        e = {'slot': s, 'position': pos, 'rect': rect}
        hits = [p['id'] for p in hard if overlap(rect, p['rect'], sc.p['clearance_px'])]
        if sub and not cue.get('ignore_subtitle_band') and overlap(rect, sub, 8): hits.append('subtitle_band')
        hits += [t['cue'] for t in taken if overlap(rect, t['rect'], 32)]
        if rect[0] < mx - 1 or rect[2] > W - mx + 1 or rect[1] < my or rect[3] > H - my:
            hits.append('out_of_safe')
        if hits:
            e['rejected'] = hits; log.append(e); continue
        probe = {'slot': s, 'rect': rect}
        masks = [m for _, m in (glyph_masks_vertical(probe, laid, G['v_col_gap']) if is_v else glyph_masks_block(probe, laid))]
        opts = []
        pols = ['light'] if cue.get('_force_light') and 'light' in sc.polarities else sc.polarities
        for pol in pols:
            worst_role = max(roles, key=lambda r: -abs(float(rel_lum(np.array(sc.ink(pol, r)))) - 0.18))
            a, med, wst = needed_alpha(sc, img, masks, rect, s, pol, worst_role, cap, cue.get('_min_alpha', 0.0) if pol == 'light' else 0.0)
            if a is not None: opts.append((pol, a, med, wst))
        if not opts:
            e['rejected'] = ['contrast_unreachable_at_cap']; log.append(e); continue
        opts.sort(key=lambda o: (o[1] if o[0] == 'light' else -0.01))
        pol, a, med, wst = opts[0]
        det = detail_std(img, rect)
        area = (rect[2] - rect[0]) * (rect[3] - rect[1])
        body = sum(inter_area(rect, p['rect']) for p in soft) / max(area, 1)
        dist = math.hypot((rect[0] + rect[2]) / 2 - anchor[0], (rect[1] + rect[3]) / 2 - anchor[1]) if anchor else 0.0
        side = 'L' if s in ('UL', 'LL', 'VL') else 'R'
        score = 100 - 70 * a - 0.25 * det - 80 * body - 0.06 * dist + (6 if prev_side == side else 0) + (3 if s[0] in 'UV' else 0)
        e.update({'polarity': pol, 'protection_alpha': a, 'est_contrast_median': round(med, 2), 'est_contrast_worst': round(wst, 2),
                  'detail_std': round(det, 1), 'body_overlap': round(body, 3), 'anchor_dist': round(dist), 'score': round(score, 1)})
        log.append(e)
        if best is None or score > best['score']: best = e
    fb = best is None
    if fb:
        s = allowed[0]
        rect = v_rect(G, s, laid) if is_v else candidate_rect(G, s, bw, bh, None, lead_off)
        best = {'slot': s, 'position': 'fallback', 'rect': rect, 'polarity': 'light' if 'light' in sc.polarities else sc.polarities[0],
                'protection_alpha': cap, 'score': None}
    return best, log, fb, laid, is_v


def min_ink_height(item, vertical):
    l, _ = item; hs = []
    chars = l['text'] if vertical else [g[0] for g in l['glyphs']]
    for ch in chars:
        if ch in TRAIL + OPEN + CLOSE + '·：《》 ' or ch.isascii(): continue
        m = Image.new('L', (l['size'] * 2, l['size'] * 2), 0)
        ImageDraw.Draw(m).text((l['size'], l['size']), ch, font=l['font'], fill=255, anchor='mm')
        ys = np.where((np.asarray(m) > 128).any(1))[0]
        if len(ys): hs.append(int(ys[-1] - ys[0] + 1))
    return min(hs) if hs else None


def render_screen(sc, screen, frames, out_dir):
    base, prot, sub, anchors = build_frame(frames[screen['frame']])
    img = base
    if screen.get('dim_full_frame'):
        img = apply_shade(img, shade_mask(None, 'FULL'), screen['dim_full_frame'], sc.prot_color)
    taken, plans, prev = [], [], None
    for cue in screen['cues']:
        best, log, fb, laid, is_v = decide(sc, cue, img, prot, sub, anchors, taken, prev)
        prev = 'L' if best['slot'] in ('UL', 'LL', 'VL') else 'R'
        taken.append({'cue': cue['id'], 'rect': best['rect']})
        plans.append((cue, best, log, fb, laid, is_v))
    for cue, best, log, fb, laid, is_v in plans:
        if best['polarity'] == 'light' and best['protection_alpha'] > 0:
            img = apply_shade(img, shade_mask(best['rect'], best['slot']), best['protection_alpha'], sc.prot_color)
    pre = img.copy(); comp = img.convert('RGBA')
    sh = sc.s.get('shadow')
    qa, decisions = [], []
    for cue, best, log, fb, laid, is_v in plans:
        items = glyph_masks_vertical(best, laid, sc.grid['v_col_gap']) if is_v else glyph_masks_block(best, laid)
        for l, m in items:
            ink = sc.ink(best['polarity'], l['role'])
            if best['polarity'] == 'light' and sh:
                sm = m.filter(ImageFilter.GaussianBlur(sh['blur'])).point(lambda v: int(v * sh['opacity']))
                s_l = Image.new('RGBA', (W, H), (0, 0, 0, 0)); s_l.putalpha(sm); comp = Image.alpha_composite(comp, s_l)
            t_l = Image.new('RGBA', (W, H), ink + (0,)); t_l.putalpha(m); comp = Image.alpha_composite(comp, t_l)
            a = np.asarray(m) > 128
            rg = (np.asarray(m.filter(ImageFilter.MaxFilter(9))) > 0) & ~a
            lum = rel_lum(np.asarray(pre)[rg]); il = float(rel_lum(np.array(ink)))
            wp = np.percentile(lum, 90 if best['polarity'] == 'light' else 10)
            ys, xs = np.where(a); bbox = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
            clear = min([max(p['rect'][0] - bbox[2], bbox[0] - p['rect'][2], p['rect'][1] - bbox[3], bbox[1] - p['rect'][3])
                         for p in prot if p['class'] in ('face', 'hand', 'object')] or [999])
            mh = min_ink_height((l, m), is_v)
            row = {'cue': cue['id'], 'text': l['text'], 'role': l['role'], 'size_px': l['size'], 'min_hanzi_ink_px': mh,
                   'contrast_median': round(contrast(il, float(np.median(lum))), 2), 'contrast_worst': round(contrast(il, float(wp)), 2),
                   'min_clearance_px': int(clear), 'subtitle_overlap': bool(sub and not cue.get('ignore_subtitle_band') and overlap(bbox, sub)), 'bbox': bbox}
            floor_ok = cue.get('floor_exempt') or mh is None or mh >= sc.p['glyph_floor_px']
            row['pass'] = bool(floor_ok and row['contrast_median'] >= sc.p['contrast_median_min'] and row['contrast_worst'] >= sc.p['contrast_worst_min']
                               and clear >= sc.p['clearance_px'] and not row['subtitle_overlap'])
            qa.append(row)
        decisions.append({'cue': cue['id'], 'chosen': {k: best.get(k) for k in ('slot', 'position', 'rect', 'polarity', 'protection_alpha', 'score')},
                          'fallback': fb, 'candidates': log})
    out = comp.convert('RGB'); fn = os.path.join(out_dir, screen['id'] + '.png'); out.save(fn, optimize=True)
    ov = out.copy(); d = ImageDraw.Draw(ov)
    for p in prot: d.rectangle(p['rect'], outline=(255, 80, 80) if p['class'] != 'body' else (255, 170, 170), width=3 if p['class'] != 'body' else 1)
    if sub: d.rectangle(sub, outline=(255, 200, 0), width=3)
    for r in qa: d.rectangle(r['bbox'], outline=(60, 220, 255), width=2)
    ov.resize((960, 540), Image.LANCZOS).save(os.path.join(out_dir, screen['id'] + '_qa.png'))
    return {'screen': screen['id'], 'frame': screen['frame'], 'file': screen['id'] + '.png',
            'sha256': hashlib.sha256(open(fn, 'rb').read()).hexdigest(), 'decisions': decisions, 'qa': qa,
            'all_pass': all(r['pass'] for r in qa) and not any(d['fallback'] for d in decisions)}


def render_checked(sc, screen, frames, out_dir, tries=8):
    """If a rendered cue misses contrast, raise its minimum protection (or force light ink) and re-decide."""
    for _ in range(tries):
        r = render_screen(sc, screen, frames, out_dir)
        bad = {q['cue'] for q in r['qa'] if q['contrast_worst'] < sc.p['contrast_worst_min'] or q['contrast_median'] < sc.p['contrast_median_min']}
        if not bad: return r
        for cue in screen['cues']:
            if cue['id'] in bad:
                ch = next(x for x in r['decisions'] if x['cue'] == cue['id'])['chosen']
                if ch['polarity'] == 'dark': cue['_force_light'] = True
                else: cue['_min_alpha'] = round(min(cue.get('protection_cap', sc.prot_cap), (ch['protection_alpha'] or 0) + 0.1), 2)
    return r


def main():
    global BASE_DIR
    sheet = json.load(open(sys.argv[1], encoding='utf-8')); out = sys.argv[2]
    BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[1])); os.makedirs(out, exist_ok=True)
    sc = Scheme(sheet['style'], sheet.get('policy'))
    rep = {'schema': 'caption-place-report/1.0', 'scheme_id': sheet['style'].get('scheme_id'), 'policy': sc.p, 'screens': []}
    for s in sheet['screens']:
        r = render_checked(sc, s, sheet['frames'], out); rep['screens'].append(r)
        print(f"{r['screen']:<34} {'PASS' if r['all_pass'] else 'CHECK'}  " +
              '; '.join(f"{d['cue']}→{d['chosen']['slot']}/{d['chosen']['polarity']}/α{d['chosen']['protection_alpha']}{' FALLBACK' if d['fallback'] else ''}" for d in r['decisions']))
    json.dump(rep, open(os.path.join(out, 'caption-place-report.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
