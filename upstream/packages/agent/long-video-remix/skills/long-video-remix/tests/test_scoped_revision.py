"""Explicit local changes can evolve content without unlocking implementation grammar."""
import copy
import importlib.util
import json
import shutil
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock
import test_method_adaptation as fixtures
import visual_pipeline as vp
import workflow_control as wc
from compile_render_manifest import compile_manifest


@unittest.skipUnless(importlib.util.find_spec('PIL'), 'Synthetic fixture requires Pillow')
class ScopedRevisionTests(unittest.TestCase):
    project = fixtures.MethodAdaptationTests.project
    independent_second_job = fixtures.MethodAdaptationTests.independent_second_job

    def setUp(self):
        fixtures.MethodAdaptationTests.setUp(self)
        (self.root/'decisions.md').write_text('## 计划确认\n'+self.quote+'\n', encoding='utf-8')
        plan=self.root/'execution-plan.md'
        plan.write_text(plan.read_text()+'\n## 最终素材取舍\n<!-- lvr:container plan.segments -->\n### Segment 1\n<!-- lvr:param seg1.duration -->5 s<!-- /lvr:param seg1.duration -->\n<!-- /lvr:container plan.segments -->\n')
        self.approve()
        wc.confirm(self.root, ('plan',), 'synthetic_fixture_user', 'decisions.md#计划确认', self.quote, [])
        self.original_method = copy.deepcopy(self.project()['workflow_control']['confirmations']['method'])

    def approve(self, keys=('direction', 'audio', 'mockup', 'method')):
        shown=[]
        for key in keys:
            shown += [ref for ref in wc.required_shown_refs(self.root, self.project(), key) if ref not in shown]
        return wc.confirm(self.root, keys, 'synthetic_fixture_user', 'decisions.md#计划确认', self.quote, shown)

    def scope(self, artifact, path, op='replace'):
        return {'artifact': artifact, 'path': path, 'op': op}

    def request(self, scope, kind='content', narrative_change=False):
        quote = 'SYNTHETIC REVISION: change only the declared fields; preserve every other implementation choice.'
        text = (self.root/'decisions.md').read_text()
        heading='## 修订指令\n'
        if heading not in text: (self.root/'decisions.md').write_text(text+'\n'+heading+quote+'\n')
        p = self.project()
        if narrative_change:
            n=self.root/p['narrative_direction_ref']; n.write_text(n.read_text()+'\n'+quote+'\n')
        return {'schema_version':'1.0', 'kind':kind, 'base_sha256':p['workflow_control']['method_preservation']['baseline']['sha256'],
            'narrative_sha256':vp.sha(self.root/p['narrative_direction_ref']), 'instruction_ref':'decisions.md#修订指令', 'quote':quote,'scope':scope}

    def edit(self, artifact, path, value):
        p=self.project(); documents=wc._method_documents(self.root,p,[artifact]); wc.method_value(documents,{'artifact':artifact,'path':path},value,True)
        entry=documents[artifact]
        if isinstance(entry['data'],str): (self.root/entry['ref']).write_text(entry['data'])
        else: vp.write(self.root/entry['ref'],entry['data'])

    def close(self, method=False, diff=None, quote=None):
        p=self.project(); state=p['workflow_control']['method_preservation']; r=state['open_revision']
        current=wc.revision_preview(self.root)
        diff=diff or current['diff_sha256']
        approval=quote or 'SYNTHETIC REVIEW: inspected the displayed diff '+current['diff_sha256']+' and approve this revision.'
        if quote == r['quote']:
            ref=r['instruction_ref']
        elif quote == self.quote:
            ref=(p['workflow_control']['confirmations'].get('plan') or p['workflow_control']['confirmations'].get('method'))['confirmation_ref']
        else:
            section='确认-'+r['revision']
            ref='decisions.md#'+section
            target=self.root/'decisions.md';previous=target.read_text()
            marker='## '+section+'\n'
            if marker not in previous:target.write_text(previous+'\n'+marker+approval+'\n')
        return wc.confirm(self.root, ('method','plan') if method else ('plan',), 'synthetic_fixture_user', ref, approval, [], method,
            r['base_sha256'] if method else None, diff)


    def add_clone(self):
        plan=vp.read(self.root/'composition-plan.json'); job=copy.deepcopy(plan['compositions'][0]);job['composition_id']='C02'
        for key in wc.JOB_OUTPUT_KEYS: job[key]=job[key].replace('C01','C02')
        job['proof_covered_by']='C01';job['proof_coverage_reason']='Synthetic identical grammar and join-risk coverage.'
        plan['compositions'].append(job);vp.write(self.root/'composition-plan.json',plan)

    def test_clean_begin_allows_a_new_narrative(self):
        wc.revise(self.root,self.request([self.scope('composition-plan','/compositions/@composition_id=C01/layers/@layer_id=panel-a/asset_ref')],narrative_change=True))
        self.assertTrue(self.project()['workflow_control']['method_preservation']['open_revision'])

    def test_dirty_begin_cannot_backfill_scope(self):
        request=self.request([self.scope('composition-plan','/compositions/@composition_id=C01/frame_count')])
        self.edit('composition-plan','/compositions/@composition_id=C01/frame_count',120)
        with self.assertRaisesRegex(ValueError,'untracked edit.*frame_count'):wc.revise(self.root,request)

    def test_one_open_revision_cannot_be_replaced(self):
        request=self.request([self.scope('composition-plan','/compositions/@composition_id=C01/frame_count')]);wc.revise(self.root,request)
        with self.assertRaisesRegex(ValueError,'in progress'):wc.revise(self.root,request)

    def test_compiler_is_blocked_even_before_first_edit(self):
        wc.revise(self.root,self.request([self.scope('composition-plan','/compositions/@composition_id=C01/frame_count')]))
        with self.assertRaisesRegex(ValueError,'revision is in progress'):compile_manifest(self.root)
        for action in ('render','authorize','qa_start','build_composition'):
            self.assertFalse(wc.report(self.root,action)['action_allowed'])

    def test_scope_cannot_target_whole_composition(self):
        with self.assertRaisesRegex(ValueError,'whole object'):
            wc.revise(self.root,self.request([self.scope('composition-plan','/compositions/@composition_id=C01')]))

    def test_scope_requires_existing_instruction_and_current_parent(self):
        request=self.request([self.scope('composition-plan','/compositions/@composition_id=C01/frame_count')])
        request['quote']='Invented approval'
        with self.assertRaisesRegex(ValueError,'existing instruction'):wc.revise(self.root,request)
        request=self.request(request['scope']);request['base_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'parent/Narrative'):wc.revise(self.root,request)

    def test_asset_substitution_keeps_method_and_stales_affected_composition(self):
        path='/compositions/@composition_id=C01/layers/@layer_id=panel-a/asset_ref'
        wc.revise(self.root,self.request([self.scope('composition-plan',path)]));self.edit('composition-plan',path,'media/b.png')
        diff=wc.revision_preview(self.root);self.assertEqual(diff['affected_compositions'],['C01'])
        result=self.close();self.assertEqual(result['status'],'revision_committed')
        self.assertEqual(self.project()['workflow_control']['confirmations']['method'],self.original_method)
        self.assertEqual(wc.evaluate(self.root)['method']['status'],'satisfied')
        self.assertEqual(wc.evaluate(self.root)['plan']['status'],'satisfied')
        self.assertIsNone(wc.method_guard(self.root,self.project()).get('open_revision'))

    def test_unrelated_field_is_reported_with_exact_id_and_path(self):
        path='/compositions/@composition_id=C01/layers/@layer_id=panel-a/asset_ref'
        wc.revise(self.root,self.request([self.scope('composition-plan',path)]));self.edit('composition-plan',path,'media/b.png')
        self.edit('composition-plan','/compositions/@composition_id=C01/preview_audio_ref','media/a.png')
        diff=wc.revision_preview(self.root);self.assertEqual(diff['status'],'LINEAGE_VIOLATION')
        self.assertTrue(any(r['path'].endswith('/preview_audio_ref') and r['classification']=='out_of_scope' for r in diff['actual_diff']))
        with self.assertRaisesRegex(ValueError,'preview_audio_ref'):self.close()

    def test_diff_confirmation_is_invalidated_by_a_later_edit(self):
        path='/compositions/@composition_id=C01/frame_count'
        wc.revise(self.root,self.request([self.scope('composition-plan',path)]));self.edit('composition-plan',path,120)
        old=wc.revision_preview(self.root)['diff_sha256'];self.edit('composition-plan',path,115)
        with self.assertRaisesRegex(ValueError,'exact displayed'):self.close(diff=old)

    def test_confirmation_cannot_skip_diff_binding(self):
        wc.revise(self.root,self.request([self.scope('composition-plan','/compositions/@composition_id=C01/frame_count')]))
        approval='SYNTHETIC REVIEW: inspected this revision and approve the changes.'
        (self.root/'revision-decisions.md').write_text('## 本轮确认\n'+approval+'\n')
        with self.assertRaisesRegex(ValueError,'diff-sha256'):
            wc.confirm(self.root,('plan',),'synthetic_fixture_user','revision-decisions.md#本轮确认',approval,[])

    def test_instruction_and_narrative_are_frozen_while_open(self):
        wc.revise(self.root,self.request([self.scope('composition-plan','/compositions/@composition_id=C01/frame_count')]))
        (self.root/'decisions.md').write_text((self.root/'decisions.md').read_text()+'Another instruction\n')
        with self.assertRaisesRegex(ValueError,'Narrative/instruction changed'):wc.revision_preview(self.root)

    def test_scope_state_mutation_is_detected(self):
        wc.revise(self.root,self.request([self.scope('composition-plan','/compositions/@composition_id=C01/frame_count')]))
        p=self.project();p['workflow_control']['method_preservation']['open_revision']['scope'][0]['path']='/compositions/@composition_id=C01/mode';vp.write(self.root/'project.json',p)
        with self.assertRaisesRegex(ValueError,'state/parent changed'):wc.revision_preview(self.root)

    def test_content_scope_cannot_change_easing(self):
        path='/compositions/@composition_id=C01/groups/push/keyframes/@key_id=push_end/easing'
        wc.revise(self.root,self.request([self.scope('composition-plan',path)]));self.edit('composition-plan',path,'linear')
        with self.assertRaisesRegex(ValueError,'visual grammar changed'):wc.revision_preview(self.root)

    def test_method_change_requires_prior_scope(self):
        with self.assertRaisesRegex(ValueError,'scoped revise'):
            wc.confirm(self.root,('method',),'synthetic_fixture_user','decisions.md',self.quote,[],True,'0'*64)

    def test_scoped_method_change_closes_with_existing_method_and_plan(self):
        path='/compositions/@composition_id=C01/groups/push/keyframes/@key_id=push_end/easing'
        wc.revise(self.root,self.request([self.scope('composition-plan',path)],'method'));self.edit('composition-plan',path,'linear')
        self.close(method=True)
        self.assertNotEqual(self.original_method['method_contract_digest'],self.project()['workflow_control']['confirmations']['method']['method_contract_digest'])
        self.assertEqual(wc.evaluate(self.root)['method']['status'],'satisfied')

    def test_scoped_method_change_cannot_sweep_unrelated_content(self):
        path='/compositions/@composition_id=C01/groups/push/keyframes/@key_id=push_end/easing'
        wc.revise(self.root,self.request([self.scope('composition-plan',path)],'method'));self.edit('composition-plan',path,'linear')
        self.edit('timeline','/text_tracks/@text_id=TXT001/text','Unrequested copy')
        with self.assertRaisesRegex(ValueError,'out-of-scope'):self.close(method=True)

    def test_scope_cannot_use_array_indices(self):
        with self.assertRaisesRegex(ValueError,'stable @id'):
            wc.revise(self.root,self.request([self.scope('composition-plan','/compositions/0/frame_count')]))

    def test_duplicate_ids_are_rejected(self):
        wc.revise(self.root,self.request([self.scope('composition-plan','/compositions/@composition_id=C02','add')]))
        plan=vp.read(self.root/'composition-plan.json');plan['compositions'].append(copy.deepcopy(plan['compositions'][0]));vp.write(self.root/'composition-plan.json',plan)
        with self.assertRaisesRegex(ValueError,'duplicate stable ID'):wc.revision_preview(self.root)

    def test_add_composition_reuses_approved_grammar(self):
        wc.revise(self.root,self.request([self.scope('composition-plan','/compositions/@composition_id=C02','add')]))
        self.add_clone();self.close();self.assertEqual(wc.evaluate(self.root)['method']['status'],'satisfied')
        self.assertEqual(len(vp.read(self.root/'composition-plan.json')['compositions']),2)

    def test_remove_composition_preserves_the_approved_grammar_catalog(self):
        wc.revise(self.root,self.request([self.scope('composition-plan','/compositions/@composition_id=C02','add')]))
        self.add_clone();self.close()
        wc.revise(self.root,self.request([self.scope('composition-plan','/compositions/@composition_id=C02','remove')]))
        plan=vp.read(self.root/'composition-plan.json');plan['compositions'].pop();vp.write(self.root/'composition-plan.json',plan)
        self.assertEqual(wc.revision_preview(self.root)['removed_compositions'],['C02']);self.close()
        self.assertEqual(self.original_method,self.project()['workflow_control']['confirmations']['method'])

    def test_content_add_cannot_introduce_a_new_layout(self):
        wc.revise(self.root,self.request([self.scope('composition-plan','/compositions/@composition_id=C02','add')]))
        self.add_clone();self.edit('composition-plan','/compositions/@composition_id=C02/layers/@layer_id=panel-a/fit','contain')
        with self.assertRaisesRegex(ValueError,'visual grammar changed'):wc.revision_preview(self.root)

    def test_binding_updates_are_derived_without_permission_to_rewrite_neighbors(self):
        path='/elements/PANEL_PUSH/parameters/scale_end'
        wc.revise(self.root,self.request([self.scope('implementation-lock',path)]));self.edit('implementation-lock',path,1.1)
        diff=wc.revision_preview(self.root)
        self.assertTrue(any(r['classification']=='derived' and r['path'].endswith('/values/scale') for r in diff['actual_diff']))
        self.close();self.assertEqual(vp.read(self.root/'visual-methods.json')['methods'][0]['parameters']['scale_end'],1.1)

    def test_wrong_manual_derived_value_is_rejected(self):
        path='/elements/PANEL_PUSH/parameters/scale_end'
        wc.revise(self.root,self.request([self.scope('implementation-lock',path)]));self.edit('implementation-lock',path,1.1)
        self.edit('visual-methods','/methods/@method_id=PM001/parameters/scale_end',1.09)
        with self.assertRaisesRegex(ValueError,'derived field differs'):wc.revision_preview(self.root)

    def test_original_outputs_are_preserved(self):
        old=self.root/'compositions/C01/v1.blend';old.parent.mkdir(parents=True);old.write_bytes(b'OLD SAVED ENGINEERING')
        path='/compositions/@composition_id=C01/layers/@layer_id=panel-a/asset_ref'
        wc.revise(self.root,self.request([self.scope('composition-plan',path)]));self.edit('composition-plan',path,'media/b.png');self.close()
        self.assertEqual(old.read_bytes(),b'OLD SAVED ENGINEERING')
        self.assertNotEqual(vp.read(self.root/'composition-plan.json')['compositions'][0]['scene_ref'],'compositions/C01/v1.blend')

    def test_clean_cancel_and_dirty_cancel(self):
        request=self.request([self.scope('composition-plan','/compositions/@composition_id=C01/frame_count')]);wc.revise(self.root,request)
        self.assertEqual(wc.revise(self.root,cancel=True)['status'],'cancelled')
        wc.revise(self.root,request);self.edit('composition-plan','/compositions/@composition_id=C01/frame_count',120)
        with self.assertRaisesRegex(ValueError,'restore controlled'):wc.revise(self.root,cancel=True)

    def test_bare_markdown_cannot_be_declared_as_an_editable_section(self):
        with self.assertRaisesRegex(ValueError,'block:id'):wc.revise(self.root,self.request([self.scope('execution-plan','heading:Segment 1')]))

    def test_markup_migration_then_unregistered_copy_change(self):
        original=(self.root/'execution-plan.md').read_text()
        wc.revise(self.root,self.request([self.scope('execution-plan','block:copy','add')],'markup'))
        line=next(line for line in original.splitlines(True) if line.strip() and not line.startswith('#'))
        (self.root/'execution-plan.md').write_text(original.replace(line,'<!-- lvr:param copy -->'+line.rstrip('\n')+'<!-- /lvr:param copy -->\n',1))
        self.close();wc.revise(self.root,self.request([self.scope('execution-plan','block:copy')]))
        self.edit('execution-plan','block:copy','Revised synthetic plan copy.');self.close()
        self.assertIn('Revised synthetic plan copy.',(self.root/'execution-plan.md').read_text())

    def test_markup_cannot_silently_rewrite_text(self):
        wc.revise(self.root,self.request([self.scope('execution-plan','block:copy','add')],'markup'))
        (self.root/'execution-plan.md').write_text('<!-- lvr:param copy -->Different text<!-- /lvr:param copy -->')
        with self.assertRaisesRegex(ValueError,'every original text byte'):wc.revision_preview(self.root)

    def test_shortening_and_coordinates_are_scoped_and_deterministic(self):
        scopes=[self.scope('timeline','/events/@event_id=E001/source_out_ms'),self.scope('composition-plan','/compositions/@composition_id=C01/frame_count'),
            self.scope('composition-plan','/compositions/@composition_id=C01/layers/@layer_id=panel-b/end_frame')]
        wc.revise(self.root,self.request(scopes));self.edit('timeline','/events/@event_id=E001/source_out_ms',5000)
        self.edit('composition-plan','/compositions/@composition_id=C01/frame_count',100);self.edit('composition-plan','/compositions/@composition_id=C01/layers/@layer_id=panel-b/end_frame',100)
        diff=wc.revision_preview(self.root)
        self.assertTrue(any(r['path'].endswith('/out_out_frame') and r['classification']=='derived' for r in diff['actual_diff']))
        self.assertEqual(diff['status'],'blocked')
        self.assertTrue(any('protected meaning' in e for e in diff['validation']['new_errors']))
        for collection in ('audio_tracks','text_tracks'):
            self.assertTrue(any(collection in e and 'outside compiled output' in e for e in diff['validation']['new_errors']))
        baseline=self.project()['workflow_control']['method_preservation']['baseline']
        with self.assertRaisesRegex(ValueError,'introduces validation errors'):self.close()
        self.assertEqual(self.project()['workflow_control']['method_preservation']['baseline'],baseline)

    def test_wrong_coordinate_is_not_accepted_as_a_derived_shift(self):
        wc.revise(self.root,self.request([self.scope('timeline','/events/@event_id=E001/source_out_ms')]))
        self.edit('timeline','/events/@event_id=E001/source_out_ms',5000);self.edit('timeline','/events/@event_id=E001/out_out_frame',111)
        with self.assertRaisesRegex(ValueError,'derived field differs'):wc.revision_preview(self.root)

    def test_interrupted_commit_restores_the_open_revision_without_approval(self):
        path='/compositions/@composition_id=C01/layers/@layer_id=panel-a/asset_ref'
        wc.revise(self.root,self.request([self.scope('composition-plan',path)]));self.edit('composition-plan',path,'media/b.png')
        before=(self.root/'project.json').read_bytes();diff=wc.revision_preview(self.root)['diff_sha256']
        with mock.patch.object(wc,'_method_write_checkpoint',side_effect=OSError('simulated commit interruption')):
            with self.assertRaises(OSError):self.close(diff=diff)
        with self.assertRaisesRegex(ValueError,'interrupted'):wc.method_guard(self.root,self.project())
        self.assertEqual(wc.recover_method_patch(self.root)['result'],'restored_previous_baseline')
        self.assertEqual((self.root/'project.json').read_bytes(),before)
        self.close();self.assertEqual(wc.evaluate(self.root)['plan']['status'],'satisfied')

    def legacy1414(self):
        p=self.project(); baseline=vp.read(self.root/'method-baseline.json');baseline['schema_version']='1.0';baseline.pop('grammar_catalog')
        baseline['method_digest']=wc.legacy_v1414_method_contract_digest(baseline['artifacts'],baseline['context'])
        vp.write(self.root/'method-baseline.json',baseline)
        state=p['workflow_control']['method_preservation'];state['baseline']['sha256']=vp.sha(self.root/'method-baseline.json')
        method=p['workflow_control']['confirmations']['method'];method['method_contract_digest']=baseline['method_digest']
        method['input_digest']=vp.digest({'method_contract':baseline['method_digest'],'sources':vp.binding(self.root,'sources.json')})
        timeline=vp.read(self.root/'timeline.json')
        old_plan={'plan_ref':p['execution_plan_ref'],'plan_without_step0_bookkeeping':wc.strip_step0((self.root/p['execution_plan_ref']).read_text()),
            'planned_selection':[{key:r.get(key) for key in ('event_id','source_id','unit_id','d2_selection_snapshot')} for r in timeline['events'] if r['kind']=='source'],
            'text_tracks':timeline['text_tracks'],'output':p['output']}
        p['workflow_control']['confirmations']['plan']['input_digest']=vp.digest(old_plan)
        p['workflow_control']['schema_version']='1.2';p['execution_policy']['workflow_gate_control']='required_v3';vp.write(self.root/'project.json',p)

    def test_v1414_migration_preserves_artifacts_and_real_decision_provenance(self):
        self.legacy1414();p=self.project();before={r['ref']:(self.root/r['ref']).read_bytes() for r in vp.read(self.root/'method-baseline.json')['artifacts'].values()}
        provenance={key:{field:p['workflow_control']['confirmations'][key][field] for field in ('actor','quote','confirmation_ref')} for key in ('plan','method')}
        wc.initialize(self.root);wc.adopt_confirmed_method(self.root)
        self.assertEqual(self.project()['workflow_control']['schema_version'],'1.3')
        self.assertEqual(wc.evaluate(self.root)['method']['status'],'satisfied');self.assertEqual(wc.evaluate(self.root)['plan']['status'],'satisfied')
        for name,raw in before.items():self.assertEqual((self.root/name).read_bytes(),raw)
        for key,fields in provenance.items():
            for field,value in fields.items():self.assertEqual(self.project()['workflow_control']['confirmations'][key][field],value)

    def test_v1414_migration_rejects_a_changed_timeline(self):
        self.legacy1414();wc.initialize(self.root);self.edit('timeline','/text_tracks/@text_id=TXT001/text','Edited after confirmation')
        with self.assertRaisesRegex(ValueError,'old confirmed artifacts changed'):wc.adopt_confirmed_method(self.root)

    def test_method_revision_cannot_reuse_old_approval(self):
        path='/compositions/@composition_id=C01/groups/push/keyframes/@key_id=push_end/easing'
        wc.revise(self.root,self.request([self.scope('composition-plan',path)],'method'));self.edit('composition-plan',path,'linear')
        with self.assertRaisesRegex(ValueError,'new actual decision|new confirmation section'):self.close(method=True,quote=self.quote)

    def test_added_shared_instance_remains_adaptable_in_the_next_round(self):
        wc.revise(self.root,self.request([self.scope('composition-plan','/compositions/@composition_id=C02','add')]))
        self.add_clone();self.close()
        patch=fixtures.MethodAdaptationTests.patch(self)
        result=wc.adapt_method(self.root,patch)
        self.assertEqual(result['affected_compositions'],['C01','C02'])
        for job in vp.read(self.root/'composition-plan.json')['compositions']:
            self.assertEqual(job['groups']['push']['keyframes'][1]['values']['scale'],1.1)

    def test_content_cannot_change_a_shared_instance_parameter_independently(self):
        wc.revise(self.root,self.request([self.scope('composition-plan','/compositions/@composition_id=C02','add')]))
        self.add_clone();self.edit('composition-plan','/compositions/@composition_id=C02/groups/push/keyframes/@key_id=push_end/values/scale',2)
        with self.assertRaisesRegex(ValueError,'bound parameter differs|shared instance parameter'):wc.revision_preview(self.root)

    def test_interrupted_baseline_rename_cleans_only_its_own_pending_checkpoint(self):
        path='/compositions/@composition_id=C01/layers/@layer_id=panel-a/asset_ref'
        wc.revise(self.root,self.request([self.scope('composition-plan',path)]));self.edit('composition-plan',path,'media/b.png')
        replace=Path.replace
        def interrupted(path,target):
            if path.name=='method-baseline.json.pending':raise OSError('simulated baseline rename interruption')
            return replace(path,target)
        with mock.patch.object(Path,'replace',interrupted):
            with self.assertRaises(OSError):self.close()
        self.assertTrue((self.root/'method-baseline.json.pending').exists())
        wc.recover_method_patch(self.root)
        self.assertFalse((self.root/'method-baseline.json.pending').exists());self.close()
        self.assertEqual(wc.evaluate(self.root)['plan']['status'],'satisfied')

    def test_instruction_and_previous_plan_quotes_cannot_close_content_revision(self):
        wc.revise(self.root,self.request([self.scope('composition-plan','/compositions/@composition_id=C01/frame_count')]))
        instruction=self.project()['workflow_control']['method_preservation']['open_revision']['quote']
        for quote in (instruction,self.quote):
            with self.subTest(quote=quote):
                with self.assertRaisesRegex(ValueError,'new actual decision|new confirmation section|not its instruction'):self.close(quote=quote)
        self.assertTrue(self.project()['workflow_control']['method_preservation']['open_revision'])

    def test_method_revision_also_rejects_its_instruction_quote(self):
        path='/compositions/@composition_id=C01/groups/push/keyframes/@key_id=push_end/easing'
        wc.revise(self.root,self.request([self.scope('composition-plan',path)],'method'));self.edit('composition-plan',path,'linear')
        quote=self.project()['workflow_control']['method_preservation']['open_revision']['quote']
        with self.assertRaisesRegex(ValueError,'not its instruction|new actual decision'):self.close(method=True,quote=quote)

    def test_collection_scope_is_rejected_before_opening(self):
        for artifact,path in [('timeline','/text_tracks'),('timeline','/events'),('composition-plan','/compositions')]:
            with self.subTest(path=path):
                with self.assertRaisesRegex(ValueError,'collection'):wc.revise(self.root,self.request([self.scope(artifact,path)]))
        self.assertNotIn('open_revision',self.project()['workflow_control']['method_preservation'])

    def test_existing_validation_errors_do_not_block_unrelated_content(self):
        path=self.root/'units.jsonl';rows=[json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        rows[0]['end_ms']=900;path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
        field='/compositions/@composition_id=C01/layers/@layer_id=panel-a/asset_ref'
        wc.revise(self.root,self.request([self.scope('composition-plan',field)]));self.edit('composition-plan',field,'media/b.png')
        diff=wc.revision_preview(self.root)
        self.assertTrue(diff['validation']['baseline_errors']);self.assertEqual(diff['validation']['new_errors'],[])
        self.close()

    def test_valid_trim_synchronizes_tracks_and_passes_new_error_check(self):
        locations=[('timeline','/events/@event_id=E001/source_out_ms',5900),('timeline','/audio_tracks/@track_id=A001/source_out_ms',5900),
            ('timeline','/audio_tracks/@track_id=A001/local_out_frame',123),('timeline','/text_tracks/@text_id=TXT001/local_out_frame',123),
            ('timeline','/text_tracks/@text_id=TXT001/stable_hold_frames',123),('composition-plan','/compositions/@composition_id=C01/frame_count',123),
            ('composition-plan','/compositions/@composition_id=C01/layers/@layer_id=panel-b/end_frame',123)]
        wc.revise(self.root,self.request([self.scope(a,p) for a,p,v in locations]))
        for a,p,v in locations:self.edit(a,p,v)
        diff=wc.revision_preview(self.root);self.assertEqual(diff['validation']['new_errors'],[])
        self.close();self.assertEqual(vp.read(self.root/'timeline.json')['events'][0]['out_out_frame'],123)

    def test_segment_scope_can_add_and_remove_exact_identity(self):
        add_scope=self.scope('execution-plan','segment:seg2','add')
        wc.revise(self.root,self.request([add_scope]))
        container={'artifact':'execution-plan','path':'container:plan.segments'}
        text=wc.method_value(wc._method_documents(self.root,self.project(),['execution-plan']),container)
        self.edit('execution-plan','container:plan.segments',text+'\n### Segment 2 · 结尾余味\n<!-- lvr:param seg2.duration -->2 s<!-- /lvr:param seg2.duration -->\n')
        diff=wc.revision_preview(self.root);self.assertEqual(diff['status'],'revision_ready_for_plan_confirmation')
        self.assertTrue(any(r['path']=='segment:seg2' and r['classification']=='in_scope' for r in diff['actual_diff']))
        self.assertTrue(any(r['path']=='block:seg2.duration' and r['classification']=='in_scope' for r in diff['actual_diff']))
        self.close()
        remove_scope=self.scope('execution-plan','segment:seg2','remove');wc.revise(self.root,self.request([remove_scope]))
        text=wc.method_value(wc._method_documents(self.root,self.project(),['execution-plan']),container)
        start=text.index('### Segment 2');self.edit('execution-plan','container:plan.segments',text[:start])
        self.close();self.assertNotIn('### Segment 2',(self.root/'execution-plan.md').read_text())

    def test_segment_scope_does_not_authorize_level_two_headings(self):
        scope=self.scope('execution-plan','segment:seg2','add');wc.revise(self.root,self.request([scope]))
        self.edit('execution-plan','container:plan.segments','\n## Unrequested section\n### Segment 2\n<!-- lvr:param seg2.duration -->2 s<!-- /lvr:param seg2.duration -->\n')
        with self.assertRaisesRegex(ValueError,'level 1/2'):wc.revision_preview(self.root)

    def test_leaf_scope_cannot_change_neighbor_inside_container(self):
        scope=self.scope('execution-plan','block:seg1.duration');wc.revise(self.root,self.request([scope]))
        text=(self.root/'execution-plan.md').read_text().replace('### Segment 1','### Renamed segment')
        (self.root/'execution-plan.md').write_text(text)
        with self.assertRaisesRegex(ValueError,'invalid Segment heading format'):wc.revision_preview(self.root)

    def test_revision_instruction_ref_must_name_a_section(self):
        request=self.request([self.scope('composition-plan','/compositions/@composition_id=C01/frame_count')])
        request['instruction_ref']='decisions.md'
        with self.assertRaisesRegex(ValueError,'instruction_ref.*#section'):wc.revise(self.root,request)

    def test_appending_confirmation_section_does_not_change_instruction_diff(self):
        wc.revise(self.root,self.request([self.scope('composition-plan','/compositions/@composition_id=C01/frame_count')]))
        self.edit('composition-plan','/compositions/@composition_id=C01/frame_count',120)
        before=wc.revision_preview(self.root)['diff_sha256']
        target=self.root/'decisions.md';target.write_text(target.read_text()+'\n## R1 确认\n可以\n')
        after=wc.revision_preview(self.root)['diff_sha256']
        self.assertEqual(after,before)

    def test_revision_confirmation_ref_must_name_a_section(self):
        wc.revise(self.root,self.request([self.scope('composition-plan','/compositions/@composition_id=C01/frame_count')]))
        self.edit('composition-plan','/compositions/@composition_id=C01/frame_count',120)
        diff=wc.revision_preview(self.root)['diff_sha256']
        with self.assertRaisesRegex(ValueError,'confirmation_ref.*#section'):
            wc.confirm(self.root,('plan',),'synthetic_fixture_user','decisions.md',self.quote,[],False,None,diff)

    def test_same_short_approval_is_valid_only_from_a_new_section(self):
        # Establish an old plan approval whose wording is deliberately short.
        p=self.project();old=p['workflow_control']['confirmations']['plan'];old['quote']='可以';old['confirmation_ref']='decisions.md#旧计划确认'
        target=self.root/'decisions.md';target.write_text(target.read_text()+'\n## 旧计划确认\n可以\n')
        vp.write(self.root/'project.json',p)
        wc.revise(self.root,self.request([self.scope('composition-plan','/compositions/@composition_id=C01/frame_count')]))
        self.edit('composition-plan','/compositions/@composition_id=C01/frame_count',120)
        diff=wc.revision_preview(self.root)['diff_sha256']
        with self.assertRaisesRegex(ValueError,'confirmation_ref.*#section'):
            wc.confirm(self.root,('plan',),'synthetic_fixture_user','decisions.md','可以',[],False,None,diff)
        with self.assertRaisesRegex(ValueError,'new confirmation section'):
            wc.confirm(self.root,('plan',),'synthetic_fixture_user','decisions.md#旧计划确认','可以',[],False,None,diff)
        target=self.root/'decisions.md';target.write_text(target.read_text()+'\n## R1 确认\n可以\n')
        result=wc.confirm(self.root,('plan',),'synthetic_fixture_user','decisions.md#R1 确认','可以',[],False,None,diff)
        self.assertEqual(result['status'],'revision_committed')

    def test_previous_plan_approval_cannot_be_replayed_by_path_or_heading_alias(self):
        target = self.root / 'decisions.md'
        target.write_text(target.read_text() + '\n## Prior Plan Approval\n可以\n', encoding='utf-8')
        wc.confirm(self.root, ('plan',), 'synthetic_fixture_user',
                   './decisions.md#Prior Plan Approval', '可以', [])
        field = '/compositions/@composition_id=C01/frame_count'
        wc.revise(self.root, self.request([self.scope('composition-plan', field)]))
        self.edit('composition-plan', field, 120)
        diff = wc.revision_preview(self.root)['diff_sha256']
        for ref in ('decisions.md#Prior Plan Approval', './decisions.md#prior-plan-approval'):
            with self.subTest(ref=ref), self.assertRaisesRegex(ValueError, 'previous plan approval'):
                wc.confirm(self.root, ('plan',), 'synthetic_fixture_user', ref, '可以',
                           [], False, None, diff)
        self.assertTrue(self.project()['workflow_control']['method_preservation']['open_revision'])

    def test_instruction_section_cannot_supply_a_different_confirmation_quote_through_an_alias(self):
        field = '/compositions/@composition_id=C01/frame_count'
        request = self.request([self.scope('composition-plan', field)])
        target = self.root / 'decisions.md'
        quote = 'Different wording within the original instruction section.'
        target.write_text(target.read_text() + quote + '\n', encoding='utf-8')
        wc.revise(self.root, request)
        self.edit('composition-plan', field, 120)
        diff = wc.revision_preview(self.root)['diff_sha256']
        with self.assertRaisesRegex(ValueError, 'not its instruction'):
            wc.confirm(self.root, ('plan',), 'synthetic_fixture_user', './decisions.md#修订指令',
                       quote, [], False, None, diff)

    def test_method_revision_cannot_replay_previous_method_approval_by_alias(self):
        target = self.root / 'decisions.md'
        target.write_text(target.read_text() + '\n## Plan Only\n计划单独确认\n', encoding='utf-8')
        wc.confirm(self.root, ('plan',), 'synthetic_fixture_user',
                   'decisions.md#plan-only', '计划单独确认', [])
        field = '/compositions/@composition_id=C01/groups/push/keyframes/@key_id=push_end/easing'
        request = self.request([self.scope('composition-plan', field)], 'method')
        wc.revise(self.root, request)
        self.edit('composition-plan', field, 'linear')
        diff = wc.revision_preview(self.root)['diff_sha256']
        with self.assertRaisesRegex(ValueError, 'new actual decision section'):
            wc.confirm(self.root, ('plan', 'method'), 'synthetic_fixture_user', './decisions.md#计划确认',
                       self.quote, [], True, request['base_sha256'], diff)

    def test_whole_segment_container_replace_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'segment:segN add/remove'):
            wc.revise(self.root,self.request([self.scope('execution-plan','container:plan.segments')]))

    def test_segment_renumber_cannot_hide_an_undeclared_removal(self):
        scope=self.scope('execution-plan','segment:seg9','add');wc.revise(self.root,self.request([scope]))
        container={'artifact':'execution-plan','path':'container:plan.segments'}
        text=wc.method_value(wc._method_documents(self.root,self.project(),['execution-plan']),container)
        replacement=text.replace('### Segment 1','### Segment 9').replace('seg1.duration','seg9.duration')
        self.edit('execution-plan','container:plan.segments',replacement)
        diff=wc.revision_preview(self.root);self.assertEqual(diff['status'],'LINEAGE_VIOLATION')
        self.assertTrue(any(r['path']=='segment:seg1' and r['op']=='remove' and r['classification']=='out_of_scope' for r in diff['actual_diff']))
        self.assertTrue(any(r['path']=='segment:seg9' and r['op']=='add' and r['classification']=='in_scope' for r in diff['actual_diff']))

    def test_existing_segment_description_remains_frozen(self):
        scope=self.scope('execution-plan','block:seg1.duration');wc.revise(self.root,self.request([scope]))
        path=self.root/'execution-plan.md';path.write_text(path.read_text().replace('### Segment 1','### Segment 1 · 新说明'))
        diff=wc.revision_preview(self.root);self.assertEqual(diff['status'],'LINEAGE_VIOLATION')
        self.assertTrue(any(r['path']=='segment:seg1.title' and r['classification']=='out_of_scope' for r in diff['actual_diff']))

    def test_segment_number_is_identity_not_display_order(self):
        container={'artifact':'execution-plan','path':'container:plan.segments'}
        wc.revise(self.root,self.request([self.scope('execution-plan','segment:seg2','add')]))
        text=wc.method_value(wc._method_documents(self.root,self.project(),['execution-plan']),container)
        self.edit('execution-plan','container:plan.segments',text+'\n### Segment 2\n<!-- lvr:param seg2.duration -->2 s<!-- /lvr:param seg2.duration -->\n');self.close()
        wc.revise(self.root,self.request([self.scope('execution-plan','segment:seg3','add')]))
        text=wc.method_value(wc._method_documents(self.root,self.project(),['execution-plan']),container)
        marker='### Segment 2'
        insert='### Segment 3 · 中间新增\n<!-- lvr:param seg3.duration -->1 s<!-- /lvr:param seg3.duration -->\n\n'
        self.edit('execution-plan','container:plan.segments',text.replace(marker,insert+marker,1))
        diff=wc.revision_preview(self.root);self.assertEqual(diff['status'],'revision_ready_for_plan_confirmation')
        self.close();final=(self.root/'execution-plan.md').read_text()
        self.assertLess(final.index('### Segment 1'),final.index('### Segment 3'))
        self.assertLess(final.index('### Segment 3'),final.index('### Segment 2'))

    def test_templates_use_semantic_ids_and_segment_container(self):
        package=Path(wc.__file__).resolve().parents[1]
        for name in ('execution-plan-template.md','execution-reference-template.md'):
            text=(package/'assets'/name).read_text();self.assertNotIn('.field-',text);wc._revision_blocks(text)
        text=(package/'assets/execution-plan-template.md').read_text()
        self.assertIn('lvr:param seg1.duration',text);self.assertIn('lvr:container plan.segments',text)

    def test_adapt_preserves_current_plan_provenance_and_binds_patch(self):
        old=copy.deepcopy(self.project()['workflow_control']['confirmations']['plan'])
        result=wc.adapt_method(self.root,fixtures.MethodAdaptationTests.patch(self))
        new=self.project()['workflow_control']['confirmations']['plan']
        self.assertEqual(wc.evaluate(self.root)['plan']['status'],'satisfied')
        for key in ('actor','confirmation_ref','quote'):self.assertEqual(new[key],old[key])
        self.assertEqual(new['adaptation']['parent_input_digest'],old['input_digest'])
        self.assertEqual(new['adaptation']['patch_sha256'],wc.digest({key:value for key,value in result.items() if key not in ('status','method_preserved','workflow')}))

    def test_validation_evidence_changes_invalidate_an_already_displayed_diff(self):
        field='/compositions/@composition_id=C01/layers/@layer_id=panel-a/asset_ref'
        wc.revise(self.root,self.request([self.scope('composition-plan',field)]));self.edit('composition-plan',field,'media/b.png')
        old=wc.revision_preview(self.root)['diff_sha256']
        evidence=self.root/'units.jsonl';evidence.write_text(evidence.read_text()+'\n')
        self.assertNotEqual(wc.revision_preview(self.root)['diff_sha256'],old)
        with self.assertRaisesRegex(ValueError,'exact displayed'):self.close(diff=old)

    def test_cli_revise_status_shows_exact_diff(self):
        request=self.request([self.scope('composition-plan','/compositions/@composition_id=C01/frame_count')])
        request_file=self.root/'scope.json';vp.write(request_file,request)
        cli = self.test_package / 'scripts/workflow_control.py'
        shutil.copytree(Path(wc.__file__).parent, cli.parent)
        result=subprocess.run([sys.executable,str(cli),'revise',str(self.root),'--scope',str(request_file)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.edit('composition-plan','/compositions/@composition_id=C01/frame_count',120)
        result=subprocess.run([sys.executable,str(cli),'revise',str(self.root)],capture_output=True,text=True)
        self.assertIn('/compositions/@composition_id=C01/frame_count',result.stdout)
        self.assertIn('diff_sha256',json.loads(result.stdout))


if __name__=='__main__':unittest.main()
