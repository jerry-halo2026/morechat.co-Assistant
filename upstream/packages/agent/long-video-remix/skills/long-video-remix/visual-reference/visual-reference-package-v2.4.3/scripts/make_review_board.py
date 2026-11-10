#!/usr/bin/env python3
"""Generate visual-review boards from V4 mockups.

Default output is the always-useful small-screen board. Use --blur only when blur/squint
inspection addresses a real problem. Use --blind only when a genuinely blind/independent
review will be run; only then is alias mapping/blind-map produced.
"""
import argparse, json, hashlib, math, random, secrets
from pathlib import Path
from PIL import Image, ImageFilter, ImageDraw

ALGO='python_random_shuffle_aliases_v1'
NON_DESIGN_KEYS={'inputs_sha256','inputs_design_sha256','_说明','note','notes','comment','comments','record_note','record_notes','created_at','updated_at'}

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def design_payload(v):
    if isinstance(v,dict): return {k:design_payload(x) for k,x in sorted(v.items()) if k not in NON_DESIGN_KEYS and not k.startswith('_record_')}
    if isinstance(v,list): return [design_payload(x) for x in v]
    return v

def design_sha(p):
    b=json.dumps(design_payload(load(p)),ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
    return hashlib.sha256(b).hexdigest()

def fit(im,w=480):
    h=max(1,round(im.height*w/im.width)); return im.resize((w,h),Image.LANCZOS)

def banner(im,text,bg='#111111',fg='white',height=34):
    out=Image.new('RGB',(im.width,im.height+height),bg); out.paste(im,(0,height))
    ImageDraw.Draw(out).text((10,8),text,fill=fg); return out

def wireframe_stamp(im):
    out=im.copy(); d=ImageDraw.Draw(out); msg='WIREFRAME · NOT FOR AESTHETIC JUDGMENT'
    h=34; d.rectangle((0,0,out.width,h),fill='#7a1717'); d.text((8,8),msg,fill='white'); return out

def sheet(items, cols=2, gap=14, header=None):
    if not items: raise SystemExit('no images')
    cw=max(x.width for x in items); ch=max(x.height for x in items); rows=math.ceil(len(items)/cols); top=42 if header else 0
    out=Image.new('RGB',(cols*cw+(cols-1)*gap,top+rows*ch+(rows-1)*gap),'#202020')
    if header: ImageDraw.Draw(out).text((10,12),header,fill='white')
    for i,x in enumerate(items): out.paste(x,((i%cols)*(cw+gap),top+(i//cols)*(ch+gap)))
    return out

def alias_map(cands, seed):
    labels=[f'X{i+1}' for i in range(len(cands))]; shuffled=labels[:]; random.Random(seed).shuffle(shuffled)
    if len(cands)>1 and shuffled==labels: shuffled=shuffled[1:]+shuffled[:1]
    return {c:a for c,a in zip(cands,shuffled)}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('visual_dir'); ap.add_argument('--out',default='review'); ap.add_argument('--seed',type=int); ap.add_argument('--case',action='store_true'); ap.add_argument('--blur',action='store_true'); ap.add_argument('--blind',action='store_true'); a=ap.parse_args()
    d=Path(a.visual_dir); out=d/a.out; out.mkdir(parents=True,exist_ok=True)
    v4p=d/'V4-mockups.json'; v4=load(v4p); cands=sorted({m['candidate'] for m in v4.get('mockups',[])})
    if not cands: raise SystemExit('V4 has no candidates')
    seed=a.seed if a.seed is not None else secrets.randbits(63)
    aliases=alias_map(cands,seed) if a.blind else {c:c for c in cands}
    small=[]; blur=[]; records=[]; any_wireframe=False
    for m in v4.get('mockups',[]):
        p=d/m['file']; used='mockup'
        if not p.exists() and a.case and m.get('wireframe'):
            p=d/m['wireframe']; used='wireframe'; any_wireframe=True
        if not p.exists(): raise SystemExit(f"missing V4 source: {m.get('file')}")
        actual=sha(p)
        if used=='mockup' and m.get('sha256') and actual!=m.get('sha256'): raise SystemExit(f"V4 source hash mismatch: {m['candidate']}/{m['keyframe']}")
        im=Image.open(p).convert('RGB')
        if used=='wireframe': im=wireframe_stamp(im)
        sm=fit(im,480); label=aliases[m['candidate']]; title=f'{label} · {m["keyframe"]}'
        sfile=out/f'small-{label}-{m["keyframe"]}.png'; sm.save(sfile); small.append(banner(sm,title))
        rec={'alias':label,'candidate':m['candidate'],'keyframe':m['keyframe'],'source':str(p.relative_to(d)),'source_kind':used,'source_sha256':actual,'v4_declared_file':m.get('file'),'v4_declared_sha256':m.get('sha256'),'small_file':str(sfile.relative_to(d)),'small_sha256':sha(sfile)}
        if a.blur:
            tiny=sm.resize((max(32,sm.width//12),max(18,sm.height//12)),Image.BILINEAR)
            bl=tiny.resize(sm.size,Image.BILINEAR).filter(ImageFilter.GaussianBlur(2))
            bfile=out/f'blur-{label}-{m["keyframe"]}.png'; bl.save(bfile); blur.append(banner(bl,title)); rec.update(blur_file=str(bfile.relative_to(d)),blur_sha256=sha(bfile))
        records.append(rec)
    header=('BLIND REVIEW · aliases randomized' if a.blind else 'SMALL-SCREEN REVIEW · candidate labels visible')
    if any_wireframe: header+=' · WIREFRAME SOURCE: NOT FOR AESTHETIC JUDGMENT'
    sb=out/'small-screen-board.png'; sheet(small,header=header).save(sb); print(sb)
    bb=None
    if a.blur:
        bb=out/'blur-squint-board.png'; sheet(blur,header=header).save(bb); print(bb)
    if a.blind:
        bm={'schema_version':'1.2','mapping_algorithm':ALGO,'random_seed':seed,'aliases':aliases,'v4_design_sha256':design_sha(v4p),'synthetic_or_case_wireframe':any_wireframe,'records':records,'small_screen_board':{'file':str(sb.relative_to(d)),'sha256':sha(sb)},'blur_squint_board':({'file':str(bb.relative_to(d)),'sha256':sha(bb)} if bb else None)}
        bmp=out/'blind-map.json'; bmp.write_text(json.dumps(bm,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(bmp)
        score_keys=['first_read','image_integration','typography','narrative_detail','template_risk_inverse','overall']
        tmpl={'schema_version':'1.2','source_blind_map_sha256':sha(bmp),'small_screen_board_sha256':sha(sb),'blur_squint_board_sha256':sha(bb) if bb else None,'reviewer':{'id':'','type':'','origin':'','independence_declared':False},'instructions':'只看盲化 board / mockup，不看候选原名和 V5 推荐。independence_declared 只是评审人声明，代码无法证明。每项 1-5 分。','required_score_keys':score_keys,'results':[{'alias':aliases[c],'scores':{k:0 for k in score_keys},'finding':''} for c in cands],'top_alias':'','reason':''}
        tp=out/'independent-review-template.json'; tp.write_text(json.dumps(tmpl,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(tp); print(f'random_seed={seed}')
if __name__=='__main__': main()
