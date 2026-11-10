"""Run the public V0–V7 contract using only generated test media."""
from pathlib import Path
import importlib.util
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import visual_pipeline as vp


@unittest.skipUnless(importlib.util.find_spec('PIL') and importlib.util.find_spec('numpy'),
                     'Visual stage integration requires Pillow and numpy')
class PublicVisualStages(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.project = Path(temp.name)
        self.visual = self.project / 'visual'
        self.visual.mkdir()
        self.stages = vp.VISUAL_STAGE_ORDER
        self.make_visual_records()

    def stage(self, index):
        return self.visual / (self.stages[index] + '.json')

    def write_stage(self, index, **data):
        vp.write(self.stage(index), dict(stage=f'V{index}', **data))

    def png(self, name, image, **options):
        file = self.visual / name
        image.save(file, **options)
        return {'file': name, 'sha256': vp.sha(file)}

    def make_visual_records(self):
        from PIL import Image, ImageDraw

        size = (320, 180)
        copy = 'Test panel'
        frame = Image.new('RGB', size, (36, 36, 36))
        ImageDraw.Draw(frame).rectangle((32, 36, 92, 112), fill='silver')
        source = self.png('source.png', frame)
        self.write_stage(0, project_id='synthetic-visual',
                         source=dict(source_id='SRC001', signature=source['sha256'],
                                     geometry=list(size), time_mapping='identity'),
                         confirmed_from_d2=dict(copy_status='confirmed', copy_lines=[
                             dict(id='T1', unit='U1', text=copy, role='act')]),
                         text_policy=dict(glyph_floor_px=12, contrast_median_min=4.5,
                                          contrast_worst_min=3, clearance_px=12),
                         keyframes=[dict(id='K1', unit='U1', file=source['file'], full_frame=True)],
                         design_scope=dict(mode='explore_new'))
        direction = dict(primary_direction='VD-01', attention_owner='action',
                         text_role='observer_comment', spatial_relation='adjacent',
                         timing_mode='reaction_echo', emphasis_budget='low')
        self.write_stage(1, shots=[dict(
            keyframe='K1',
            protect=[dict(id='object', **{'class': 'object'}, rect_src=[32, 36, 92, 112])],
            zones=[dict(id='quiet', rect_src=[110, 20, 310, 165], luma_mean=36, luma_std=0)],
            problems=[dict(id='P1', evidence=['quiet', 'object'])],
        )], direction_hypothesis=dict(
            analysis_order='after_visual_problem_before_reference',
            global_baseline=direction, per_shot=[dict(direction, keyframe='K1')]))
        self.write_stage(2, selections=[], no_ref_needed={
            'K1.P1': 'The synthetic source frame has a measured text zone.'
        }, direction_context=dict(source='V1.direction_hypothesis',
                                  global_primary_direction='VD-01',
                                  reference_goal='Compare text placement against the measured zone.'))
        candidates = []
        mockups = []
        for name, direction_id, placement, rect in [
            ('A', 'VD-01', 'fixed_slot', [120, 48, 224, 72]),
            ('B', 'VD-02', 'bespoke', [120, 120, 224, 144]),
        ]:
            strategy = dict(direction, primary_direction=direction_id)
            element = dict(id=f'{name}.copy', text=copy, role='label')
            candidates.append(dict(
                id=name, direction_strategy=strategy,
                art_direction_thesis=dict(
                    statement='Test panel uses measured negative space to preserve the geometric subject.',
                    copy_refs=['T1'], image_refs=['K1.object']),
                failure_condition=[dict(condition='Text overlaps the protected object.')],
                dimensions=dict(text_direction='horizontal', placement_logic=placement,
                                image_text_relation='in_frame_clean_zone',
                                polarity_strategy='auto_dark_or_light', geometry='crop'),
                style=dict(fonts={'test': {}}, roles={'label': {'font': 'test'}}, ink={}),
                ref_trace=[],
                per_shot=[dict(
                    keyframe='K1', direction_use=strategy, elements=[element],
                    composition_grammar=dict(primary_subject='K1.object', text_shape='single_line',
                                             negative_space='K1.quiet', visual_axis='left to right',
                                             visual_weight='protect the test shape first',
                                             reading_order=['K1.object', 'K1.quiet', element['id']]),
                    shot_dependency=dict(depends_on=['K1.quiet'],
                                         if_moved='Recheck available text space in the new frame.'))],
            ))
            mockup = frame.copy()
            ImageDraw.Draw(mockup).text(rect[:2], copy, fill='white')
            mockups.append(dict(
                self.png(f'mockup-{name}.png', mockup), keyframe='K1', candidate=name,
                scale_x_equals_scale_y=True,
                elements=[dict(element, rect=rect, min_hanzi_ink_px=14, contrast_median=6,
                               contrast_worst=5, min_clearance_px=28, subtitle_overlap=False)]))
        self.write_stage(3, candidates=candidates, direction_read=dict(
            direction, source_hypothesis='V1.direction_hypothesis', typography_voice='neutral_observer'))
        self.write_stage(4, renderer='Pillow synthetic test', mockups=mockups)

        chosen = mockups[0]
        shown = {key: chosen[key] for key in ('candidate', 'file', 'sha256')}
        baseline_image = frame.copy()
        ImageDraw.Draw(baseline_image).text((170, 82), copy, fill='white')
        baseline = self.png('baseline.png', baseline_image)
        board = self.png('board.png', baseline_image.resize((240, 135)))
        self.write_stage(5, quality_claim='not_automated',
                         presented_to_user=dict(context='user', what='Simulated test display', artifacts=[shown]),
                         independent_review=dict(status='not_used', reason='Synthetic integration fixture.'),
                         review_scope=dict(blur_squint=dict(status='not_needed',
                                                           reason='Mechanical contract test only.')),
                         review_artifacts={'small_screen_board': board},
                         same_source_ab=dict(
                             controls=dict(keyframe='K1', copy_ids=['T1'], same_source=True,
                                           same_canvas=True, same_copy=True, audio_unchanged=True,
                                           canvas=list(size), source_frame=dict(source, keyframe='K1')),
                             baseline=baseline, candidate=dict(shown, keyframe='K1'),
                             observations=dict(hierarchy='The subject remains separated from the caption.',
                                               person_text_relation='Caption placement uses the measured zone.',
                                               typography_voice='The test label keeps the same caption text.'),
                             result=dict(status='visible_change', evidence_use='comparison_only')))
        self.write_stage(6, status='confirmed', chosen_candidate='A',
                         user_message_verbatim='Simulated approval for test only.', confirmed_artifacts=[shown])
        self.write_stage(7, chosen_candidate='A', style=candidates[0]['style'],
                         canvas=list(size), reference_trace=[], elements=[
                             dict(chosen['elements'][0], keyframe='K1', t_in=0.2, t_out=1.5, motion={})])

    def cli(self, script, *args):
        return subprocess.run([sys.executable, '-IB', str(script), *map(str, args)],
                              capture_output=True, text=True, timeout=45)

    def check_stage(self, index, status, error=None):
        scripts = vp.REFERENCE_PACKAGE / 'scripts'
        refreshed = self.cli(scripts / 'refresh_visual_chain.py', self.visual)
        self.assertEqual(refreshed.returncode, 0, refreshed.stdout + refreshed.stderr)
        checked = self.cli(vp.VISUAL_STAGE_CHECKER, self.visual, '--package', vp.REFERENCE_PACKAGE)
        self.assertEqual(checked.returncode, 0 if error is None else 1, checked.stdout + checked.stderr)
        self.assertIn([self.stages[index], status], [line.split() for line in checked.stdout.splitlines()])
        if error is not None:
            self.assertIn(error, checked.stdout)

    def test_public_visual_chain_syncs_implementation_lock(self):
        self.check_stage(7, 'PASS')
        project = vp.read(ROOT / 'assets/project-template.json')
        project['visual_mockup_ref'] = 'visual/mockup-A.png'
        vp.write(self.project / 'project.json', project)
        lock_file = self.project / 'implementation-lock.json'
        vp.write(lock_file, vp.read(ROOT / 'assets/implementation-lock-template.json'))
        synced = self.cli(ROOT / 'scripts/sync_visual_stage.py', self.project,
                          '--target', 'implementation-lock')
        self.assertEqual(synced.returncode, 0, synced.stdout + synced.stderr)
        lock = vp.read(lock_file)
        self.assertEqual(lock['reference_trace'], [])
        self.assertEqual(lock['visual_stage_binding']['v7_sha256'], vp.sha(self.stage(7)))
        self.assertEqual(lock['confirmed_mockups'][0]['sha256'], vp.sha(self.visual / 'mockup-A.png'))

    def test_v1_problem_coverage_is_required(self):
        v2 = vp.read(self.stage(2))
        v2['no_ref_needed'] = {}
        vp.write(self.stage(2), v2)
        self.check_stage(2, 'FAIL', 'no_ref_needed')

    def test_new_design_requires_same_source_ab(self):
        v5 = vp.read(self.stage(5))
        del v5['same_source_ab']
        vp.write(self.stage(5), v5)
        self.check_stage(5, 'FAIL', 'same_source_ab')

    def test_reencoded_pixels_cannot_count_as_improvement(self):
        from PIL import Image

        v5 = vp.read(self.stage(5))
        comparison = v5['same_source_ab']
        with Image.open(self.visual / comparison['candidate']['file']) as image:
            comparison['baseline'] = self.png('reencoded.png', image, compress_level=0)
        self.assertNotEqual(comparison['baseline']['sha256'], comparison['candidate']['sha256'])
        vp.write(self.stage(5), v5)
        self.check_stage(5, 'FAIL', 'no_visible_change')

    def test_confirmation_must_bind_the_displayed_mockup(self):
        v6 = vp.read(self.stage(6))
        v6['confirmed_artifacts'][0]['sha256'] = '0' * 64
        vp.write(self.stage(6), v6)
        self.check_stage(6, 'FAIL', 'V5')
