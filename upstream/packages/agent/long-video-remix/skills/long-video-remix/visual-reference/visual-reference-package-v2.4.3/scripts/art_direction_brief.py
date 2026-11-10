#!/usr/bin/env python3
"""Build a compact, evidence-only art-direction brief from V0/V1/V2.
Usage: python3 -I scripts/art_direction_brief.py <visual_dir> [--out review/art-direction-brief.json]
Does not invent design. It only packages copy, shot evidence, selected transfers and do-not-copy constraints.
"""
import argparse, json, os, hashlib
from pathlib import Path

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('visual_dir'); ap.add_argument('--out',default='review/art-direction-brief.json'); a=ap.parse_args()
    d=Path(a.visual_dir); v0=load(d/'V0-intake.json'); v1=load(d/'V1-visual-problems.json'); v2=load(d/'V2-reference-selection.json')
    sel={}
    for x in v2.get('selections',[]): sel.setdefault(x['problem'],[]).append({k:x.get(k) for k in ('ref_id','structure_card','transfer','do_not_transfer','conditions','note')})
    scope=(v0.get('design_scope') or {}).get('mode','explore_new')
    count='2-3' if scope=='explore_new' else '1-3'
    rule=('先说明设计怎样参与叙事，再定字体/颜色/位置；新风格探索的候选之间必须有实质结构差异。'
          if scope=='explore_new' else '先说明设计怎样参与叙事，再定字体/颜色/位置；明确复用/简单文字处理不为凑数制造候选。')
    out={'schema_version':'1.1','project_id':v0.get('project_id'),'copy_status':v0['confirmed_from_d2'].get('copy_status'),
         'copy_lines':v0['confirmed_from_d2'].get('copy_lines',[]),'direction_hypothesis':v1.get('direction_hypothesis'),'direction_context':v2.get('direction_context'),'shots':[],'candidate_requirements':{
         'design_scope':scope,'count':count,'must_include':['direction_read','direction_strategy','per_shot.direction_use','art_direction_thesis','composition_grammar','shot_dependency','failure_condition'],
         'rule':rule,
         'direction_knowledge':{
           'atlas':'references/visual-direction-atlas.md',
           'scene_text_grammar':'references/scene-text-grammar.md',
           'timing_grammar':'references/timing-grammar.md',
           'instruction':'V1 先基于内容/关系/画面事实形成 direction_hypothesis，V2 再用参考校准；V3 才深化 direction_read。每个 candidate 与 per_shot 都可承接不同观看逻辑。Atlas 是知识资产，不新增用户审批或 Gate。'
         }}}
    for s in v1.get('shots',[]):
        k=s['keyframe']; probs=[]
        for p in s.get('problems',[]):
            pid=f"{k}.{p['id']}"; probs.append({'id':pid,'statement':p.get('statement') or p.get('problem'),'evidence':p.get('evidence',[]),'references':sel.get(pid,[])})
        out['shots'].append({'keyframe':k,'geometry':s.get('geometry'),'protect':s.get('protect',[]),'zones':s.get('zones',[]),
                             'narrative_anchor':s.get('narrative_anchor'),'problems':probs})
    op=d/a.out; op.parent.mkdir(parents=True,exist_ok=True); op.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(op)
if __name__=='__main__': main()
