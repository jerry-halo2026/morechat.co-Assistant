#!/usr/bin/env python3
"""Measure one locally captured reference frame and (optionally) write the numbers back into a structure card.

The frame itself never enters the package: only its SHA-256, the locator you give, and the measured values are recorded.

Usage:
    python3 -I measure_frame.py <frame.png> <boxes.json> [--card "<结构卡 ID>"] [--locator "<源素材标识与时间码>"]
                                [--manifest <package>/manifests/reference-structure-cards.json]

boxes.json (frame pixel coordinates, [x0, y0, x1, y1]):
    {"text": [...],               # required: box around one text block
     "background": [...],         # optional: background sample; default = 24px ring around the text box
     "subject": [...],            # recommended: nearest face/body/action subject the text must relate to / avoid
     "detail": [...],             # legacy alias for subject
     "relationship_note": "...", # what the text is doing relative to the person/action
     "why_it_works": "..."}       # why this treatment is useful, not just decorative

Outputs (printed as JSON, and appended to card.measured.frames when --card is given):
    text_h_pct_H, text_w_pct_W, text_center_pct, polarity, bg_luma_mean, bg_luma_std,
    contrast_text_vs_bg (WCAG), gap_to_subject_pct_W / vector_to_subject_pct when subject/detail exists.
"""
import sys, json, hashlib, argparse, os
import numpy as np
from PIL import Image


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def rel_lum(rgb):
    c = rgb / 255.0
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def otsu(a):
    hist = np.bincount(a.astype(np.uint8).ravel(), minlength=256).astype(float)
    p = hist / hist.sum(); w = np.cumsum(p); mu = np.cumsum(p * np.arange(256)); mt = mu[-1]
    with np.errstate(divide='ignore', invalid='ignore'):
        sb = (mt * w - mu) ** 2 / (w * (1 - w))
    return int(np.nanargmax(sb))


def measure(frame, boxes):
    im = Image.open(frame).convert('RGB'); W, H = im.size
    rgb = np.asarray(im).astype(float); L = np.asarray(im.convert('L')).astype(float)
    x0, y0, x1, y1 = boxes['text']
    reg = L[y0:y1, x0:x1]
    t = otsu(reg)
    light = reg > t
    if boxes.get('background'):
        bx0, by0, bx1, by1 = boxes['background']; bg_mask = np.zeros((H, W), bool); bg_mask[by0:by1, bx0:bx1] = True
    else:
        r = 24; bg_mask = np.zeros((H, W), bool)
        bg_mask[max(0, y0 - r):min(H, y1 + r), max(0, x0 - r):min(W, x1 + r)] = True
        bg_mask[y0:y1, x0:x1] = False
    bg_med = float(np.median(L[bg_mask]))
    # text = the Otsu class that differs more from the surrounding background (robust when ink covers ~half the box)
    m_light = float(reg[light].mean()) if light.any() else 0.0
    m_dark = float(reg[~light].mean()) if (~light).any() else 255.0
    text_is_light = abs(m_light - bg_med) >= abs(m_dark - bg_med)
    text_mask = light if text_is_light else ~light
    polarity = 'light_text' if text_is_light else 'dark_text'
    rows = np.where(text_mask.sum(1) > max(1, 0.005 * text_mask.shape[1]))[0]
    cols = np.where(text_mask.sum(0) > 0)[0]
    if not len(rows): raise SystemExit('text box contains no separable ink')
    ink_h = int(rows.max() - rows.min() + 1); ink_w = int(cols.max() - cols.min() + 1)
    cx = x0 + (cols.min() + cols.max()) / 2; cy = y0 + (rows.min() + rows.max()) / 2
    bgL = L[bg_mask]
    full_text = np.zeros((H, W), bool); full_text[y0:y1, x0:x1] = text_mask
    lt = float(np.median(rel_lum(rgb[full_text]))); lb = float(np.median(rel_lum(rgb[bg_mask])))
    out = {'frame_size': [W, H], 'polarity': polarity,
           'text_h_pct_H': round(ink_h / H * 100, 2), 'text_w_pct_W': round(ink_w / W * 100, 2),
           'text_center_pct': [round(cx / W * 100, 1), round(cy / H * 100, 1)],
           'bg_luma_mean': round(float(bgL.mean()), 1), 'bg_luma_std': round(float(bgL.std()), 1),
           'contrast_text_vs_bg': round((max(lt, lb) + 0.05) / (min(lt, lb) + 0.05), 2)}
    subj = boxes.get('subject') or boxes.get('detail')
    if subj:
        dx0, dy0, dx1, dy1 = subj
        gx = max(0, dx0 - x1, x0 - dx1); gy = max(0, dy0 - y1, y0 - dy1)
        gap = round(float(np.hypot(gx, gy)) / W * 100, 2)
        out['gap_to_subject_pct_W'] = gap
        out['gap_to_detail_pct_W'] = gap  # backward-compatible name
        tcx,tcy=(x0+x1)/2,(y0+y1)/2; scx,scy=(dx0+dx1)/2,(dy0+dy1)/2
        out['vector_to_subject_pct']=[round((scx-tcx)/W*100,2),round((scy-tcy)/H*100,2)]
    for k in ('relationship_note','why_it_works','action_avoidance_note'):
        if boxes.get(k): out[k]=str(boxes[k]).strip()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('frame'); ap.add_argument('boxes')
    ap.add_argument('--card'); ap.add_argument('--locator', default='')
    ap.add_argument('--manifest', default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                                      'manifests/reference-structure-cards.json'))
    a = ap.parse_args()
    boxes=json.load(open(a.boxes, encoding='utf-8'))
    if a.card:
        missing=[]
        if not (boxes.get('subject') or boxes.get('detail')): missing.append('subject')
        if len(str(boxes.get('relationship_note','')).strip()) < 8: missing.append('relationship_note')
        if len(str(boxes.get('why_it_works','')).strip()) < 8: missing.append('why_it_works')
        if missing: raise SystemExit('same-context measured frame missing: ' + ', '.join(missing))
    m = measure(a.frame, boxes)
    rec = {'frame_sha256': sha(a.frame), 'locator': a.locator or boxes.get('locator',''), **m}
    print(json.dumps(rec, ensure_ascii=False, indent=1))
    if a.card:
        d = json.load(open(a.manifest, encoding='utf-8'))
        card = next((c for c in d['cards'] if c['card_id'] == a.card), None)
        if not card: raise SystemExit(f'card {a.card} not found')
        ms = card.setdefault('measured', {})
        frames = ms.setdefault('frames', [])
        if any(f.get('frame_sha256') == rec['frame_sha256'] for f in frames):
            print('frame already recorded; not appended'); return
        frames.append(rec); ms['status'] = 'measured' if len(frames) >= 2 else 'partial'
        json.dump(d, open(a.manifest, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'written to {a.card}.measured ({len(frames)} frame(s), status={ms["status"]}); re-run scripts/render_structure_cards_md.py')


if __name__ == '__main__':
    main()
