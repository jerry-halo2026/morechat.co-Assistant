#!/usr/bin/env python3
"""Synchronize mechanically duplicated Visual Stage fields into V7 / Implementation Lock.

This script intentionally does not invent semantic execution mappings. It copies fields that are
exactly derivable (chosen candidate, V3 style, V7 byte binding, confirmed mockup bindings, and V7
stage_trace rows). Target execution parameter paths / proof checks still require the actual renderer
implementation and remain explicit in Implementation Lock.
"""
import argparse, importlib.util, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
import visual_pipeline as vp

CHECKER=vp.VISUAL_STAGE_CHECKER
spec=importlib.util.spec_from_file_location('visual_stage_checker',CHECKER); checker=importlib.util.module_from_spec(spec); spec.loader.exec_module(checker)

def write(p,d): p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf-8')
def read(p): return json.loads(p.read_text('utf-8'))

def sync_v7(root,project):
    rel=vp.visual_stage_dir(project)
    if rel is None: raise ValueError('project has no visual_stage_dir')
    d=vp.path_at(root,rel); v3=read(d/'V3-candidates.json'); v6=read(d/'V6-user-decision.json'); p=d/'V7-lock.json'
    if not p.exists(): raise ValueError('V7-lock.json must exist first; create its renderer/elements/timing instead of inventing them')
    v7=read(p); chosen=v6.get('chosen_candidate'); cand=next((x for x in v3.get('candidates',[]) if x.get('id')==chosen),None)
    if not cand: raise ValueError('V6 chosen_candidate is missing from V3')
    v7['chosen_candidate']=chosen; v7['style']=cand.get('style')
    rec={}
    for stage in checker.STAGES[:7]:
        fp=d/(stage+'.json')
        if fp.exists(): rec[stage+'.json']=checker.design_sha_path(fp)
    v7['inputs_design_sha256']=rec; v7.pop('inputs_sha256',None); write(p,v7); print(p)

def sync_lock(root,project):
    design=vp.visual_stage_design(root,project,require_lock=True); ctl=vp.policy(project); p=vp.path_at(root,ctl['implementation_lock_ref']); lock=read(p)
    v7_art=design['report']['artifacts']['V7-lock']; lock['visual_stage_binding']={'v7_ref':v7_art['ref'],'v7_sha256':v7_art['sha256'],'chosen_candidate':design['chosen_candidate']}
    lock['confirmed_mockups']=vp.confirmed_visual_artifacts(root,project)
    lock['selected_mockup_ref']=project.get('visual_mockup_ref')
    lock['selected_mockup_sha256']=vp.binding(root,project['visual_mockup_ref'])['sha256']
    existing=lock.get('reference_trace') if isinstance(lock.get('reference_trace'),list) else []
    by_stage={}
    for row in existing:
        st=row.get('stage_trace') if isinstance(row,dict) else None
        if isinstance(st,dict): by_stage[(st.get('structure_card'),st.get('transfer'),st.get('element'),st.get('parameter_path'))]=row
    migrations={(m['structure_card'],m['transfer']):m for m in design.get('chosen_migrations',[])}
    for st in design['v7'].get('reference_trace',[]):
        key=(st.get('structure_card'),st.get('transfer'),st.get('element'),st.get('parameter_path'))
        if key in by_stage: continue
        mig=migrations.get((st.get('structure_card'),st.get('transfer'))) or {}
        eid=st.get('element'); target=[eid] if eid in (lock.get('elements') or {}) else []
        existing.append({'method_id':None,'ref_id':mig.get('ref_id'),'stage_trace':st,'target_element_ids':target,'parameter_paths':[],'proof_checks':[],'do_not_copy_checks':[]})
    lock['reference_trace']=existing
    from workflow_control import sync_confirmed_visual_bindings
    if not sync_confirmed_visual_bindings(root,project,lock): write(p,lock)
    print(p)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('project_directory',type=Path); ap.add_argument('--target',choices=('v7','implementation-lock','all'),default='all'); a=ap.parse_args(); root=a.project_directory.resolve(); project=read(root/'project.json')
    if a.target in ('v7','all'): sync_v7(root,project)
    if a.target in ('implementation-lock','all'): sync_lock(root,project)
if __name__=='__main__':
    try: main()
    except (ValueError,KeyError,OSError,json.JSONDecodeError) as e: print('BLOCKED:',e); raise SystemExit(1)
