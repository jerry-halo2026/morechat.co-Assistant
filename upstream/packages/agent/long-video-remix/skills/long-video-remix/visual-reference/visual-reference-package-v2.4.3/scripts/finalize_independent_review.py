#!/usr/bin/env python3
"""Validate and bind a blind-review response to the exact current blind map and boards."""
import argparse, json, hashlib
from pathlib import Path
REQ=['first_read','image_integration','typography','narrative_detail','template_risk_inverse','overall']

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('visual_dir'); ap.add_argument('response'); ap.add_argument('--out',default='review/independent-review.json'); a=ap.parse_args()
    d=Path(a.visual_dir); bmp=d/'review/blind-map.json'
    if not bmp.exists(): raise SystemExit('blind-map missing: generate it only when a real blind review is intended')
    bm=json.loads(bmp.read_text('utf-8')); r=json.loads(Path(a.response).read_text('utf-8'))
    if r.get('source_blind_map_sha256')!=sha(bmp): raise SystemExit('response is bound to a different blind-map')
    sb=bm.get('small_screen_board') or {}; sf=d/sb.get('file','')
    if not sf.exists() or sha(sf)!=sb.get('sha256'): raise SystemExit('current small_screen_board does not match blind-map')
    if r.get('small_screen_board_sha256')!=sb.get('sha256'): raise SystemExit('small-screen board hash mismatch')
    bb=bm.get('blur_squint_board')
    if bb:
        bf=d/bb.get('file','')
        if not bf.exists() or sha(bf)!=bb.get('sha256'): raise SystemExit('current blur_squint_board does not match blind-map')
        if r.get('blur_squint_board_sha256')!=bb.get('sha256'): raise SystemExit('blur/squint board hash mismatch')
    elif r.get('blur_squint_board_sha256') not in (None,''):
        raise SystemExit('blind-map has no blur/squint board; response must not bind one')
    reviewer=r.get('reviewer') or {}
    for k in ('id','type','origin'):
        if not str(reviewer.get(k,'')).strip(): raise SystemExit(f'reviewer.{k} is required')
    if not isinstance(reviewer.get('independence_declared'),bool): raise SystemExit('reviewer.independence_declared must be boolean')
    rev={v:k for k,v in bm['aliases'].items()}; need=set(rev); got={x.get('alias') for x in r.get('results',[])}
    if got!=need: raise SystemExit(f'aliases incomplete: {got} != {need}')
    results=[]
    for x in r['results']:
        if len(x.get('finding','').strip())<20: raise SystemExit(f'{x.get("alias")}: finding too short')
        scores=x.get('scores') or {}
        if set(scores)!=set(REQ): raise SystemExit(f'{x.get("alias")}: scores must contain exactly {REQ}')
        for k in REQ:
            v=scores[k]
            if not isinstance(v,(int,float)) or not 1<=v<=5: raise SystemExit(f'{x.get("alias")}.{k}: score must be 1..5')
        results.append({'candidate':rev[x['alias']],'alias':x['alias'],'scores':scores,'finding':x['finding']})
    if r.get('top_alias') not in rev: raise SystemExit('invalid top_alias')
    if len(r.get('reason','').strip())<20: raise SystemExit('reason too short')
    out={'schema_version':'1.2','source_blind_map_sha256':sha(bmp),'small_screen_board_sha256':sb['sha256'],'blur_squint_board_sha256':bb['sha256'] if bb else None,'reviewer':reviewer,'review_status':'independent_declared' if reviewer['independence_declared'] else 'advisory_non_independent','results':results,'top_candidate':rev[r['top_alias']],'reason':r['reason']}
    op=d/a.out; op.parent.mkdir(parents=True,exist_ok=True); op.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(op); print(sha(op))
    if not reviewer['independence_declared']: print('WARNING: reviewer did not declare independence; this review is advisory only')
if __name__=='__main__': main()
