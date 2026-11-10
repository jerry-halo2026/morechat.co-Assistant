#!/usr/bin/env python3
"""Render Blender compositions with two explicit purposes.

proof: only proof_composition_ids, before Execute, with demo/proof/review pending.
production: deferred non-proof windows, after final authorization, without demo review.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile

import visual_pipeline as vp


def render(root, composition_id, blender='blender', purpose=None):
    from workflow_control import require_action
    project = vp.read(root / 'project.json')
    vp.policy(project)
    plan = vp.composition_plan(root, project)
    matches = [row for row in plan['compositions'] if row['composition_id'] == composition_id]
    vp.require(len(matches) == 1, 'Unknown composition_id')
    job = matches[0]
    proof_ids = vp.proof_composition_ids(plan)
    representative = composition_id in set(proof_ids)
    if purpose is None:
        purpose = 'proof' if representative else 'production'
    vp.require(purpose in ('proof', 'production'), 'purpose must be proof or production')
    if purpose == 'proof':
        vp.require(representative,
                   'Only proof_composition_ids may be rendered as the pre-Execute Dynamic Demo / Proof')
        require_action(root, 'build_composition')
        keys = ('scene_ref', 'video_ref', 'demo_ref', 'proof_ref', 'receipt_ref', 'readback_ref', 'review_ref')
    else:
        # Non-proof compositions are intentionally deferred until Execute. This
        # prevents N planned Blender windows from becoming N pre-approval demos.
        require_action(root, 'render')
        keys = ('scene_ref', 'video_ref', 'receipt_ref', 'readback_ref')
    targets = {key: vp.path_at(root, job[key]) for key in keys}
    for target in targets.values():
        vp.require(not target.exists(), 'Use new artifact names for a revised composition; existing outputs are preserved: ' + str(target))
        target.parent.mkdir(parents=True, exist_ok=True)
    executable = shutil.which(blender)
    if executable is None and Path(blender).is_file():
        executable = str(Path(blender).resolve())
    vp.require(executable is not None, 'Blender executable unavailable; the gate remains pending')
    worker = Path(__file__).with_name('blender_composite_worker.py').resolve()
    inputs = vp.job_input(root, project, plan, job)
    original_digest = vp.digest(inputs)
    dimensions = {}
    for layer in job.get('layers', []):
        if layer.get('kind') in ('image', 'video'):
            media = vp.probe(vp.path_at(root, layer['asset_ref']), count=False)
            streams = [r for r in media.get('streams', []) if r.get('codec_type') == 'video']
            vp.require(len(streams) == 1, 'Image/video layer requires one decodable video stream')
            stream = streams[0]
            dimensions[layer['asset_ref']] = [stream['width'], stream['height']]
            if layer['kind'] == 'video':
                from fractions import Fraction
                vp.require(Fraction(stream['avg_frame_rate']) == Fraction(plan['output']['fps_num'], plan['output']['fps_den']),
                           'Normalize source videos to the project frame rate with FFmpeg before compositing')
    lock = vp.path_at(root, '.composition-render.lock')
    descriptor = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    published = []
    try:
        with tempfile.TemporaryDirectory(prefix='.composition-', dir=str(targets['scene_ref'].parent)) as directory:
            work = Path(directory)
            frames = work / 'frames'
            frames.mkdir()
            payload = {'job': job, 'output': plan['output'], 'project_root': str(root.resolve()),
                       'asset_dimensions': dimensions, 'frames_directory': str(frames),
                       'scene_output': str(work / 'engineering.blend'),
                       'scene_final_parent': str(targets['scene_ref'].parent),
                       'readback_output': str(work / 'readback.json')}
            vp.write(work / 'job.json', payload)
            command = [executable, '--background', '--factory-startup', '--disable-autoexec', '--threads', '2',
                       '--python-exit-code', '1', '--python', str(worker), '--', str(work / 'job.json')]
            log = vp.run(command, timeout=1800)
            readback = vp.read(work / 'readback.json')
            first = readback['first_native_frame']
            vp.require(len(list(frames.glob('frame_*.png'))) == job['frame_count'], 'Blender did not render every expected frame')
            fps = str(plan['output']['fps_num']) + '/' + str(plan['output']['fps_den'])
            vp.run([vp.tool('ffmpeg'), '-v', 'error', '-n', '-framerate', fps, '-start_number', str(first),
                    '-i', str(frames / 'frame_%06d.png'), '-frames:v', str(job['frame_count']),
                    '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(work / 'visual.mp4')])
            technical = vp.verify_video(work / 'visual.mp4', plan['output'], job['frame_count'])
            if purpose == 'proof':
                if job.get('preview_audio_ref'):
                    duration = job['frame_count'] * plan['output']['fps_den'] / plan['output']['fps_num']
                    audio = vp.path_at(root, job['preview_audio_ref'])
                    audio_probe = vp.probe(audio, count=False)
                    audio_streams = [r for r in audio_probe.get('streams', []) if r.get('codec_type') == 'audio']
                    vp.require(bool(audio_streams), 'Preview audio file contains no audio')
                    audio_duration = float(audio_probe.get('format', {}).get('duration', 0))
                    vp.require(audio_duration + 0.02 >= duration, 'Preview audio must cover the full demo; no automatic padding')
                    vp.run([vp.tool('ffmpeg'), '-v', 'error', '-n', '-i', str(work / 'visual.mp4'), '-i', str(audio),
                            '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-t', str(duration),
                            '-movflags', '+faststart', str(work / 'demo.mp4')])
                else:
                    shutil.copyfile(work / 'visual.mp4', work / 'demo.mp4')
                vp.verify_video(work / 'demo.mp4', plan['output'], job['frame_count'], bool(job.get('preview_audio_ref')))
            current = vp.read(root / 'project.json')
            current_plan = vp.composition_plan(root, current)
            current_job = next(row for row in current_plan['compositions'] if row['composition_id'] == composition_id)
            vp.require(vp.digest(vp.job_input(root, current, current_plan, current_job)) == original_digest,
                       'Inputs changed while rendering; no artifact is published')
            for key, name in [('scene_ref', 'engineering.blend'), ('video_ref', 'visual.mp4'),
                              ('readback_ref', 'readback.json')]:
                os.link(str(work / name), str(targets[key]))
                published.append(targets[key])
            artifact_keys = ['scene_ref', 'video_ref']
            if purpose == 'proof':
                os.link(str(work / 'demo.mp4'), str(targets['demo_ref']))
                published.append(targets['demo_ref'])
                proof_frame = job.get('proof_frame', job['frame_count'] // 2)
                vp.require(type(proof_frame) is int and 0 <= proof_frame < job['frame_count'], 'Invalid proof_frame')
                os.link(str(frames / ('frame_%06d.png' % (first + proof_frame))), str(targets['proof_ref']))
                published.append(targets['proof_ref'])
                artifact_keys += ['demo_ref', 'proof_ref']
            artifact_keys += ['readback_ref']
            receipt = {'schema_version': '1.0', 'status': 'rendered_not_reviewed', 'backend': 'blender',
                       'purpose': purpose, 'backend_version': readback['backend_version'],
                       'project_id': project['project_id'], 'composition_id': composition_id,
                       'input_digest': original_digest,
                       'artifacts': [vp.binding(root, job[key]) for key in artifact_keys],
                       'technical': technical, 'worker_sha256': vp.sha(worker),
                       'actual_command': [str(x) for x in command[:command.index('--')]],
                       'log_sha256': vp.hashlib.sha256(log).hexdigest(), 'playback_verified': False}
            vp.write(targets['receipt_ref'], receipt)
            published.append(targets['receipt_ref'])
            if purpose == 'proof':
                selected_refs = vp.selected_reference_ids(root, project)
                mockups = vp.confirmed_visual_artifacts(root, project)
                review = {'schema_version': '1.0', 'composition_id': composition_id,
                          'demo_sha256': vp.binding(root, job['demo_ref'])['sha256'],
                          'engineering_sha256': vp.binding(root, job['scene_ref'])['sha256'],
                          'render_input_digest': original_digest, 'reviewer': None, 'playback_verified': False,
                          'blocking_issues': ['Continuous playback and composition checks are pending'],
                          'checks': [dict({'name': name, 'status': 'not_tested', 'method': None, 'evidence': [], 'finding': None},
                                          **({'reference_ref_ids': selected_refs,
                                              'implementation_lock_sha256': vp.binding(root, project['visual_pipeline']['implementation_lock_ref'])['sha256'],
                                              'implementation_scope_digest': inputs['reference_application']['implementation_lock']['scope_digest'],
                                              'mockup_sha256': vp.binding(root, project['visual_mockup_ref'])['sha256'],
                                              'mockup_sha256s': ({x['ref']: x['sha256'] for x in mockups} if vp.visual_stage_dir(project) is not None else None),
                                              'visual_stage_v7_sha256': (vp.visual_stage_report(root, project, 'V7-lock')['artifacts']['V7-lock']['sha256'] if vp.visual_stage_dir(project) is not None else None),
                                              'proof_sha256': vp.binding(root, job['proof_ref'])['sha256']}
                                             if name == 'ReferenceCompliance' else {}))
                                     for name in vp.REVIEW_CHECKS]}
                vp.write(targets['review_ref'], review)
                published.append(targets['review_ref'])
                # Register measured capability/artifact paths, never approve them.
                project = vp.read(root / 'project.json')
                # Keep the legacy single proof pointer as the primary proof while
                # v1.4.5 records the complete representative proof set separately.
                current_plan = vp.composition_plan(root, project)
                current_jobs = {row['composition_id']: row for row in current_plan['compositions']}
                current_proof_ids = vp.proof_composition_ids(current_plan)
                primary_ref = current_jobs[current_proof_ids[0]]['proof_ref']
                project['visual_proof_ref'] = primary_ref
                available_proof_refs = [current_jobs[cid]['proof_ref'] for cid in current_proof_ids
                                        if vp.path_at(root, current_jobs[cid]['proof_ref']).is_file()]
                if len(current_proof_ids) > 1:
                    project['visual_proof_refs'] = available_proof_refs
                else:
                    project.pop('visual_proof_refs', None)
                project['visual_gate_status'] = 'awaiting_proof'
                refs = project.setdefault('execution_reference_asset_refs', [])
                bound_refs = [x['ref'] for x in vp.confirmed_visual_artifacts(root, project)]
                if vp.visual_stage_dir(project) is not None:
                    bound_refs.append(vp.visual_stage_report(root, project, 'V7-lock')['artifacts']['V7-lock']['ref'])
                bound_refs += [project['visual_pipeline']['implementation_lock_ref'], job['proof_ref'], 'capability-map.json']
                for ref in bound_refs:
                    if ref and ref not in refs:
                        refs.append(ref)
                cap_path = root / 'capability-map.json'
                caps = vp.read(cap_path) if cap_path.exists() else {'schema_version': '1.0', 'capabilities': []}
                caps['capabilities'] = [row for row in caps.get('capabilities', [])
                                        if not (row.get('capability') == 'compose_layers' and row.get('composition_id') == composition_id)]
                caps['capabilities'].append({'capability': 'compose_layers', 'composition_id': composition_id,
                    'status': 'available', 'actual_tool': 'Blender ' + readback['backend_version'] + ' + FFmpeg',
                    'entrypoint': 'scripts/render_blender_composition.py PROJECT --composition ' + composition_id + ' --purpose proof',
                    'output_mapping': {'proof': job['proof_ref'], 'scene': job['scene_ref'], 'video': job['video_ref'], 'demo': job['demo_ref']},
                    'time_unit': 'frame', 'end_semantics': 'exclusive', 'tested_range': [0, job['frame_count']],
                    'audio_observation': False, 'video_observation': False,
                    'limits': {'mode': job.get('mode', 'layers'), 'human_review_pending': True}})
                vp.write(cap_path, caps)
                from workflow_control import save_project
                save_project(root, project)
            return receipt
    except BaseException:
        for target in reversed(published):
            target.unlink(missing_ok=True)
        raise
    finally:
        lock.unlink(missing_ok=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project_directory', type=Path)
    parser.add_argument('--composition', required=True)
    parser.add_argument('--blender', default=os.environ.get('BLENDER_EXECUTABLE', 'blender'))
    parser.add_argument('--purpose', choices=('proof', 'production'), help='Default: proof for proof_composition_ids; production for other compositions')
    args = parser.parse_args()
    try:
        result = render(args.project_directory.resolve(), args.composition, args.blender, args.purpose)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, TypeError, KeyError, OSError, vp.subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc), 'render_allowed': False}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
