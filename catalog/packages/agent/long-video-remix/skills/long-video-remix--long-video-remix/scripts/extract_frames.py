#!/usr/bin/env python3
"""Extract frames and timing signals whose labels are MEASURED source time.

One tool for Broad sampling, Detail reading and edit-point search:

  frames   sample a source range at N fps; each frame is the first decoded
           frame at or after its sampling slot, labelled with its real pts.
  strip    every decoded frame inside a short bracket (edit-point search).
  signals  no images: a frame-difference (motion) curve, motion segments,
           hard-cut candidates, and silence / speech segments from the audio.

Labels are never computed as "start + index / fps": every label is read from
ffmpeg showinfo / metadata output, so variable-frame-rate sources and sparse
sampling cannot shift a label away from the picture it names.

Usage:
  extract_frames.py PROJECT SOURCE_ID START_MS-END_MS --mode frames --fps 1
  extract_frames.py PROJECT SOURCE_ID START_MS-END_MS --mode strip
  extract_frames.py PROJECT SOURCE_ID START_MS-END_MS --mode signals

Only sources with time_mapping.type=identity are accepted: canonical source_ms
must equal media time. Proxies or offsets need an explicit adapter first.
"""
import argparse
import json
import math
import re
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

from execution_integrity import source_signature, time_mapping_digest

INDEX_NAME = 'frames.jsonl'
SIGNALS_NAME = 'signals.json'
OUTPUT_MARKER = '.extract_frames.json'
SHOWINFO = re.compile(r'\bn:\s*(\d+)\s+pts:\s*(-?\d+)\s+pts_time:\s*(-?[\d.]+)')
META_FRAME = re.compile(r'\bframe:\s*(\d+)\s+pts:\s*(-?\d+)\s+pts_time:\s*(-?[\d.]+)')
META_YAVG = re.compile(r'lavfi\.signalstats\.YAVG=([\d.]+)')
META_YMAX = re.compile(r'lavfi\.signalstats\.YMAX=([\d.]+)')
SILENCE_START = re.compile(r'silence_start:\s*(-?[\d.]+)')
SILENCE_END = re.compile(r'silence_end:\s*(-?[\d.]+)')


class ExtractError(Exception):
    pass


def parse_range(text):
    match = re.fullmatch(r'\s*(\d+)\s*-\s*(\d+)\s*', text or '')
    if not match:
        raise ExtractError('range must be START_MS-END_MS in integer source milliseconds')
    start, end = int(match.group(1)), int(match.group(2))
    if end <= start:
        raise ExtractError('range end must be greater than start')
    return start, end


def resolve_source(root, source_id):
    sources = json.loads((root / 'sources.json').read_text(encoding='utf-8'))
    matches = [s for s in sources if isinstance(s, dict) and s.get('source_id') == source_id]
    if len(matches) != 1:
        raise ExtractError('source_id %s not found exactly once in sources.json' % source_id)
    source = matches[0]
    mapping = source.get('time_mapping')
    if not isinstance(mapping, dict) or mapping.get('type') != 'identity':
        raise ExtractError('extract_frames refuses non-identity time_mapping for %s: canonical source_ms must '
                           'equal media time; map proxies/offsets with an explicit adapter first' % source_id)
    locator = source.get('locator')
    if not isinstance(locator, str) or not locator.strip():
        raise ExtractError('%s has no locator' % source_id)
    if '://' in locator or locator.lower().startswith(('connector:', 'mcp:')):
        raise ExtractError('%s locator is not a local file; extract through its adapter' % source_id)
    path = Path(locator)
    if not path.is_absolute():
        path = root / path
    if not path.is_file():
        raise ExtractError('%s media file not found: %s' % (source_id, path))
    return source, path


def record_outputs(path):
    files = sorted(p.name for p in path.iterdir() if p.is_file() and p.name != OUTPUT_MARKER)
    (path / OUTPUT_MARKER).write_text(json.dumps({'tool': 'extract_frames', 'files': files}) + '\n',
                                     encoding='utf-8')


def prepare_out_dir(path, protected=()):
    """Replace tracked tool files only; refuse project/source ancestors and foreign content."""
    if any(path == p.resolve() or path in p.resolve().parents for p in protected):
        raise ExtractError('output directory must not be the project root or contain a source file; '
                           'choose another --out')
    if path.exists():
        entries = list(path.iterdir())
        try:
            marker = json.loads((path / OUTPUT_MARKER).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            marker = {}
        files = marker.get('files') if isinstance(marker, dict) else None
        ours = (isinstance(marker, dict) and marker.get('tool') == 'extract_frames'
                and isinstance(files, list) and all(isinstance(n, str) and Path(n).name == n
                    and (n in (INDEX_NAME, SIGNALS_NAME, 'motion.csv') or n.endswith('.jpg')) for n in files))
        foreign = {p.name for p in entries} - (set(files) | {OUTPUT_MARKER}) if ours else set()
        if entries and (not ours or foreign or any((path / n).is_dir() for n in files)):
            raise ExtractError('output directory %s is not empty and was not written by extract_frames; '
                               'choose another --out' % path)
        for name in files or []:
            (path / name).unlink(missing_ok=True)
    path.mkdir(parents=True, exist_ok=True)
    record_outputs(path)


def run_ffmpeg(args):
    proc = subprocess.run(['ffmpeg', '-hide_banner', '-nostdin', '-nostats', '-y'] + args,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors='replace')
    if proc.returncode != 0:
        raise ExtractError('ffmpeg failed: %s' % proc.stderr.strip()[-800:])
    return proc.stderr


def run_vfr(seek_args, filter_graph, out_pattern, extra=()):
    """Run a variable-frame-rate image extraction; fall back to -vsync on old ffmpeg."""
    base = seek_args + ['-map', '0:v:0', '-vf', filter_graph]
    tail = list(extra) + ['-q:v', '2', str(out_pattern)]
    try:
        return run_ffmpeg(base + ['-fps_mode', 'vfr'] + tail)
    except ExtractError as exc:
        if 'fps_mode' not in str(exc):
            raise
        return run_ffmpeg(base + ['-vsync', 'vfr'] + tail)


def label_frames(out_dir, source_id, start_ms, stderr, meta):
    produced = sorted(out_dir.glob('tmp_*.jpg'))
    shown = [float(m.group(3)) for m in SHOWINFO.finditer(stderr)]
    if len(shown) != len(produced):
        raise ExtractError('measured %d timestamps for %d images; refusing to guess labels'
                           % (len(shown), len(produced)))
    records, used = [], set()
    for path, pts_time in zip(produced, shown):
        source_ms = start_ms + int(round(pts_time * 1000.0))
        name = '%s_%012d.jpg' % (source_id, source_ms)
        suffix = 1
        while name in used:  # only possible for >1000 fps sources
            name = '%s_%012d_%d.jpg' % (source_id, source_ms, suffix)
            suffix += 1
        used.add(name)
        path.rename(out_dir / name)
        record = dict(meta, source_ms=source_ms, file=name, label_method='measured_pts')
        records.append(record)
    return records


def write_sheets(out_dir, records, cols, rows, cell_width):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return [], 'Pillow not installed; contact sheets skipped'
    sheets, per = [], cols * rows
    for number, offset in enumerate(range(0, len(records), per), start=1):
        batch = records[offset:offset + per]
        thumbs = []
        for rec in batch:
            img = Image.open(out_dir / rec['file']).convert('RGB')
            height = max(1, int(img.height * cell_width / float(img.width)))
            thumbs.append((img.resize((cell_width, height)), rec['source_ms']))
        cell_h = max(t[0].height for t in thumbs) + 16
        sheet = Image.new('RGB', (cols * cell_width, rows * cell_h), (24, 24, 24))
        draw = ImageDraw.Draw(sheet)
        for i, (thumb, ms) in enumerate(thumbs):
            x, y = (i % cols) * cell_width, (i // cols) * cell_h
            sheet.paste(thumb, (x, y))
            draw.text((x + 4, y + thumb.height + 2), '%.3fs' % (ms / 1000.0), fill=(255, 255, 255))
        name = 'sheet_%03d.jpg' % number
        sheet.save(out_dir / name, quality=90)
        sheets.append(name)
    return sheets, None


def extract_images(args, root, source, media, start, end):
    duration = (end - start) / 1000.0
    # -ss and -t are INPUT options: the decoder stops at the range end, so every frame the
    # filters see (and showinfo measures) is a frame that is written.
    seek = ['-ss', '%.3f' % (start / 1000.0), '-t', '%.3f' % duration, '-i', str(media)]
    if args.mode == 'frames':
        # First decoded frame in each 1/fps bucket: the picture is never earlier than its slot
        # and the label is the frame's own measured pts, not the slot.
        rate = repr(float(args.fps))
        graph = ("select='isnan(prev_t)+gt(floor(t*%s+1e-9)\\,floor(prev_t*%s+1e-9))',showinfo"
                 % (rate, rate))
        stderr = run_vfr(seek, graph, args.out_dir / 'tmp_%06d.jpg')
    else:
        stderr = run_vfr(seek, 'showinfo', args.out_dir / 'tmp_%06d.jpg',
                         extra=['-frames:v', str(args.max_frames + 1)])
        if len(list(args.out_dir.glob('tmp_*.jpg'))) > args.max_frames:
            for path in args.out_dir.glob('tmp_*.jpg'):
                path.unlink()
            raise ExtractError('strip bracket holds more than --max-frames %d frames; narrow it '
                               '(a strip is for a short bracket around one edit point)' % args.max_frames)
    meta = {'source_id': source['source_id'], 'mode': args.mode,
            'sampling_fps': args.fps if args.mode == 'frames' else None,
            'source_signature': source_signature(source), 'time_mapping_digest': time_mapping_digest(source)}
    records = label_frames(args.out_dir, source['source_id'], start, stderr, meta)
    if args.mode == 'frames':
        step = 1000.0 / args.fps
        for rec in records:
            slot = start + int(((rec['source_ms'] - start) // step) * step)
            rec['slot_ms'] = slot
        filled = {r['slot_ms'] for r in records}
        empty_slots = [start + int(k * step) for k in range(int(duration * args.fps) + 1)
                       if start + int(k * step) < end and start + int(k * step) not in filled]
    else:
        empty_slots = []
    with (args.out_dir / INDEX_NAME).open('w', encoding='utf-8') as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
    sheets, sheet_note = [], None
    if args.sheet:
        cols, rows = args.sheet
        sheets, sheet_note = write_sheets(args.out_dir, records, cols, rows, args.cell_width)
    result = {'status': 'ok', 'mode': args.mode, 'source_id': source['source_id'],
              'range_ms': [start, end], 'frames': len(records), 'output_dir': str(args.out_dir),
              'index': str(args.out_dir / INDEX_NAME), 'first_ms': records[0]['source_ms'] if records else None,
              'last_ms': records[-1]['source_ms'] if records else None, 'sheets': sheets,
              'label_method': 'measured_pts'}
    if empty_slots:
        result['empty_slots_ms'] = empty_slots
        result['note'] = 'some sampling slots contain no decoded frame (variable frame rate / gaps)'
    if sheet_note:
        result['sheet_note'] = sheet_note
    return result


def merge_segments(times, gap_ms, frame_ms):
    segments = []
    for t in times:
        if segments and t - segments[-1][1] <= gap_ms:
            segments[-1][1] = t
        else:
            segments.append([max(0, t - frame_ms), t])
    return segments


def has_audio(media):
    proc = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=index',
                           '-of', 'csv=p=0', str(media)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.returncode == 0 and bool(proc.stdout.strip())


def extract_signals(args, source, media, start, end):
    duration = (end - start) / 1000.0
    # -ss and -t are INPUT options: the decoder stops at the range end, so every frame the
    # filters see (and showinfo measures) is a frame that is written.
    seek = ['-ss', '%.3f' % (start / 1000.0), '-t', '%.3f' % duration, '-i', str(media)]
    # Frame difference -> 16x9 block averages. YMAX (largest block change) catches a small
    # moving hand or object that a whole-frame mean would dilute; YAVG (whole-frame mean)
    # flags hard cuts. metadata=print writes to the log, which avoids path escaping.
    stderr = run_ffmpeg(seek + ['-map', '0:v:0', '-vf',
                                'scale=160:-2,format=yuv420p,tblend=all_mode=difference,'
                                'scale=16:9:flags=area,signalstats,metadata=print', '-f', 'null', '-'])
    curve, current, row = [], None, {}
    for line in stderr.splitlines():
        frame = META_FRAME.search(line)
        if frame:
            if current is not None and 'max' in row:
                curve.append((current, row['max'], row.get('avg', 0.0)))
            current, row = start + int(round(float(frame.group(3)) * 1000.0)), {}
            continue
        value = META_YMAX.search(line)
        if value:
            row['max'] = float(value.group(1))
        value = META_YAVG.search(line)
        if value:
            row['avg'] = float(value.group(1))
    if current is not None and 'max' in row:
        curve.append((current, row['max'], row.get('avg', 0.0)))
    with (args.out_dir / 'motion.csv').open('w', encoding='utf-8') as fh:
        fh.write('source_ms,local_change,global_change\n')
        for ms, local, whole in curve:
            fh.write('%d,%.3f,%.3f\n' % (ms, local, whole))
    values = [v for _, v, _ in curve]
    if values:
        median = statistics.median(values)
        mad = statistics.median([abs(v - median) for v in values])
        threshold = args.motion_threshold if args.motion_threshold is not None else max(6.0, median + 6 * mad)
    else:
        threshold = args.motion_threshold if args.motion_threshold is not None else 6.0
    deltas = [b[0] - a[0] for a, b in zip(curve, curve[1:])]
    frame_ms = int(statistics.median(deltas)) if deltas else 40
    moving = [ms for ms, v, _ in curve if v >= threshold]
    motion = merge_segments(moving, args.merge_gap_ms, frame_ms)
    cuts = [ms for ms, _, whole in curve if whole >= args.cut_threshold]

    silences, speech, audio_present = [], [], has_audio(media)
    if audio_present:
        stderr = run_ffmpeg(seek + ['-map', '0:a:0', '-af', 'silencedetect=noise=%sdB:d=%.3f'
                                    % (args.silence_db, args.silence_min_ms / 1000.0), '-f', 'null', '-'])
        open_start = None
        for line in stderr.splitlines():
            s = SILENCE_START.search(line)
            e = SILENCE_END.search(line)
            if s:
                open_start = max(start, start + int(round(float(s.group(1)) * 1000.0)))
            if e and open_start is not None:
                silences.append([open_start, min(end, start + int(round(float(e.group(1)) * 1000.0)))])
                open_start = None
        if open_start is not None:
            silences.append([open_start, end])
        cursor = start
        for a, b in silences:
            if a > cursor:
                speech.append([cursor, a])
            cursor = max(cursor, b)
        if cursor < end:
            speech.append([cursor, end])
    signals = {
        'source_id': source['source_id'], 'range_ms': [start, end], 'label_method': 'measured_pts',
        'source_signature': source_signature(source), 'time_mapping_digest': time_mapping_digest(source),
        'motion_threshold': round(threshold, 4), 'motion_segments_ms': motion, 'cut_candidates_ms': cuts,
        'audio_present': audio_present, 'silence_segments_ms': silences, 'sound_segments_ms': speech,
        'note': 'candidates for where to look and where edges may sit; confirm with frames, strips or listening',
    }
    (args.out_dir / SIGNALS_NAME).write_text(json.dumps(signals, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return dict(signals, status='ok', mode='signals', output_dir=str(args.out_dir))


def parse_sheet(text):
    if text in (None, '', 'none'):
        return None
    match = re.fullmatch(r'(\d+)x(\d+)', text)
    if not match or int(match.group(1)) < 1 or int(match.group(2)) < 1:
        raise ExtractError('--sheet must look like 4x5 or none')
    return int(match.group(1)), int(match.group(2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('project', type=Path)
    parser.add_argument('source_id')
    parser.add_argument('range', help='START_MS-END_MS in canonical source milliseconds')
    parser.add_argument('--mode', choices=('frames', 'strip', 'signals'), required=True)
    parser.add_argument('--fps', type=float, help='frames mode sampling density, e.g. 0.5, 1, 4')
    parser.add_argument('--out', type=Path, help='output directory (default under PROJECT/analysis/frames)')
    parser.add_argument('--sheet', default=None, help='contact sheet grid such as 4x5; default 4x5 for frames, '
                                                      '6x4 for strip; none to skip')
    parser.add_argument('--cell-width', type=int, default=320)
    parser.add_argument('--max-frames', type=int, default=240)
    parser.add_argument('--motion-threshold', type=float, default=None,
                        help='local-change threshold (0-255 block difference); default adapts to the '
                             'range with a floor of 6 - calibrate per source')
    parser.add_argument('--cut-threshold', type=float, default=30.0)
    parser.add_argument('--merge-gap-ms', type=int, default=300)
    parser.add_argument('--silence-db', type=float, default=-35.0)
    parser.add_argument('--silence-min-ms', type=int, default=300)
    args = parser.parse_args(argv)
    try:
        root = args.project.resolve()
        start, end = parse_range(args.range)
        if shutil.which('ffmpeg') is None or shutil.which('ffprobe') is None:
            raise ExtractError('ffmpeg and ffprobe are required on PATH')
        source, media = resolve_source(root, args.source_id)
        duration = source.get('duration_ms')
        if isinstance(duration, int) and end > duration:
            raise ExtractError('range ends after source duration_ms %d' % duration)
        if args.mode == 'frames':
            if args.fps is None or not math.isfinite(args.fps) or args.fps <= 0:
                raise ExtractError('frames mode requires --fps > 0 and finite')
            expected = int((end - start) / 1000.0 * args.fps) + 1
            if expected > args.max_frames:
                raise ExtractError('frames mode would produce about %d images (> --max-frames %d); '
                                   'narrow the range or lower --fps' % (expected, args.max_frames))
        default_sheet = {'frames': '4x5', 'strip': '6x4', 'signals': 'none'}[args.mode]
        args.sheet = parse_sheet(args.sheet if args.sheet is not None else default_sheet)
        if args.out is None:
            tag = '%s_%d-%d' % (args.mode, start, end)
            if args.mode == 'frames':
                tag += '_fps%s' % ('%g' % args.fps if args.fps else 'x')
            args.out = root / 'analysis' / 'frames' / args.source_id / tag
        args.out_dir = args.out.resolve()
        prepare_out_dir(args.out_dir, (root, media))
        try:
            if args.mode == 'signals':
                result = extract_signals(args, source, media, start, end)
            else:
                result = extract_images(args, root, source, media, start, end)
        finally:
            record_outputs(args.out_dir)
    except (ExtractError, OSError, ValueError) as exc:
        print('extract_frames: %s' % exc, file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
