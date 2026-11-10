#!/usr/bin/env python3
"""Blender-side bounded 2D compositor; run via blender --background --python.

The layer mode is intentionally limited. Unsupported treatments remain pending
or use an explicitly authored native_blend scene; never silently simplify them.
"""
import argparse
import json
import math
from pathlib import Path
import sys

PROPERTIES = ('x', 'y', 'scale', 'rotation', 'opacity')
DEFAULTS = {'x': 0.0, 'y': 0.0, 'scale': 1.0, 'rotation': 0.0, 'opacity': 1.0}
EASINGS = ('linear', 'smoothstep', 'ease_in', 'ease_out', 'hold')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sample(defaults, keys, frame):
    """Bounded interpolation, no Bezier overshoot or last-frame reset."""
    result = dict(DEFAULTS)
    require(isinstance(defaults, dict) and set(defaults).issubset(PROPERTIES), 'Unknown transform property')
    result.update(defaults)
    require(isinstance(keys, list), 'Keyframes must be a list')
    for key in keys:
        require(isinstance(key, dict) and type(key.get('frame')) is int and key['frame'] >= 0,
                'Keyframes use nonnegative integer local frames')
        require(key.get('easing', 'linear') in EASINGS, 'Unsupported easing')
        require(isinstance(key.get('values'), dict) and set(key['values']).issubset(PROPERTIES), 'Unsupported animated property')
    require(len({key['frame'] for key in keys}) == len(keys), 'Duplicate keyframe time')
    for prop in PROPERTIES:
        points = [{'frame': 0, 'value': result[prop], 'easing': 'linear'}]
        for key in sorted(keys, key=lambda item: item['frame']):
            if prop in key['values']:
                point = {'frame': key['frame'], 'value': key['values'][prop], 'easing': key.get('easing', 'linear')}
                if point['frame'] == 0:
                    points[0] = point
                else:
                    points.append(point)
        require(all(type(p['value']) in (int, float) and math.isfinite(p['value']) for p in points), 'Nonfinite transform value')
        result[prop] = points[-1]['value']
        for left, right in zip(points, points[1:]):
            if frame < right['frame']:
                amount = max(0.0, min(1.0, (frame - left['frame']) / (right['frame'] - left['frame'])))
                easing = right['easing']
                if easing == 'smoothstep':
                    amount = amount * amount * (3 - 2 * amount)
                elif easing == 'ease_in':
                    amount *= amount
                elif easing == 'ease_out':
                    amount = 1 - (1 - amount) ** 2
                elif easing == 'hold':
                    amount = 0
                result[prop] = left['value'] + amount * (right['value'] - left['value'])
                break
    require(result['scale'] > 0 and 0 <= result['opacity'] <= 1, 'Scale/opacity out of range')
    return result


def world_pose(layer, groups, frame, active=None):
    pose = sample(layer.get('transform', {}), layer.get('keyframes', []), frame)
    parent = layer.get('parent')
    if not parent:
        return pose
    active = set() if active is None else set(active)
    require(parent in groups and parent not in active, 'Missing or cyclic parent group')
    active.add(parent)
    group = world_pose(groups[parent], groups, frame, active)
    angle = math.radians(group['rotation'])
    x, y = pose['x'] * group['scale'], pose['y'] * group['scale']
    pose.update(x=group['x'] + math.cos(angle) * x - math.sin(angle) * y,
                y=group['y'] + math.sin(angle) * x + math.cos(angle) * y,
                scale=pose['scale'] * group['scale'],
                rotation=pose['rotation'] + group['rotation'],
                opacity=pose['opacity'] * group['opacity'])
    return pose


def keyframe(owner, prop, frame):
    owner.keyframe_insert(data_path=prop, frame=frame)


def build_layers(bpy, scene, payload):
    job, profile = payload['job'], payload['output']
    groups = job.get('groups', {})
    require(isinstance(groups, dict), 'Groups must be named transform objects')
    layers = job['layers']
    require(0 < len(layers) <= 64, 'Layer mode supports 1..64 layers per short composition')
    editor = scene.sequence_editor_create()
    collection = getattr(editor, 'strips', None)
    if collection is None:
        collection = editor.sequences
    strips, ids = [], set()
    root = Path(payload['project_root'])
    for index, layer in enumerate(layers):
        lid = layer.get('layer_id')
        require(isinstance(lid, str) and lid and lid not in ids, 'Unique layer_id required')
        ids.add(lid)
        start, end = layer.get('start_frame'), layer.get('end_frame')
        require(type(start) is int and type(end) is int and 0 <= start < end <= job['frame_count'], 'Layer interval out of composition')
        require(all(key['frame'] < job['frame_count'] for key in layer.get('keyframes', [])), 'Keyframe outside composition')
        kind, first = layer.get('kind'), start + 1
        channel = index + 1
        fit = 1.0
        if kind in ('image', 'video'):
            path = str((root / layer['asset_ref']).resolve())
            if kind == 'image':
                strip = collection.new_image(lid, path, channel=channel, frame_start=first)
                strip.frame_final_end = end + 1
            else:
                offset = layer.get('source_in_frame', 0)
                require(type(offset) is int and offset >= 0, 'source_in_frame must be nonnegative')
                strip = collection.new_movie(lid, path, channel=channel, frame_start=first - offset)
                strip.frame_offset_start = offset
                require(strip.frame_final_duration >= end - start, 'Video source is shorter than the selected interval')
                strip.frame_final_end = end + 1
            dimensions = payload['asset_dimensions'][layer['asset_ref']]
            ratios = [profile['width'] / dimensions[0], profile['height'] / dimensions[1]]
            require(layer.get('fit', 'cover') in ('cover', 'contain', 'native'), 'Unsupported fit mode')
            fit = {'cover': max(ratios), 'contain': min(ratios), 'native': 1.0}[layer.get('fit', 'cover')]
        elif kind in ('color', 'text'):
            strip = collection.new_effect(lid, type='COLOR' if kind == 'color' else 'TEXT',
                                          channel=channel, frame_start=first, frame_end=end + 1)
            if kind == 'color':
                strip.color = layer.get('color', [0, 0, 0])
            else:
                require(isinstance(layer.get('text'), str) and layer['text'], 'Actual text is required')
                strip.text = layer['text']
                strip.font_size = layer.get('font_size', 48)
                strip.color = layer.get('color', [1, 1, 1, 1])
                strip.location = (0.5, 0.5)
                if hasattr(strip, 'alignment_x'):
                    strip.alignment_x = 'CENTER'
                else:
                    strip.align_x = 'CENTER'
                for anchor in ('anchor_x', 'anchor_y'):
                    if hasattr(strip, anchor):
                        setattr(strip, anchor, 'CENTER')
                if layer.get('font_ref'):
                    strip.font = bpy.data.fonts.load(str(root / layer['font_ref']))
        else:
            raise ValueError('Unsupported layer kind; use a reviewed native_blend engineering scene: ' + str(kind))
        strip.blend_type = 'ALPHA_OVER'
        strip.mute = False
        # Curves are sampled to actual frame values. Blender need not infer an
        # easing implementation and changing the cut cannot reset the final pose.
        for frame in range(start, end):
            scene.frame_set(frame + 1)
            pose = world_pose(layer, groups, frame)
            strip.transform.offset_x = pose['x']
            strip.transform.offset_y = pose['y']
            strip.transform.scale_x = strip.transform.scale_y = fit * pose['scale']
            strip.transform.rotation = math.radians(pose['rotation'])
            strip.blend_alpha = pose['opacity']
            for prop in ('offset_x', 'offset_y', 'scale_x', 'scale_y', 'rotation'):
                keyframe(strip.transform, prop, frame + 1)
            keyframe(strip, 'blend_alpha', frame + 1)
        strips.append((layer, strip, fit))
    return strips


def check_native_dependencies(bpy, scene, payload):
    allowed = {str((Path(payload['project_root']) / ref).resolve()) for ref in payload['job'].get('native_dependency_refs', [])}
    paths = []
    for image in bpy.data.images:
        if image.source in ('FILE', 'MOVIE', 'SEQUENCE') and not image.packed_file:
            paths.append(bpy.path.abspath(image.filepath))
    editor = scene.sequence_editor
    if editor:
        for strip in getattr(editor, 'strips_all', getattr(editor, 'sequences_all', [])):
            if strip.type in ('MOVIE', 'SOUND'):
                paths.append(bpy.path.abspath(strip.filepath))
            elif strip.type == 'IMAGE':
                paths.extend(str(Path(bpy.path.abspath(strip.directory)) / element.filename) for element in strip.elements)
    for font in bpy.data.fonts:
        if font.filepath and font.filepath != '<builtin>' and not font.packed_file:
            paths.append(bpy.path.abspath(font.filepath))
    for collection_name in ('libraries', 'sounds', 'movieclips', 'cache_files', 'volumes'):
        for resource in getattr(bpy.data, collection_name, []):
            if getattr(resource, 'filepath', '') and not getattr(resource, 'packed_file', None):
                paths.append(bpy.path.abspath(resource.filepath))
    require(all(str(Path(path).resolve()) in allowed for path in paths),
            'Declare every external native-scene media/font file in native_dependency_refs')


def render(payload):
    import bpy
    job, profile = payload['job'], payload['output']
    require(0 < job['frame_count'] <= 3600, 'This compositor renders short scopes of at most 3600 frames')
    if job.get('mode', 'layers') == 'native_blend':
        bpy.ops.wm.open_mainfile(filepath=str(Path(payload['project_root']) / job['native_scene_ref']), load_ui=False, use_scripts=False)
        scene = bpy.context.scene
        check_native_dependencies(bpy, scene, payload)
        strips = []
        first = job.get('native_start_frame', scene.frame_start)
        require(type(first) is int and first >= 0, 'Invalid native_start_frame')
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene = bpy.context.scene
        first = 1
        scene.render.use_sequencer = True
        scene.render.use_compositing = False
        scene.render.film_transparent = True
        scene.view_settings.view_transform = 'Standard'
        scene.view_settings.exposure = 0
        scene.view_settings.gamma = 1
        strips = build_layers(bpy, scene, payload)
    scene.render.resolution_x, scene.render.resolution_y = profile['width'], profile['height']
    scene.render.resolution_percentage = 100
    scene.render.fps = profile['fps_num']
    scene.render.fps_base = profile['fps_den']
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.frame_start, scene.frame_end = first, first + job['frame_count'] - 1
    scene.render.filepath = str(Path(payload['frames_directory']) / 'frame_######')
    scene.render.use_file_extension = True
    samples = sorted({0, job['frame_count'] - 1, *[x for join in job['joins'] for x in (join['frame'] - 1, join['frame'], join['frame'] + 1)
                                                   if 0 <= x < job['frame_count']]})
    readback = {'backend': 'blender', 'backend_version': bpy.app.version_string,
                'mode': job.get('mode', 'layers'), 'first_native_frame': first,
                'frame_count': job['frame_count'], 'output': profile, 'samples': []}
    for frame in samples:
        scene.frame_set(first + frame)
        state = {'local_frame': frame, 'layers': []}
        for layer, strip, fit in strips:
            if not layer['start_frame'] <= frame < layer['end_frame']:
                continue
            pose = world_pose(layer, job.get('groups', {}), frame)
            actual = {'x': float(strip.transform.offset_x), 'y': float(strip.transform.offset_y),
                      'scale': float(strip.transform.scale_x) / fit,
                      'rotation': math.degrees(float(strip.transform.rotation)), 'opacity': float(strip.blend_alpha)}
            require(all(abs(actual[key] - pose[key]) < 0.002 for key in PROPERTIES), 'Native keyframe readback differs from the declared pose')
            state['layers'].append({'layer_id': layer['layer_id'], 'actual': actual, 'expected': pose})
        readback['samples'].append(state)
    scene.frame_set(first)
    bpy.ops.render.render(animation=True)
    # The delivered engineering file uses paths relative to its final folder,
    # rather than to the temporary render directory that will be removed.
    destination = payload['scene_final_parent']
    for image in bpy.data.images:
        if image.filepath and image.source in ('FILE', 'MOVIE', 'SEQUENCE'):
            image.filepath = bpy.path.relpath(bpy.path.abspath(image.filepath), start=destination)
    for font in bpy.data.fonts:
        if font.filepath and font.filepath != '<builtin>':
            font.filepath = bpy.path.relpath(bpy.path.abspath(font.filepath), start=destination)
    if scene.sequence_editor:
        editor = scene.sequence_editor
        for strip in getattr(editor, 'strips_all', getattr(editor, 'sequences_all', [])):
            if strip.type in ('MOVIE', 'SOUND'):
                strip.filepath = bpy.path.relpath(bpy.path.abspath(strip.filepath), start=destination)
            elif strip.type == 'IMAGE':
                strip.directory = bpy.path.relpath(bpy.path.abspath(strip.directory), start=destination)
    scene.render.filepath = '//rerender/frame_'
    bpy.ops.wm.save_as_mainfile(filepath=payload['scene_output'], relative_remap=False)
    Path(payload['readback_output']).write_text(json.dumps(readback, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('payload', type=Path)
    parsed = parser.parse_args(args)
    render(json.loads(parsed.payload.read_text(encoding='utf-8')))


if __name__ == '__main__':
    main()
