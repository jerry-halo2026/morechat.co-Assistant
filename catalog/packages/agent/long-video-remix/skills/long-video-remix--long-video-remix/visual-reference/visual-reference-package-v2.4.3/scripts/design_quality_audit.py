#!/usr/bin/env python3
"""Mechanical design-quality evidence audit.

It does NOT score beauty. Small-screen glyph height is reported as projected pixels at the
configured review width. It is only pass/fail when text_policy.small_screen_min_px is
explicitly configured; otherwise no threshold is invented.
"""
import argparse,json
from pathlib import Path
from PIL import Image

def load(p): return json.loads(Path(p).read_text('utf-8'))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('visual_dir'); ap.add_argument('--out',default='review/design-quality-audit.json'); ap.add_argument('--case',action='store_true'); a=ap.parse_args()
    d=Path(a.visual_dir); v0=load(d/'V0-intake.json'); v1=load(d/'V1-visual-problems.json'); v3=load(d/'V3-candidates.json'); v4=load(d/'V4-mockups.json')
    review_width=((v0.get('design_review_policy') or {}).get('small_screen_width_px') or 480)
    configured_min=v0.get('text_policy',{}).get('small_screen_min_px')
    shot_sets={}
    for s in v1.get('shots',[]):
        k=s['keyframe']; shot_sets[k]={'zones':{f"{k}.{z['id']}" for z in s.get('zones',[])},'anchors':set(),'semantic':set()}
        if s.get('narrative_anchor'): shot_sets[k]['anchors'].add(f"{k}.{s['narrative_anchor']['id']}")
        shot_sets[k]['semantic']|={f"{k}.{x['id']}" for x in s.get('protect',[]) if x.get('class') in ('hand','object','face','body')}
    bycand={}
    for m in v4.get('mockups',[]): bycand.setdefault(m['candidate'],[]).append(m)
    report={'schema_version':'1.1','note':'机械审计不判断高级感；small-screen 数值只做投影，除非项目显式配置 small_screen_min_px。','small_screen_width_px':review_width,'configured_small_screen_min_px':configured_min,'candidates':[]}
    for cd in v3.get('candidates',[]):
        cid=cd['id']; warns=[]; metrics=[]; centers=[]
        for ps in cd.get('per_shot',[]):
            dep=set(ps.get('shot_dependency',{}).get('depends_on',[])); ss=shot_sets.get(ps['keyframe'],{})
            semantic=dep & (ss.get('anchors',set())|ss.get('semantic',set()))
            if not semantic: warns.append(f"{ps['keyframe']}: shot_dependency 只依赖区域/通用结构，没有依赖动作、人物或叙事锚点")
        for m in bycand.get(cid,[]):
            fp=d/m['file']
            if not fp.exists() and a.case and m.get('wireframe'): fp=d/m['wireframe']
            if not fp.exists(): continue
            im=Image.open(fp); w,h=im.size; sf=review_width/w
            for e in m.get('elements',[]):
                glyph=e.get('min_hanzi_ink_px',0)*sf
                rec={'keyframe':m['keyframe'],'element':e['id'],'projected_glyph_px':round(glyph,2)}
                if isinstance(configured_min,(int,float)):
                    rec['configured_min_px']=configured_min; rec['meets_configured_min']=glyph+1e-6>=configured_min
                    if not rec['meets_configured_min']: warns.append(f"{m['keyframe']}/{e['id']}: small-screen projected glyph {glyph:.1f}px < configured {configured_min}px")
                else:
                    rec['threshold_status']='not_configured'
                metrics.append(rec)
                b=e.get('bbox')
                if b and len(b)==4: centers.append((m['keyframe'],((b[0]+b[2])/2/w,(b[1]+b[3])/2/h)))
        if len(centers)>=2:
            vals=[]
            for i in range(len(centers)):
                for j in range(i+1,len(centers)):
                    if centers[i][0]==centers[j][0]: continue
                    vals.append(abs(centers[i][1][0]-centers[j][1][0])+abs(centers[i][1][1]-centers[j][1][1]))
            if vals and sum(vals)/len(vals)<0.10: warns.append('跨镜头文字中心高度/位置过于相似：可能是固定模板，需人工确认是否真的依赖镜头')
        report['candidates'].append({'candidate':cid,'small_screen_projection':metrics,'warnings':warns,'mechanical_status':'warn' if warns else 'pass'})
    op=d/a.out; op.parent.mkdir(parents=True,exist_ok=True); op.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(op)
if __name__=='__main__': main()
