#!/usr/bin/env python3
"""Refresh semantic design-chain fingerprints for V1–V7.

Formatting and record-only note changes are ignored by the design fingerprint. By default the
legacy raw-byte chain is removed from rewritten stages; pass --keep-byte-chain when an audit copy
of exact file bytes is also desired.
"""
import argparse, hashlib, json
from pathlib import Path
STAGES=['V0-intake','V1-visual-problems','V2-reference-selection','V3-candidates','V4-mockups','V5-design-review','V6-user-decision','V7-lock']
NON_DESIGN_KEYS={'inputs_sha256','inputs_design_sha256','_说明','note','notes','comment','comments','record_note','record_notes','created_at','updated_at'}

def payload(v):
    if isinstance(v,dict): return {k:payload(x) for k,x in sorted(v.items()) if k not in NON_DESIGN_KEYS and not k.startswith('_record_')}
    if isinstance(v,list): return [payload(x) for x in v]
    return v

def design_sha(p):
    d=json.loads(Path(p).read_text('utf-8'))
    b=json.dumps(payload(d),ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
    return hashlib.sha256(b).hexdigest()

def raw_sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('visual_dir'); ap.add_argument('--keep-byte-chain',action='store_true'); a=ap.parse_args()
    d=Path(a.visual_dir).resolve()
    for i,stage in enumerate(STAGES[1:],1):
        p=d/(stage+'.json')
        if not p.exists(): break
        data=json.loads(p.read_text('utf-8')); design={}; raw={}
        for prev in STAGES[:i]:
            pp=d/(prev+'.json')
            if pp.exists():
                design[prev+'.json']=design_sha(pp)
                if a.keep_byte_chain: raw[prev+'.json']=raw_sha(pp)
        data['inputs_design_sha256']=design
        if a.keep_byte_chain: data['inputs_sha256']=raw
        else: data.pop('inputs_sha256',None)
        p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf-8')
        print(f'{stage}: {len(design)} design fingerprints')
if __name__=='__main__': main()
