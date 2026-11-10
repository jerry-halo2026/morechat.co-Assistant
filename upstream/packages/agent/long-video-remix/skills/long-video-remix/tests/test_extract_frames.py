"""extract_frames.py: every label must name the picture it is attached to.

Each synthetic source frame carries its own index as luminance, so a sampled JPEG
can be mapped back to the source frame it really came from. Comparing labels with
labels (or with "start + i / fps") would be tautological and would not catch the
half-interval offset that ffmpeg's default fps rounding produces.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
SCRIPT = PACKAGE / 'scripts' / 'extract_frames.py'

try:
    from PIL import Image, ImageStat
except Exception:  # pragma: no cover - optional dependency
    Image = ImageStat = None

FPS = 25
FRAME_MS = 40
HAVE_FFMPEG = bool(shutil.which('ffmpeg') and shutil.which('ffprobe'))


def ffmpeg(*args):
    proc = subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error'] + list(args),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise AssertionError(proc.stderr)


def luma(path):
    return ImageStat.Stat(Image.open(path).convert('L')).mean[0]


class _Project:
    def make(self, locator='source.mp4', mapping=None):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        source = {'source_id': 'SRC001', 'locator': locator, 'version': 'test', 'duration_ms': 20000,
                  'time_mapping': mapping or {'type': 'identity'}}
        (self.root / 'sources.json').write_text(json.dumps([source]), encoding='utf-8')

    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.root), 'SRC001'] + list(args),
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def ok(self, *args):
        proc = self.run_tool(*args)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)


@unittest.skipUnless(HAVE_FFMPEG and Image is not None, 'ffmpeg, ffprobe and Pillow required')
class MeasuredLabelTests(_Project, unittest.TestCase):
    def setUp(self):
        self.make()
        # Luminance = source frame index; lossless so the index survives encoding.
        ffmpeg('-f', 'lavfi', '-i', "nullsrc=s=160x90:r=%d:d=8,geq=lum='N':cb=128:cr=128,format=yuv420p" % FPS,
               '-c:v', 'libx264', '-crf', '0', '-g', '50', str(self.root / 'cfr.mp4'))
        ref = self.root / 'ref'; ref.mkdir()
        ffmpeg('-i', str(self.root / 'cfr.mp4'), '-q:v', '2', str(ref / 'f_%04d.jpg'))
        # Frames below index 16 are clipped to the same black level; leave them out of the table.
        self.table = [(luma(p), i * FRAME_MS) for i, p in enumerate(sorted(ref.glob('f_*.jpg'))) if i >= 16]

    def actual_ms(self, path):
        value = luma(path)
        return min(self.table, key=lambda item: abs(item[0] - value))[1]

    def assert_labels_match_pictures(self, result):
        records = [json.loads(x) for x in Path(result['index']).read_text(encoding='utf-8').splitlines()]
        self.assertTrue(records)
        checked = 0
        for rec in records:
            self.assertEqual(rec['label_method'], 'measured_pts')
            if rec['source_ms'] < 17 * FRAME_MS:
                continue
            self.assertEqual(self.actual_ms(Path(result['output_dir']) / rec['file']), rec['source_ms'], rec)
            checked += 1
        self.assertGreater(checked, 0)
        return records

    def test_frames_1fps_labels_match_picture(self):
        shutil.copy(self.root / 'cfr.mp4', self.root / 'source.mp4')
        result = self.ok('1000-6000', '--mode', 'frames', '--fps', '1')
        records = self.assert_labels_match_pictures(result)
        self.assertEqual([r['source_ms'] for r in records], [1000, 2000, 3000, 4000, 5000])

    def test_frames_4fps_picture_is_never_before_its_slot(self):
        shutil.copy(self.root / 'cfr.mp4', self.root / 'source.mp4')
        result = self.ok('2000-4000', '--mode', 'frames', '--fps', '4')
        for rec in self.assert_labels_match_pictures(result):
            self.assertGreaterEqual(rec['source_ms'], rec['slot_ms'])
            self.assertLess(rec['source_ms'] - rec['slot_ms'], FRAME_MS)

    def test_strip_returns_every_frame_with_its_own_time(self):
        shutil.copy(self.root / 'cfr.mp4', self.root / 'source.mp4')
        result = self.ok('1200-1600', '--mode', 'strip')
        records = self.assert_labels_match_pictures(result)
        self.assertEqual([r['source_ms'] for r in records], list(range(1200, 1600, FRAME_MS)))
        self.assertTrue(result['sheets'])

    def test_variable_frame_rate_labels_are_measured_not_computed(self):
        # Drop most frames between index 60 and 99: timestamps become irregular.
        ffmpeg('-i', str(self.root / 'cfr.mp4'), '-vf', "select='not(between(n,60,99))+not(mod(n,7))'",
               '-fps_mode', 'vfr', '-c:v', 'libx264', '-crf', '0', str(self.root / 'source.mp4'))
        result = self.ok('2000-4500', '--mode', 'frames', '--fps', '4')
        records = self.assert_labels_match_pictures(result)
        # At least one picture sits well after its slot: a computed label would be wrong there.
        self.assertTrue(any(r['source_ms'] - r['slot_ms'] > FRAME_MS for r in records), records)

    def test_strip_refuses_a_long_bracket(self):
        shutil.copy(self.root / 'cfr.mp4', self.root / 'source.mp4')
        proc = self.run_tool('0-8000', '--mode', 'strip', '--max-frames', '50')
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('narrow it', proc.stderr)


@unittest.skipUnless(HAVE_FFMPEG, 'ffmpeg and ffprobe required')
class SignalTests(_Project, unittest.TestCase):
    def setUp(self):
        self.make()
        # A small box moves only between 3 s and 5 s; a tone sounds only between 2 s and 4 s;
        # the picture cuts to black at 6 s.
        ffmpeg('-f', 'lavfi', '-i', 'color=c=gray:s=320x180:r=25:d=6',
               '-f', 'lavfi', '-i', 'color=c=white:s=40x40:r=25:d=6',
               '-f', 'lavfi', '-i', 'color=c=black:s=320x180:r=25:d=2',
               '-f', 'lavfi', '-i', "aevalsrc='if(between(t,2,4),0.5*sin(2*PI*440*t),0)':s=48000:d=8",
               '-filter_complex', "[0][1]overlay=x='if(between(t,3,5),(t-3)*120,-100)':y=70[a];[a][2]concat=n=2:v=1:a=0[v]",
               '-map', '[v]', '-map', '3:a', '-c:v', 'libx264', '-crf', '18', '-c:a', 'aac', '-shortest',
               str(self.root / 'source.mp4'))

    def test_motion_sound_and_cut_are_located_in_source_time(self):
        result = self.ok('0-8000', '--mode', 'signals')
        self.assertTrue(any(abs(a - 3000) <= 80 and abs(b - 5000) <= 80 for a, b in result['motion_segments_ms']),
                        result['motion_segments_ms'])
        self.assertTrue(any(abs(ms - 6000) <= 80 for ms in result['cut_candidates_ms']), result['cut_candidates_ms'])
        self.assertTrue(any(abs(a - 2000) <= 60 and abs(b - 4000) <= 60 for a, b in result['sound_segments_ms']),
                        result['sound_segments_ms'])
        self.assertTrue((Path(result['output_dir']) / 'motion.csv').is_file())


class SafetyTests(_Project, unittest.TestCase):
    def test_non_identity_mapping_is_refused(self):
        self.make(mapping={'type': 'offset', 'offset_ms': 500})
        (self.root / 'source.mp4').write_bytes(b'not used')
        proc = self.run_tool('0-1000', '--mode', 'frames', '--fps', '1')
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('non-identity time_mapping', proc.stderr)

    def test_remote_locator_is_refused(self):
        self.make(locator='https://example.com/video.mp4')
        proc = self.run_tool('0-1000', '--mode', 'frames', '--fps', '1')
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('not a local file', proc.stderr)

    @unittest.skipUnless(HAVE_FFMPEG, 'ffmpeg required')
    def test_foreign_output_directory_is_never_cleared(self):
        self.make()
        ffmpeg('-f', 'lavfi', '-i', 'testsrc=size=160x90:rate=10', '-t', '2', '-pix_fmt', 'yuv420p',
               str(self.root / 'source.mp4'))
        for index in ('none', 'frames.jsonl', 'signals.json'):
            with self.subTest(index=index):
                foreign = self.root / index; foreign.mkdir()
                (foreign / 'keep.txt').write_text('user file')
                if index != 'none':
                    (foreign / index).write_text('{}')
                proc = self.run_tool('0-1000', '--mode', 'frames', '--fps', '1', '--out', str(foreign))
                self.assertNotEqual(proc.returncode, 0)
                self.assertTrue((foreign / 'keep.txt').is_file())

    @unittest.skipUnless(HAVE_FFMPEG, 'ffmpeg required')
    def test_project_and_source_ancestors_are_protected(self):
        self.make()
        ffmpeg('-f', 'lavfi', '-i', 'color=s=160x90:r=10:d=2', str(self.root / 'source.mp4'))
        (self.root / 'frames.jsonl').write_text('{"frame_id":"F001"}\n')
        (self.root / 'project.json').write_text('{}')
        for out in (self.root, self.root.parent):
            proc = self.run_tool('0-1000', '--mode', 'frames', '--fps', '1', '--out', str(out))
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('project root or contain a source', proc.stderr)
        self.assertTrue((self.root / 'source.mp4').is_file())
        self.assertEqual((self.root / 'project.json').read_text(), '{}')
        self.assertIn('F001', (self.root / 'frames.jsonl').read_text())

    @unittest.skipUnless(HAVE_FFMPEG, 'ffmpeg required')
    def test_owned_outputs_can_be_replaced_without_deleting_foreign_content(self):
        self.make()
        ffmpeg('-f', 'lavfi', '-i', 'color=s=160x90:r=10:d=2', str(self.root / 'source.mp4'))
        result = self.ok('0-1000', '--mode', 'frames', '--fps', '1', '--sheet', 'none')
        out = Path(result['output_dir'])
        self.ok('1000-2000', '--mode', 'frames', '--fps', '1', '--out', str(out), '--sheet', 'none')
        self.assertFalse((out / 'SRC001_000000000000.jpg').exists())
        self.assertTrue((out / 'SRC001_000000001000.jpg').is_file())
        before = (out / 'frames.jsonl').read_bytes()
        proc = self.run_tool('0-1000', '--mode', 'frames', '--fps', 'nan', '--out', str(out))
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual((out / 'frames.jsonl').read_bytes(), before)
        (out / 'keep.txt').write_text('user file')
        proc = self.run_tool('0-1000', '--mode', 'frames', '--fps', '1', '--out', str(out))
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual((out / 'keep.txt').read_text(), 'user file')
        self.assertEqual((out / 'frames.jsonl').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
