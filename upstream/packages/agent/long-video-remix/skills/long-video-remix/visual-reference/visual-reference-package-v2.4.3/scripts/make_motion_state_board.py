#!/usr/bin/env python3
"""Create a before / enter / hold / exit motion-state board.
Usage: python3 -I scripts/make_motion_state_board.py --before a.png --enter b.png --hold c.png --exit d.png --out board.png
"""
import argparse,hashlib,json
from pathlib import Path
from PIL import Image,ImageDraw

def sha(p):
    h=hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()
def main():
    ap=argparse.ArgumentParser()
    for k in ('before','enter','hold','exit'): ap.add_argument('--'+k,required=True)
    ap.add_argument('--out',required=True); a=ap.parse_args(); files=[a.before,a.enter,a.hold,a.exit]; labels=['BEFORE','ENTER','HOLD','EXIT']
    ims=[]
    for f,l in zip(files,labels):
        im=Image.open(f).convert('RGB'); w=400; im=im.resize((w,round(im.height*w/im.width)),Image.LANCZOS); pad=32; x=Image.new('RGB',(im.width,im.height+pad),'#111'); x.paste(im,(0,pad)); ImageDraw.Draw(x).text((8,8),l,fill='white'); ims.append(x)
    h=max(x.height for x in ims); gap=10; out=Image.new('RGB',(sum(x.width for x in ims)+gap*3,h),'#202020'); xx=0
    for x in ims: out.paste(x,(xx,0)); xx+=x.width+gap
    p=Path(a.out); p.parent.mkdir(parents=True,exist_ok=True); out.save(p); mf=p.with_suffix('.json'); mf.write_text(json.dumps({'states':[{'state':l,'file':f,'sha256':sha(f)} for f,l in zip(files,labels)],'board':{'file':str(p),'sha256':sha(p)}},ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(p); print(mf)
if __name__=='__main__': main()
