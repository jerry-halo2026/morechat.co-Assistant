#!/usr/bin/env python3
"""Measure the editing grammar of a reference clip (or of your own cut): shots, transitions, pacing, grade,
camera motion, music alignment, and the timing / typography of on-screen text.

The clip never enters the package. Outputs are numbers only, plus the clip's SHA-256 so the numbers can be traced.

Usage:
    python3 -I analyze_clip.py structure <clip> --out <dir> [--sections "0-34.6:A,34.6-61.2:B"] [--start S] [--end E] [--no-audio]
    python3 -I analyze_clip.py textcards <clip> --boxes <boxes.json> --out <dir>

structure → <dir>/structure.json + <dir>/structure.md   (--start / --end analyse only that window; times stay in clip time)
    shots (start, duration, camera motion class), transitions (cut / double_cut / glitch_burst / white_flash / black),
    pacing (shots per 10 s window, per-section median shot length), grade (monochrome share, accent colour share),
    music (tempo, cut-to-beat alignment against a random baseline, phase concentration, best periodic grid).

textcards → <dir>/textcards.json
    boxes.json:
    {"cards": [{"id": "N1", "shot": [t0, t1], "side": "left", "face": [x0, y0, x1, y1],
                "lines": {"main": {"box": [x0, y0, x1, y1], "ink": "chroma:blue"},
                          "sub":  {"box": [...], "ink": "chroma:blue"}}}]}
    Boxes are rough search areas in percent of the frame; the tool finds the tight text box inside.
    ink: "chroma:blue" | "hex:#RRGGBB:tol" | "bright:<luma>" | "dark:<luma>"
    For every line: tight box (%W/%H), cap height %H, colour, background mean / spread, WCAG contrast, OKLab lightness gap and chroma,
    appear / full / gone times relative to the shot start (presence of the final glyph mask).

Requires ffmpeg on PATH and numpy, scipy, opencv-python-headless (see visual-reference-requirements.txt).
"""
import argparse, hashlib, json, os, subprocess, sys, tempfile, wave
from collections import Counter

import numpy as np

try:
    import cv2
    from scipy.signal import stft, find_peaks
except ImportError as e:  # optional dependencies: the rest of the package does not need them
    sys.exit(f'analyze_clip.py needs opencv-python-headless and scipy ({e})')


# ---------------------------------------------------------------- helpers
def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def probe(clip):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate',
                        '-show_entries', 'format=duration', '-of', 'json', clip], capture_output=True, text=True)
    j = json.loads(r.stdout); s = j['streams'][0]; n, d = s['r_frame_rate'].split('/')
    return int(s['width']), int(s['height']), float(n) / float(d), float(j['format']['duration'])


def frames(clip, w, h, t0=None, t1=None):
    cmd = ['ffmpeg', '-v', 'error']
    if t0 is not None: cmd += ['-ss', str(t0)]
    if t1 is not None: cmd += ['-to', str(t1)]
    cmd += ['-i', clip, '-vf', f'scale={w}:{h}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = w * h * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        yield np.frombuffer(b, np.uint8).reshape(h, w, 3)
    p.wait()


def runs(mask):
    out, s = [], None
    for i, m in enumerate(list(mask) + [False]):
        if m and s is None: s = i
        if not m and s is not None: out.append((s, i)); s = None
    return out


def rel_lum(rgb):
    c = np.asarray(rgb, float) / 255
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return float(0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2])


def contrast(a, b):
    la, lb = sorted([rel_lum(a), rel_lum(b)], reverse=True)
    return round((la + 0.05) / (lb + 0.05), 2)


def r2(x): return None if x is None else round(float(x), 2)


def oklab(rgb):
    c = np.asarray(rgb, float) / 255; c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    l = 0.4122214708 * c[0] + 0.5363325363 * c[1] + 0.0514459929 * c[2]; m = 0.2119034982 * c[0] + 0.6806995451 * c[1] + 0.1073969566 * c[2]
    s_ = 0.0883024619 * c[0] + 0.2817188376 * c[1] + 0.6299787005 * c[2]; l, m, s_ = np.cbrt(l), np.cbrt(m), np.cbrt(s_)
    return np.array([0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s_, 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s_,
                     0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s_]) * 100


# ---------------------------------------------------------------- structure
def structure(a):
    W, H, fps, dur = probe(a.clip)
    t0 = float(a.start or 0.0); t1 = float(a.end) if a.end else dur; dur = t1 - t0
    T = lambda i: round(t0 + i / fps, 3)
    w = 508; h = int(round(H * w / W / 2) * 2)
    sw, sh = 254, max(2, int(round(H * 254 / W / 2) * 2))
    orb = cv2.ORB_create(1000); bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    dl, ecr, luma, sat_med, blue, warm, mot = [], [], [], [], [], [], []
    prevL = prevE = prevEd = prevG = None
    hues = np.zeros(18)
    for i, f in enumerate(frames(a.clip, w, h, t0 if a.start else None, a.end)):
        g = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY)
        s = cv2.GaussianBlur(cv2.resize(g, (sw, sh), interpolation=cv2.INTER_AREA).astype(np.float32), (5, 5), 0)
        e = (cv2.Canny(s.astype(np.uint8), 40, 120) > 0).astype(np.float32); ed = cv2.dilate(e, np.ones((3, 3)))
        if prevL is None: dl.append(0.0); ecr.append(0.0)
        else:
            dl.append(float(np.abs(s - prevL).mean()))
            sa, sb = prevE.sum() + 1, e.sum() + 1
            ecr.append(float(max((prevE * (1 - ed)).sum() / sa, (e * (1 - prevEd)).sum() / sb)))
        prevL, prevE, prevEd = s, e, ed
        hsv = cv2.cvtColor(f, cv2.COLOR_RGB2HSV)
        luma.append(float(g.mean())); sat_med.append(float(np.median(hsv[..., 1]) / 255))
        r, gg, b = [f[..., k].astype(np.int16) for k in range(3)]
        blue.append(float(((b > r + 30) & (b > 90)).mean())); warm.append(float(((r > b + 30) & (r > 90)).mean()))
        strong = (hsv[..., 1] > 90) & (hsv[..., 2] > 90)
        if strong.any(): hues += np.bincount((hsv[..., 0][strong] // 10).ravel(), minlength=18)[:18]
        if i % 3 == 0:
            rec = None
            if prevG is not None:
                ka, da = orb.detectAndCompute(prevG, None); kb, db = orb.detectAndCompute(g, None)
                if da is not None and db is not None and len(ka) > 20 and len(kb) > 20:
                    m = bf.match(da, db)
                    if len(m) > 15:
                        pa = np.float32([ka[x.queryIdx].pt for x in m]); pb = np.float32([kb[x.trainIdx].pt for x in m])
                        M, inl = cv2.estimateAffinePartial2D(pa, pb, method=cv2.RANSAC, ransacReprojThreshold=2.0)
                        if M is not None and inl.sum() > 12: rec = (float(np.hypot(M[0, 0], M[0, 1])), float(M[0, 2]), float(M[1, 2]))
            mot.append((i, rec)); prevG = g
    n = len(luma); dl, ecr, luma = np.array(dl), np.array(ecr), np.array(luma)
    # cuts: local-adaptive peaks of a combined luma + edge-change score
    score = 0.5 * dl / (np.median(dl) + 1e-6) + 0.5 * ecr / (np.median(ecr) + 1e-6)
    cuts = [i for i in range(1, n - 1) if score[i] >= score[i - 1] and score[i] >= score[i + 1]
            and score[i] > 3.0 * np.median(score[max(1, i - 15):i + 16]) and dl[i] > 6 and ecr[i] > 0.45]
    clusters = []
    for c in cuts:
        if clusters and c - clusters[-1][-1] <= 8: clusters[-1].append(c)
        else: clusters.append([c])
    white, black = runs(luma > 190), runs(luma < 8)
    def overlaps(rr, a0, b0): return any(not (y < a0 or x > b0) for x, y in rr)
    trans = []
    for g_ in clusters:
        a0, b0 = g_[0] - 3, g_[-1] + 4
        k = ('white_flash' if overlaps(white, a0, b0) else 'black' if overlaps(black, a0, b0)
             else 'glitch_burst' if len(g_) >= 3 else 'double_cut' if len(g_) == 2 else 'cut')
        wf = sum(min(y, b0 + 6) - max(x, a0 - 6) for x, y in white if not (y < a0 - 6 or x > b0 + 6))
        trans.append({'t': T(g_[0]), 'span_frames': g_[-1] - g_[0] + 1, 'peaks': len(g_), 'kind': k, 'white_frames': max(0, int(wf))})
    bounds = [0] + [g_[-1] for g_ in clusters] + [n]
    shots = []
    for k in range(len(bounds) - 1):
        s0, s1 = bounds[k], bounds[k + 1]
        if s1 - s0 < 3: continue
        rr = [r for i, r in mot if s0 + 3 <= i < s1 and r is not None]
        sh_ = {'start': T(s0), 'dur': round((s1 - s0) / fps, 3), 'motion': 'untracked'}
        if len(rr) >= 3:
            R = np.array(rr); step = 3 / fps
            z = (np.median(R[:, 0]) - 1) * 100 / step; px = np.median(R[:, 1]) / w * 100 / step; py = np.median(R[:, 2]) / h * 100 / step
            mag = float(np.hypot(px, py))
            kind = ('static' if abs(z) < 0.5 and mag < 1.0 else 'push_in' if z >= 0.5 and abs(z) * 2 >= mag
                    else 'pull_out' if z <= -0.5 and abs(z) * 2 >= mag else 'drift' if mag < 6 else 'fast_move')
            sh_.update(zoom_pct_s=r2(z), pan_pctW_s=r2(px), tilt_pctH_s=r2(py), motion=kind)
        shots.append(sh_)
    d = np.array([s['dur'] for s in shots])
    pacing = {'shots': len(shots), 'median_s': r2(np.median(d)), 'mean_s': r2(d.mean()), 'p10_s': r2(np.percentile(d, 10)), 'p90_s': r2(np.percentile(d, 90)),
              'shots_per_10s': [sum(1 for s in shots if t0 + t <= s['start'] < t0 + t + 10) for t in range(0, int(dur) + 1, 10)]}
    sections = []
    if a.sections:
        for part in a.sections.split(','):
            rng, name = part.split(':'); lo, hi = map(float, rng.split('-'))
            ss = [s for s in shots if lo <= s['start'] < hi]; dd = [s['dur'] for s in ss]
            sections.append({'name': name, 'span': [lo, hi], 'shots': len(ss), 'median_s': r2(np.median(dd)) if dd else None,
                             'shots_per_10s': round(len(ss) / (hi - lo) * 10, 1), 'transitions': dict(Counter(t['kind'] for t in trans if lo <= t['t'] < hi)),
                             'motion': dict(Counter(s['motion'] for s in ss))})
    grade = {'luma_mean': r2(luma.mean()), 'monochrome_frame_share': r2((np.array(sat_med) < 0.05).mean()),
             'blue_accent_frame_share': r2((np.array(blue) > 0.005).mean()), 'warm_accent_frame_share': r2((np.array(warm) > 0.005).mean()),
             'warm_accent_times_s': [round(T(x), 2) for x, _ in runs(np.array(warm) > 0.005)],
             'dominant_hue_deg_of_saturated_px': int(np.argmax(hues) * 20) if hues.sum() else None,
             'white_runs': [[round(T(x), 2), y - x] for x, y in white], 'black_runs': [[round(T(x), 2), y - x] for x, y in black]}
    music = None
    if not a.no_audio: music = audio(a.clip, [t['t'] for t in trans], t0, t1)
    out = {'tool': 'analyze_clip.py structure', 'clip_sha256': sha256(a.clip), 'source': {'width': W, 'height': H, 'fps': round(fps, 3), 'duration_s': round(dur, 2), 'aspect': round(W / H, 3), 'window_s': [round(t0, 3), round(t1, 3)]},
           'pacing': pacing, 'sections': sections, 'transitions_summary': dict(Counter(t['kind'] for t in trans)), 'grade': grade, 'music': music,
           'shots': shots, 'transitions': trans}
    os.makedirs(a.out, exist_ok=True)
    json.dump(out, open(os.path.join(a.out, 'structure.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    md = [f"# Clip structure · {os.path.basename(a.clip)}", '', f"SHA-256 `{out['clip_sha256'][:16]}…` · {W}×{H} · {fps:.2f} fps · {dur:.1f} s", '',
          f"Shots {pacing['shots']} · median {pacing['median_s']} s · mean {pacing['mean_s']} s · p10–p90 {pacing['p10_s']}–{pacing['p90_s']} s", '',
          'Transitions: ' + ', '.join(f'{k} {v}' for k, v in out['transitions_summary'].items()), '',
          f"Grade: monochrome frames {grade['monochrome_frame_share']:.0%} · blue accent frames {grade['blue_accent_frame_share']:.0%} · warm accent frames {grade['warm_accent_frame_share']:.0%}", '']
    if sections:
        md += ['| section | span s | shots | median s | shots/10 s | transitions |', '|---|---|---|---|---|---|']
        md += [f"| {s['name']} | {s['span'][0]}–{s['span'][1]} | {s['shots']} | {s['median_s']} | {s['shots_per_10s']} | {s['transitions']} |" for s in sections]
        md.append('')
    if music:
        md += [f"Music: ≈{music['bpm']} bpm · transitions within ±2 frames of a beat {music['on_beat_2f']} (random baseline {music['random_baseline_2f']}) · "
               f"phase concentration R={music['phase_R']} (p≈{music['phase_p']}) · best periodic grid {music['best_period_s']} s (R={music['best_period_R']}, null p95 {music['null_p95_R']})", '']
    open(os.path.join(a.out, 'structure.md'), 'w', encoding='utf-8').write('\n'.join(md))
    print('\n'.join(md))


def audio(clip, cut_times, t0=0.0, t1=None):
    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, 'a.wav')
        r = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t0)] + (['-to', str(t1)] if t1 else []) + ['-i', clip, '-vn', '-ac', '1', '-ar', '22050', wav], capture_output=True)
        if r.returncode != 0 or not os.path.exists(wav): return None
        wf = wave.open(wav); sr = wf.getframerate(); x = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768
    if len(x) < sr * 4: return None
    hop = 512; _, _, Z = stft(x, fs=sr, nperseg=2048, noverlap=2048 - hop)
    S = np.log1p(np.abs(Z) * 100); flux = np.r_[0, np.maximum(0, np.diff(S, axis=1)).sum(0)]; flux = (flux - flux.mean()) / (flux.std() + 1e-9)
    fr = sr / hop; ac = np.correlate(flux, flux, mode='full')[len(flux) - 1:]; lags = np.arange(len(ac)) / fr
    m = (lags > 60 / 180) & (lags < 1.0); lag = float(lags[m][np.argmax(ac[m])]); period = lag * fr
    N = len(flux); sc = flux.copy(); prev = -np.ones(N, int)
    for i in range(N):  # dynamic-programming beat tracker (Ellis 2007)
        lo, hi = max(0, int(i - 2 * period)), int(i - period / 2)
        if hi <= lo: continue
        cand = np.arange(lo, hi); pen = -100 * np.log((i - cand) / period) ** 2
        j = int(np.argmax(sc[cand] + pen)); sc[i] = flux[i] + sc[cand][j] + pen[j]; prev[i] = cand[j]
    tail = int(2 * period); i = int(np.argmax(sc[-tail:]) + N - tail); beats = []
    while i >= 0: beats.append(i); i = prev[i]
    beats = np.array(beats[::-1]) / fr + t0
    t = np.array(cut_times); dur = len(x) / sr
    near = lambda ts: np.array([np.min(np.abs(beats - v)) for v in ts]) if len(ts) else np.array([])
    rng = np.random.default_rng(0)
    base = [float((near(rng.uniform(t0, t0 + dur, len(t))) <= 2 / 30).mean()) for _ in range(200)]
    R = abs(np.exp(2j * np.pi * (t % lag) / lag).mean()) if len(t) else 0.0
    scan = [(abs(np.exp(2j * np.pi * (t % p) / p).mean()), p) for p in np.arange(0.25, 2.5, 0.002)]
    bR, bp = max(scan)
    null = [max(abs(np.exp(2j * np.pi * (rt % p) / p).mean()) for p in np.arange(0.25, 2.5, 0.01)) for rt in (rng.uniform(0, dur, len(t)) for _ in range(100))]
    return {'bpm': round(60 / lag, 1), 'beat_s': round(lag, 3), 'beats': beats.round(3).tolist(),
            'on_beat_2f': f'{int((near(t) <= 2 / 30).sum())}/{len(t)}', 'random_baseline_2f': f'{np.mean(base) * len(t):.1f}±{np.std(base) * len(t):.1f}',
            'phase_R': round(float(R), 2), 'phase_p': round(float(np.exp(-len(t) * R * R)), 3),
            'best_period_s': round(float(bp), 3), 'best_period_R': round(float(bR), 2), 'null_p95_R': round(float(np.percentile(null, 95)), 2)}


# ---------------------------------------------------------------- textcards
def ink_mask(reg, spec):
    r = reg.astype(np.int16)
    kind, _, arg = spec.partition(':')
    if kind == 'chroma' and arg == 'blue': return (r[..., 2] - r[..., 0] > 45) & (r[..., 2] > 125)
    if kind == 'hex':
        hx, _, tol = arg.partition(':'); c = np.array([int(hx.lstrip('#')[k:k + 2], 16) for k in (0, 2, 4)])
        return np.sqrt(((r - c) ** 2).sum(-1)) < float(tol or 60)
    L = r @ np.array([0.299, 0.587, 0.114])
    if kind == 'bright': return L > float(arg or 200)
    if kind == 'dark': return L < float(arg or 50)
    raise SystemExit(f'unknown ink spec {spec}')


def longest_run(v, frac):
    on = v > frac * (v.max() if v.max() > 0 else 1); best, s = (0, 0), None
    for i, o in enumerate(list(on) + [False]):
        if o and s is None: s = i
        if not o and s is not None:
            if i - s > best[1] - best[0]: best = (s, i)
            s = None
    return best


def textcards(a):
    W, H, fps, dur = probe(a.clip); spec = json.load(open(a.boxes, encoding='utf-8')); out = []
    P = lambda b: (int(b[0] / 100 * W), int(b[1] / 100 * H), int(b[2] / 100 * W), int(b[3] / 100 * H))
    for card in spec['cards']:
        t0, t1 = card['shot']; fr = list(frames(a.clip, W, H, t0, t1)); n = len(fr)
        res = {'id': card['id'], 'shot': [t0, t1], 'shot_dur_s': round(n / fps, 2), 'side': card.get('side'), 'lines': {}}
        hold = fr[int(card.get('hold_at', 0.7) * (n - 1))]
        for name, ln in card['lines'].items():
            x0, y0, x1, y1 = P(ln['box']); g = ink_mask(hold[y0:y1, x0:x1], ln['ink'])
            ra, rb = longest_run(g.sum(1).astype(float), 0.12)
            cols = np.where(g[ra:rb].sum(0) > 0)[0]
            if not len(cols) or rb <= ra: res['lines'][name] = {'error': 'no ink found'}; continue
            gap = max(4, 1.6 * (rb - ra)) if name == card.get('main', 'main') else max(6, 3 * (rb - ra))
            segs = np.split(cols, np.where(np.diff(cols) > gap)[0] + 1); seg = max(segs, key=len)
            bx = [x0 + int(seg[0]), y0 + ra, x0 + int(seg[-1]) + 1, y0 + rb]
            reg = hold[bx[1]:bx[3], bx[0]:bx[2]]; m = ink_mask(reg, ln['ink'])
            col = np.median(reg[m], 0); hgt = bx[3] - bx[1]
            rg = hold[max(0, bx[1] - hgt):bx[3] + hgt, max(0, bx[0] - hgt):bx[2] + hgt]
            ring = rg[~ink_mask(rg, ln['ink'])].reshape(-1, 3).astype(float)   # background around the text, ink excluded
            lum = ring @ [0.299, 0.587, 0.114]; bg = np.median(ring, 0)
            ot, ob = oklab(col), oklab(bg)
            pres = np.array([(ink_mask(f[bx[1]:bx[3], bx[0]:bx[2]], ln['ink']) & m).sum() / max(1, m.sum()) for f in fr])
            on, full = np.where(pres > 0.10)[0], np.where(pres > 0.85)[0]
            res['lines'][name] = {'box_pct': [round(bx[0] / W * 100, 1), round(bx[1] / H * 100, 1), round(bx[2] / W * 100, 1), round(bx[3] / H * 100, 1)],
                                  'cap_h_pct_H': round(hgt / H * 100, 2), 'w_pct_W': round((bx[2] - bx[0]) / W * 100, 1),
                                  'center_pct': [round((bx[0] + bx[2]) / 2 / W * 100, 1), round((bx[1] + bx[3]) / 2 / H * 100, 1)],
                                  'rgb': [int(v) for v in col], 'bg_luma_mean': round(float(lum.mean()), 1), 'bg_luma_std': round(float(lum.std()), 1),
                                  'contrast_text_vs_bg': contrast(col, bg), 'delta_L_oklab': r2(abs(ot[0] - ob[0])),
                                  'chroma_text_oklab': r2(np.hypot(ot[1], ot[2])), 'chroma_bg_oklab': r2(np.hypot(ob[1], ob[2])),
                                  'appear_s': r2(on[0] / fps) if len(on) else None, 'full_s': r2(full[0] / fps) if len(full) else None,
                                  'gone_s': r2((on[-1] + 1) / fps) if len(on) else None,
                                  'ends_with_shot': bool(len(on) and on[-1] >= n - 2)}
        L = res['lines']; mn, sb = L.get(card.get('main', 'main')), L.get(card.get('sub', 'sub'))
        if mn and sb and 'error' not in mn and 'error' not in sb:
            res['ratio_main_sub'] = round(mn['cap_h_pct_H'] / sb['cap_h_pct_H'], 2)
            res['gap_lines_pct_H'] = round(sb['box_pct'][1] - mn['box_pct'][3], 2)
            res['sub_lag_s'] = r2(sb['appear_s'] - mn['appear_s']) if None not in (sb['appear_s'], mn['appear_s']) else None
            if card.get('face') and card.get('side') in ('left', 'right'):
                fx0, _, fx1, _ = card['face']; tx0 = min(mn['box_pct'][0], sb['box_pct'][0]); tx1 = max(mn['box_pct'][2], sb['box_pct'][2])
                res['gap_to_face_pct_W'] = round(fx0 - tx1 if card['side'] == 'left' else tx0 - fx1, 1)
                res['edge_margin_pct_W'] = round(tx0 if card['side'] == 'left' else 100 - tx1, 1)
        out.append(res)
        print(card['id'], json.dumps({k: v for k, v in res.items() if k != 'lines'}, ensure_ascii=False))
        for k, v in L.items(): print('   ', k, json.dumps({x: v.get(x) for x in ('cap_h_pct_H', 'w_pct_W', 'center_pct', 'rgb', 'contrast_text_vs_bg', 'bg_luma_mean', 'bg_luma_std', 'appear_s', 'full_s', 'gone_s')}, ensure_ascii=False))
    os.makedirs(a.out, exist_ok=True)
    json.dump({'tool': 'analyze_clip.py textcards', 'clip_sha256': sha256(a.clip), 'source': {'width': W, 'height': H, 'fps': round(fps, 3)}, 'cards': out},
              open(os.path.join(a.out, 'textcards.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('structure'); s.add_argument('clip'); s.add_argument('--out', required=True); s.add_argument('--sections'); s.add_argument('--start', type=float); s.add_argument('--end', type=float); s.add_argument('--no-audio', action='store_true')
    t = sp.add_parser('textcards'); t.add_argument('clip'); t.add_argument('--boxes', required=True); t.add_argument('--out', required=True)
    a = ap.parse_args()
    structure(a) if a.cmd == 'structure' else textcards(a)


if __name__ == '__main__':
    main()
