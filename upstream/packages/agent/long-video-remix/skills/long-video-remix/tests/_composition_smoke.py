#!/usr/bin/env python3
"""Generate synthetic media and pending production records. Never approve gates."""
import array
import math
import wave

import visual_pipeline as vp
from _synthetic_project import SYNTHETIC_REFERENCE, copy_synthetic_ready


def build(root):
    vp.require(not root.exists(), 'Choose a new fixture directory; existing work is preserved')
    copy_synthetic_ready(root)
    reference = vp.visual_reference_catalog()[SYNTHETIC_REFERENCE]
    from PIL import Image, ImageDraw
    media = root / 'media'
    media.mkdir()
    for name, color, direction in [('a', (32, 58, 78), 1), ('b', (64, 43, 54), -1)]:
        image = Image.new('RGB', (320, 180), color)
        draw = ImageDraw.Draw(image)
        draw.rectangle((14, 14, 305, 165), outline=(195, 200, 205), width=2)
        draw.ellipse((72, 54, 112, 94), fill=(210, 208, 200))
        draw.ellipse((205, 54, 245, 94), fill=(210, 208, 200))
        draw.line((94, 74, 225, 74), fill=(152, 179, 190), width=2)
        draw.text((24, 140), 'SYNTHETIC ENGINEERING TEST ' + name.upper(), fill=(225, 225, 225))
        image.save(media / (name + '.png'))
    samples = array.array('h')
    for index in range(5 * 48000):
        value = round(1600 * math.sin(index * 2 * math.pi * 220 / 48000))
        samples.extend((value, value))
    with wave.open(str(media / 'audio.wav'), 'wb') as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(48000)
        handle.writeframes(samples.tobytes())
    project = vp.read(root / 'project.json')
    project['current_stage'] = 'D2'
    project['render_authorized'] = False
    project['execution_plan_status'] = 'not_provided'
    # The synthetic-ready snapshot contains a historical proof-confirmed example.
    # This fixture intentionally starts before Proof so current D2 gates can be exercised.
    project['visual_gate_status'] = 'mockup_confirmed'
    project['visual_proof_ref'] = 'proof.svg'  # candidate artifact exists but is not confirmed
    project['execution_reference_asset_refs'] = ['mockup.svg', 'capability-map.json']
    vp.write(root / 'project.json', project)
    timeline = vp.read(root / 'timeline.json')
    timeline['status'] = 'draft'
    for track in timeline.get('text_tracks', []):
        track.setdefault('text_role', 'creator_text')
        track.setdefault('glyph_height_px', 14)
        track.setdefault('canvas_height_px', 180)
    vp.write(root / 'timeline.json', timeline)
    project = vp.initialize(root)
    # Exercise existing-project reference routing. V0–V7 has its own integration tests.
    project['visual_pipeline'].pop('visual_stage_dir', None)
    project['output'] = {'width': 320, 'height': 180, 'fps_num': 25, 'fps_den': 1}
    project['workflow_control']['audio_choice'] = {'mode': 'no_music', 'description': 'Synthetic test tone; no music or dialogue claim', 'ref': 'demo-spec.md#Audio'}
    project['workflow_control']['visual_spec_refs'] = ['demo-spec.md#Visual']
    vp.write(root / 'project.json', project)
    (root / 'demo-spec.md').write_text('# Audio\n\nSynthetic stereo test tone only.\n\n# Visual\n\nTwo generated panels; group push and a deliberate cut. Engineering test only.\n\n# Production Lock\n\nBlender composition worker + finish_ffmpeg.py; fixed 320x180/25fps fixture, no toolchain substitution.\n', encoding='utf-8')
    project = vp.read(root / 'project.json')
    project['workflow_control']['production_spec_refs'] = ['demo-spec.md#Production Lock']
    vp.write(root / 'project.json', project)
    vp.write(root / 'visual-methods.json', {'schema_version': '1.0', 'project_id': project['project_id'], 'methods': [{
        'method_id': 'PM001', 'library_refs': ['M13'], 'fallback_refs': ['F09'],
        'visual_reference_status': 'used', 'visual_reference_refs': [SYNTHETIC_REFERENCE],
        'viewed_reference_assets': [{'ref_id': SYNTHETIC_REFERENCE,
            'asset_path': reference['asset_path'],
            'sha256': reference['sha256'],
            'observation': 'Synthetic fixture records the strong type scale versus stable subject area; no source design is copied.'}],
        'reference_selection_reason': 'Tests the required reference-routing contract before engineering, not an aesthetic preference.',
        'reference_transfer_principles': ['Use hierarchy and spatial separation to protect the subject area.'],
        'reference_do_not_copy': ['Do not copy the source portrait, brand lettering, texture or exact composition.'],
        'visual_reference_not_applicable_reason': None,
        'event_ids': ['E001'], 'source_evidence_refs': ['DO001'],
        'narrative_role': 'Synthetic engineering example; no real narrative assertion',
        'visual_focus': 'The two circles and their common relation remain visible',
        'source_conditions': 'Generated 320x180 panels with explicit safe margins',
        'original_frame_assessment': 'Use a restrained group push to test saved motion and end-state continuity',
        'selected_treatment': 'Group push, hold the achieved pose, then a declared hard cut to panel B',
        'selection_reason': 'Tests shared motion, absence of reset, and coverage of both sides of a cut',
        'alternatives_considered': [], 'parameters': {'scale_start': 1, 'scale_end': 1.08, 'motion_end_frame': 60, 'cut_frame': 75},
        'failure_modes': ['End pose resets before the cut', 'Foreground and image move independently'],
        'demo_checks': ['Actual frames 60..74 hold the achieved pose', 'Both sides of frame 75 are visible'],
        'composition_required': True}]})
    mockup_sha = vp.sha(root / project['visual_mockup_ref'])
    vp.write(root / 'implementation-lock.json', {
        'schema_version': '1.0', 'project_id': project['project_id'],
        'selected_mockup_ref': project['visual_mockup_ref'], 'selected_mockup_sha256': mockup_sha,
        'output': project['output'],
        'renderer_lock': {
            'toolchain': [
                {'role': 'composition', 'actual_tool': 'blender', 'entrypoint': 'scripts/render_blender_composition.py'},
                {'role': 'delivery', 'actual_tool': 'ffmpeg', 'entrypoint': 'scripts/finish_ffmpeg.py'}],
            'final_execute_entrypoint': 'scripts/finish_ffmpeg.py'},
        'palette': {'fixture_panel': '#203A4E'},
        'fonts': {},
        'elements': {
            'PANEL_PUSH': {
                'role': 'Protect subject area while testing a shared restrained push.',
                'renderer': 'blender_layers', 'implementation_method': 'group_transform',
                'event_ids': ['E001'],
                'parameters': {'scale_start': 1.0, 'scale_end': 1.08, 'motion_end_frame': 60}},
            'PANEL_CUT': {
                'role': 'Declared hard cut after the held pose.',
                'renderer': 'blender_layers', 'implementation_method': 'layer_switch',
                'event_ids': ['E001'],
                'parameters': {'cut_frame': 75}}
        },
        'reference_trace': [{
            'method_id': 'PM001', 'ref_id': SYNTHETIC_REFERENCE, 'mockup_ref': project['visual_mockup_ref'],
            'applied_principles': ['Use hierarchy and spatial separation to protect the subject area.'],
            'target_element_ids': ['PANEL_PUSH'],
            'parameter_paths': ['elements.PANEL_PUSH.parameters.scale_start', 'elements.PANEL_PUSH.parameters.scale_end'],
            'proof_checks': ['The subject area remains stable/readable through the restrained push.'],
            'do_not_copy_checks': ['No source portrait, brand lettering, texture or exact composition is reproduced.']
        }],
        'parameter_bindings': [{
            'source': {'artifact': 'implementation-lock', 'path': '/elements/PANEL_PUSH/parameters/scale_end'},
            'targets': [
                {'artifact': 'visual-methods', 'path': '/methods/@method_id=PM001/parameters/scale_end'},
                {'artifact': 'composition-plan', 'path': '/compositions/@composition_id=C01/groups/push/keyframes/@key_id=push_end/values/scale'},
                {'artifact': 'composition-plan', 'path': '/compositions/@composition_id=C01/joins/@join_id=J01/outgoing_state',
                 'format': 'Hold the {value} scale; no reset'}]}],
        'safe_adaptation': {'allowed': [{'slot': 'push_scale_end', 'artifact': 'implementation-lock',
            'path': '/elements/PANEL_PUSH/parameters/scale_end', 'type': 'number', 'minimum': 1.0, 'maximum': 1.12}],
            'requires_d2_return': ['renderer substitution', 'layout reinterpretation', 'motion grammar/easing change']}
    })
    project = vp.read(root / 'project.json')
    project['execution_reference_asset_refs'] = ['mockup.svg', 'implementation-lock.json', 'capability-map.json']
    vp.write(root / 'project.json', project)
    vp.write(root / 'composition-plan.json', {'schema_version': '1.0', 'project_id': project['project_id'],
        'implementation_lock_ref': 'implementation-lock.json',
        'output': project['output'], 'proof_scope_policy': 'representative_risk_based_v1', 'proof_composition_ids': ['C01'], 'compositions': [{
            'composition_id': 'C01', 'backend': 'blender', 'mode': 'layers', 'method_ids': ['PM001'],
            'implementation_element_ids': ['PANEL_PUSH', 'PANEL_CUT'],
            'event_ids': ['E001'], 'anchor_event_id': 'E001', 'local_start_frame': 0, 'frame_count': 125,
            'groups': {'push': {'transform': {}, 'keyframes': [{'key_id': 'push_start', 'frame': 0, 'values': {'scale': 1}},
                        {'key_id': 'push_end', 'frame': 60, 'values': {'scale': 1.08}, 'easing': 'smoothstep'}]}},
            'layers': [
                {'layer_id': 'panel-a', 'kind': 'image', 'asset_ref': 'media/a.png', 'start_frame': 0, 'end_frame': 75, 'parent': 'push', 'fit': 'cover'},
                {'layer_id': 'panel-b', 'kind': 'image', 'asset_ref': 'media/b.png', 'start_frame': 75, 'end_frame': 125, 'fit': 'cover'}],
            'joins': [{'join_id': 'J01', 'frame': 75, 'before_frames': 25, 'after_frames': 25,
                       'from_event_id': 'E001', 'to_event_id': 'E001', 'cut_intent': 'A declared internal panel cut in one synthetic event',
                       'outgoing_state': 'Hold the 1.08 scale; no reset', 'incoming_state': 'Stable full panel B',
                       'motion_handoff': 'End the push before the deliberate cut; no automatic crossfade'}],
            'preview_audio_ref': 'media/audio.wav', 'silent_demo': False,
            'scene_ref': 'compositions/C01/v1.blend', 'video_ref': 'compositions/C01/v1-visual.mp4',
            'demo_ref': 'compositions/C01/v1-demo.mp4', 'proof_ref': 'compositions/C01/v1-proof.png',
            'receipt_ref': 'compositions/C01/v1-render.json', 'readback_ref': 'compositions/C01/v1-readback.json',
            'review_ref': 'compositions/C01/v1-review.json'}]})
    vp.write(root / 'delivery-spec.json', {'schema_version': '1.0', 'project_id': project['project_id'],
        'base_video_ref': 'render/clean-video.mp4', 'mixed_audio_ref': 'media/audio.wav',
        'subtitles_ref': None, 'font_refs': [], 'crf': 18, 'output_ref': 'render/final.mp4'})
    vp.require(project['workflow_control']['confirmations'] == {}, 'Fixture must not contain approval records')
    return {'project': str(root.resolve()), 'status': 'pending_decisions', 'render_authorized': False,
            'scope': 'Synthetic engineering input, not real-media or aesthetic acceptance'}
