import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import visual_pipeline as vp
PKG = ROOT / 'visual-reference' / 'visual-reference-package-v2.4.3'


class VisualReferenceTests(unittest.TestCase):
    def test_embedded_reference_checksum_manifest_matches_current_files(self):
        checksum_file = PKG / 'SHA256SUMS'
        listed = {}
        for line in checksum_file.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            digest, rel = line.split('  ', 1)
            listed[rel] = digest
        actual_files = {str(p.relative_to(PKG)) for p in PKG.rglob('*') if p.is_file() and p.name != 'SHA256SUMS' and '__pycache__' not in p.parts and p.suffix != '.pyc'}
        self.assertEqual(set(listed), actual_files)
        for rel, digest in listed.items():
            actual = hashlib.sha256((PKG / rel).read_bytes()).hexdigest()
            self.assertEqual(digest, actual, rel)

    def test_new_project_template_uses_v236_visual_stage_without_duplicate_reference_routing(self):
        project = json.loads((ROOT / 'assets' / 'project-template.json').read_text(encoding='utf-8'))
        self.assertEqual(project['visual_pipeline']['visual_stage_dir'], 'visual')
        method = json.loads((ROOT / 'assets' / 'visual-methods-template.json').read_text(encoding='utf-8'))['methods'][0]
        self.assertIn('visual_stage_problem_refs', method)
        self.assertNotIn('visual_reference_status', method)
        self.assertNotIn('visual_reference_refs', method)
        lock = json.loads((ROOT / 'assets' / 'implementation-lock-template.json').read_text(encoding='utf-8'))
        self.assertIn('visual_stage_binding', lock)
        self.assertIn('confirmed_mockups', lock)
        self.assertEqual(lock['reference_trace'], [])

    def test_public_catalog_starts_empty(self):
        self.assertEqual(vp.visual_reference_catalog(), {})
        for path, key in ((vp.STRUCTURE_CARD_MANIFEST, 'cards'),
                          (vp.EXTERNAL_REFERENCE_MANIFEST, 'references')):
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))[key], [])

    def test_host_stage_report_consumes_v236_checker_statuses(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            vdir = root / 'visual'
            vdir.mkdir()
            for stage in vp.VISUAL_STAGE_ORDER[:3]:
                (vdir / (stage + '.json')).write_text('{}\n', encoding='utf-8')
            project = {'visual_pipeline': {'visual_stage_dir': 'visual'}}
            lines = []
            for i, stage in enumerate(vp.VISUAL_STAGE_ORDER):
                status = 'PASS' if i < 3 else 'MISSING'
                lines.append(f'{stage:<24} {status}')
            fake = subprocess.CompletedProcess([], 0, stdout='\n'.join(lines) + '\n', stderr='')
            with mock.patch.object(vp.subprocess, 'run', return_value=fake):
                report = vp.visual_stage_report(root, project, 'V2-reference-selection')
            self.assertEqual(report['statuses']['V2-reference-selection'], 'PASS')
            self.assertEqual(set(report['artifacts']), set(vp.VISUAL_STAGE_ORDER[:3]))

    def test_v6_confirmed_artifacts_bind_all_chosen_mockups_before_v7(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            vdir = root / 'visual'
            (vdir / 'mockups').mkdir(parents=True)
            a1 = vdir / 'mockups' / 'A_M01.png'
            a2 = vdir / 'mockups' / 'A_M02.png'
            b1 = vdir / 'mockups' / 'B_M01.png'
            for path, payload in ((a1,b'a1'),(a2,b'a2'),(b1,b'b1')):
                path.write_bytes(payload)
            def h(path):
                return hashlib.sha256(path.read_bytes()).hexdigest()
            v6 = {
                'stage': 'V6', 'status': 'confirmed', 'chosen_candidate': 'A',
                'confirmed_artifacts': [
                    {'file':'mockups/A_M01.png','sha256':h(a1),'candidate':'A'},
                    {'file':'mockups/A_M02.png','sha256':h(a2),'candidate':'A'},
                    {'file':'mockups/B_M01.png','sha256':h(b1),'candidate':'B'},
                ]
            }
            (vdir / 'V6-user-decision.json').write_text(json.dumps(v6), encoding='utf-8')
            project = {'visual_pipeline': {'visual_stage_dir': 'visual'}}
            report = {'dir':'visual', 'artifacts': {'V6-user-decision': {'ref':'visual/V6-user-decision.json','sha256':h(vdir/'V6-user-decision.json')}}}
            with mock.patch.object(vp, 'visual_stage_report', return_value=report) as stage:
                bound = vp.confirmed_visual_artifacts(root, project)
            stage.assert_called_once_with(root, project, 'V6-user-decision')
            self.assertEqual([x['ref'] for x in bound], ['visual/mockups/A_M01.png','visual/mockups/A_M02.png'])


    def test_visual_direction_intelligence_is_packaged_and_non_gating(self):
        atlas = json.loads((PKG / 'manifests' / 'visual-direction-atlas.json').read_text(encoding='utf-8'))
        self.assertTrue(atlas['not_a_gate'])
        self.assertEqual([x['id'] for x in atlas['directions']], [f'VD-{i:02d}' for i in range(1, 8)])
        for name in ('visual-direction-atlas.md', 'scene-text-grammar.md', 'timing-grammar.md'):
            self.assertTrue((PKG / 'references' / name).is_file())
        v3 = json.loads((PKG / 'templates' / 'visual-stage' / 'V3-candidates.json').read_text(encoding='utf-8'))
        self.assertIn('direction_read', v3)
        v1 = json.loads((PKG / 'templates' / 'visual-stage' / 'V1-visual-problems.json').read_text(encoding='utf-8'))
        v2 = json.loads((PKG / 'templates' / 'visual-stage' / 'V2-reference-selection.json').read_text(encoding='utf-8'))
        self.assertIn('direction_hypothesis', v1)
        self.assertEqual(v1['direction_hypothesis']['analysis_order'], 'after_visual_problem_before_reference')
        self.assertIn('direction_context', v2)
        self.assertIn('direction_strategy', v3['candidates'][0])
        self.assertIn('direction_use', v3['candidates'][0]['per_shot'][0])
        brief = (PKG / 'scripts' / 'art_direction_brief.py').read_text(encoding='utf-8')
        self.assertIn('visual-direction-atlas.md', brief)
        self.assertIn('direction_read', brief)
        self.assertIn('direction_hypothesis', brief)

    def test_router_points_to_v236_procedure(self):
        text = (ROOT / 'references' / 'visual-reference-router.md').read_text(encoding='utf-8')
        self.assertIn('V0 → V7', text)
        self.assertIn('visual-design-procedure.md', text)
        self.assertIn('visual_stage_binding', text)


if __name__ == '__main__':
    unittest.main()
