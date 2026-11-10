#!/usr/bin/env python3
"""Prepare V5 review evidence after V4.

Default: art-direction brief + small-screen board + mechanical audit.
Use --blur when blur/squint inspection answers a real layout/readability question.
Use --blind only when a genuinely blind/independent review will be performed. A project with
independent_review=required automatically enables --blind, but still does not force --blur.
"""
import argparse, subprocess, sys, json
from pathlib import Path
HERE=Path(__file__).resolve().parent

def run(args):
    r=subprocess.run([sys.executable,'-I',*map(str,args)])
    if r.returncode: raise SystemExit(r.returncode)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('visual_dir'); ap.add_argument('--case',action='store_true'); ap.add_argument('--seed',type=int); ap.add_argument('--blur',action='store_true'); ap.add_argument('--blind',action='store_true'); a=ap.parse_args()
    d=Path(a.visual_dir).resolve(); need=['V0-intake.json','V1-visual-problems.json','V2-reference-selection.json','V3-candidates.json','V4-mockups.json']
    miss=[x for x in need if not (d/x).exists()]
    if miss: raise SystemExit('missing: '+', '.join(miss))
    v0=json.loads((d/'V0-intake.json').read_text('utf-8')); policy=(v0.get('design_review_policy') or {}).get('independent_review','optional')
    blind=a.blind or policy=='required'
    run([HERE/'art_direction_brief.py',d])
    cmd=[HERE/'make_review_board.py',d]
    if a.seed is not None: cmd += ['--seed',str(a.seed)]
    if a.case: cmd.append('--case')
    if a.blur: cmd.append('--blur')
    if blind: cmd.append('--blind')
    run(cmd)
    cmd=[HERE/'design_quality_audit.py',d]
    if a.case: cmd.append('--case')
    run(cmd)
    generated=['art-direction-brief.json','small-screen-board.png','design-quality-audit.json']
    if a.blur: generated.append('blur-squint-board.png')
    if blind: generated += ['blind-map.json','independent-review-template.json']
    bullets='\n'.join('- `'+x+'`' for x in generated)
    msg=f"""# V5 review evidence ready

Generated evidence:
{bullets}

Independent review policy: **{policy}**.

- Small-screen review is always generated.
- Blur/squint is **problem-driven**; only declare `review_scope.blur_squint.status=used` when `--blur` was intentionally used. Otherwise record `not_needed` + reason.
- Blind-map is generated only for a real blind/independent review (`--blind` or policy=`required`). Do not create blind evidence just to satisfy a template.
- `optional` (default): if no genuinely separate reviewer is available, set `independent_review.status=not_used` with a reason.
- `required`: complete the blind review and run `finalize_independent_review.py`.
- `disabled`: skip independent review.

V5 PASS means the evidence chain is mechanically complete. It does not mean an automated system certified aesthetic quality.
"""
    nxt=d/'review/REVIEW_NEXT.md'; nxt.write_text(msg,encoding='utf-8'); print(nxt)
if __name__=='__main__': main()
