import hashlib
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ChecksumTests(unittest.TestCase):
    def test_project_fallback_files_are_packaged_and_current(self):
        required = {
            name: 'v1.5.1-public-methodology-clean'
            for name in ('SKILL.md', 'PROJECT_INSTRUCTIONS.txt',
                         'CHAT_PROJECT_REFERENCE.md', 'INSTALL.md', 'INSTALL.en.md',
                         'README.md', 'README.en.md')
        }
        for name, version in required.items():
            path = ROOT / name
            self.assertTrue(path.is_file(), f'missing project fallback file: {name}')
            self.assertIn(version, path.read_text(encoding='utf-8')[:1400], name)

    def test_project_reference_embeds_current_operating_sources(self):
        text = (ROOT / 'CHAT_PROJECT_REFERENCE.md').read_text(encoding='utf-8')
        sections = re.split(r'^## FILE: `([^`]+)`\n\n', text, flags=re.M)
        embedded = dict(zip(sections[1::2], sections[2::2]))
        self.assertEqual(len(embedded), 26)
        self.assertIn('references/visual-reference-router.md', embedded)
        self.assertIn('visual-reference/visual-reference-package-v2.4.3/references/visual-design-procedure.md', embedded)
        for name, content in embedded.items():
            with self.subTest(source=name):
                self.assertEqual(content.removesuffix('\n\n---\n\n').rstrip(),
                                 (ROOT / name).read_text(encoding='utf-8').rstrip())

    def test_unused_release_history_is_not_packaged(self):
        lib = ROOT / 'visual-reference/visual-reference-package-v2.4.3'
        absent = [ROOT / 'CHANGELOG.md', ROOT / 'RELEASE_NOTES.md', ROOT / 'docs/qa',
                  ROOT / 'visual-reference/runtime-source-v1.4.11',
                  ROOT / 'visual-reference/upstream-v2.4.3',
                  ROOT / 'visual-reference/library-integration.json',
                  lib / 'QA-v2.3.6.md', lib / 'RELEASE_NOTES_v2.3.6.md',
                  lib / 'TEST_RESULTS_v2.3.6.txt', lib / 'manifests/build-audit.json',
                  lib / 'manifests/visual-qa.json', lib / 'manifests/release-manifest-v2.3.6.json']
        absent.extend((lib / 'manifests').glob('package-verification*.json'))
        for path in absent:
            self.assertFalse(path.exists(), str(path.relative_to(ROOT)))

    def test_public_package_contains_no_media_assets(self):
        media = {'.svg', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif', '.ico',
                 '.mp4', '.mov', '.mkv', '.webm', '.wav', '.mp3', '.blend',
                 '.otf', '.ttf', '.woff', '.woff2'}
        names = (line.split('  ', 1)[1] for line in
                 (ROOT / 'SHA256SUMS').read_text(encoding='utf-8').splitlines())
        self.assertEqual([name for name in names if Path(name).suffix.lower() in media], [])

    def test_sha256sums_entries_exist_and_match(self):
        expected = {}
        for line in (ROOT / 'SHA256SUMS').read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            digest, name = line.split('  ', 1)
            expected[name] = digest
        self.assertTrue(expected, 'SHA256SUMS must list packaged files')
        for name, digest in expected.items():
            path = ROOT / name
            self.assertTrue(path.is_file(), f'missing packaged file: {name}')
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, actual, name)
