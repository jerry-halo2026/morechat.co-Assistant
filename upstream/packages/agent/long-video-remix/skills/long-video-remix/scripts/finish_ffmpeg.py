#!/usr/bin/env python3
"""Return reviewed Blender windows to the authorized FFmpeg edit; never pass QA.

The base video is produced by the existing FFmpeg renderer from the current
render-manifest. This adapter preserves its other windows and approved mix.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile

import visual_pipeline as vp


def finish(root):
    from workflow_control import require_action
    from check_render_authorization import check
    project = vp.read(root / 'project.json')
    vp.policy(project)
    require_action(root, 'render')
    manifest_path = root / 'render-manifest.json'
    manifest = vp.read(manifest_path)
    check(root, manifest)
    ctl = vp.policy(project)
    spec = vp.delivery_spec(root, project)
    source_inputs = vp.delivery_inputs(root, project)
    profile = {key: manifest[key] for key in ('width', 'height', 'fps_num', 'fps_den')}
    base = vp.path_at(root, spec['base_video_ref'])
    vp.verify_video(base, profile, manifest['total_frames'])
    target = vp.path_at(root, spec.get('output_ref'))
    receipt_path = vp.path_at(root, ctl['delivery_receipt_ref'])
    vp.require(not target.exists() and not receipt_path.exists(), 'Use new delivery paths; completed outputs/receipts are preserved')
    vp.require(project['workflow_control'].get('render_output_ref') == spec['output_ref'],
               'Declare the same final output in delivery-spec and workflow_control before authorization')
    mixed = spec.get('mixed_audio_ref')
    audio_required = manifest.get('audio_required', True)
    vp.require(not audio_required or bool(mixed), 'The approved mixed_audio_ref is required; no automatic music or audio replacement')
    compositions = manifest.get('compositions')
    vp.require(isinstance(compositions, list) and bool(compositions), 'Compiled Blender delivery windows are required')
    vp.require(compositions == vp.manifest_compositions(root, project, manifest), 'Composition windows or media changed after compilation')
    target.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    duration = manifest['total_frames'] * manifest['fps_den'] / manifest['fps_num']
    if mixed:
        audio_media = vp.probe(vp.path_at(root, mixed), count=False)
        vp.require(any(row.get('codec_type') == 'audio' for row in audio_media.get('streams', [])), 'Mixed audio has no audio stream')
        vp.require(float(audio_media.get('format', {}).get('duration', 0)) + .02 >= duration,
                   'Mixed audio is shorter than the manifest; fix the mix instead of silently padding it')
    with tempfile.TemporaryDirectory(prefix='.ffmpeg-finish-', dir=str(target.parent)) as directory:
        work = Path(directory)
        command = [vp.tool('ffmpeg'), '-v', 'error', '-n', '-i', str(base)]
        for row in compositions:
            clip = vp.path_at(root, row['video']['ref'])
            vp.verify_video(clip, profile, row['end_frame'] - row['start_frame'])
            command += ['-i', str(clip)]
        audio_index = len(compositions) + 1
        if mixed:
            command += ['-i', str(vp.path_at(root, mixed))]
        graph, parts, cursor = [], [], 0
        for index, row in enumerate(compositions, 1):
            if cursor < row['start_frame']:
                label = 'base' + str(index)
                graph.append('[0:v]trim=start_frame={}:end_frame={},setpts=PTS-STARTPTS[{}]'.format(cursor, row['start_frame'], label))
                parts.append('[' + label + ']')
            label = 'composition' + str(index)
            graph.append('[{}:v]trim=end_frame={},setpts=PTS-STARTPTS[{}]'.format(index, row['end_frame'] - row['start_frame'], label))
            parts.append('[' + label + ']')
            cursor = row['end_frame']
        if cursor < manifest['total_frames']:
            graph.append('[0:v]trim=start_frame={}:end_frame={},setpts=PTS-STARTPTS[tail]'.format(cursor, manifest['total_frames']))
            parts.append('[tail]')
        graph.append(''.join(parts) + 'concat=n={}:v=1:a=0[assembled]'.format(len(parts)))
        video_label = '[assembled]'
        if spec.get('subtitles_ref'):
            source = vp.path_at(root, spec['subtitles_ref'])
            vp.require(source.suffix.lower() == '.ass', 'Use the approved ASS subtitle file for reproducible styling')
            shutil.copyfile(source, work / 'captions.ass')
            font_dir = work / 'fonts'
            font_dir.mkdir()
            for index, ref in enumerate(spec.get('font_refs', [])):
                font = vp.path_at(root, ref)
                shutil.copyfile(font, font_dir / ('font' + str(index) + font.suffix))
            graph.append('[assembled]ass=filename=captions.ass:fontsdir=fonts[captioned]')
            video_label = '[captioned]'
        graph_path = work / 'filters.txt'
        graph_path.write_text(';\n'.join(graph) + '\n', encoding='utf-8')
        fps = str(profile['fps_num']) + '/' + str(profile['fps_den'])
        command += ['-filter_complex_script', str(graph_path), '-map', video_label]
        if mixed:
            command += ['-map', str(audio_index) + ':a:0', '-c:a', 'aac', '-b:a', '192k']
        else:
            command += ['-an']
        command += ['-frames:v', str(manifest['total_frames']), '-r', fps,
                    '-c:v', 'libx264', '-preset', 'medium', '-crf', str(spec.get('crf', 18)),
                    '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-t', str(duration), str(work / 'final.mp4')]
        vp.run(command, timeout=3600, cwd=work)
        technical = vp.verify_video(work / 'final.mp4', profile, manifest['total_frames'], audio_required)
        check(root, vp.read(manifest_path))
        vp.require(vp.digest(vp.delivery_inputs(root, project)) == vp.digest(source_inputs),
                   'Delivery inputs changed while FFmpeg was running')
        os.link(str(work / 'final.mp4'), str(target))
        try:
            receipt = {'schema_version': '1.0', 'status': 'rendered_not_reviewed', 'backend': 'ffmpeg',
                       'project_id': project['project_id'], 'manifest_digest': manifest['manifest_digest'],
                       'delivery_input_digest': vp.digest(source_inputs), 'output_ref': spec['output_ref'],
                       'artifact': vp.binding(root, spec['output_ref']), 'technical': technical,
                       'compositions': compositions, 'playback_verified': False,
                       'ffmpeg_version': vp.run([vp.tool('ffmpeg'), '-version']).decode().splitlines()[0]}
            vp.write(receipt_path, receipt)
        except BaseException:
            target.unlink(missing_ok=True)
            raise
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project_directory', type=Path)
    args = parser.parse_args()
    try:
        result = finish(args.project_directory.resolve())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, TypeError, KeyError, OSError, vp.subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc), 'render_allowed': False}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
