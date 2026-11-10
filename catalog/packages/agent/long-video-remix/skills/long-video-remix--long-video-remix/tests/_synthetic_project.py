"""Prepare synthetic project data without shipping media or changing the package catalog."""
from pathlib import Path
import shutil
from unittest.mock import patch

import visual_pipeline as vp

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_REFERENCE = 'SYN-REF-01'
REFERENCE_PACKAGE_REL = vp.REFERENCE_PACKAGE.relative_to(ROOT)


def copy_synthetic_ready(root):
    """Keep the synthetic snapshot hashes stable by recreating its three test assets."""
    shutil.copytree(ROOT / 'examples/synthetic-ready', root, dirs_exist_ok=True)
    (root / 'keyframe.svg').write_bytes(b'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180"><rect width="320" height="180" fill="#ddd"/><rect x="26" y="24" width="268" height="132" rx="10" fill="#bbb"/><text x="160" y="94" text-anchor="middle" font-family="sans-serif" font-size="16">synthetic keyframe F001</text></svg>\n')
    (root / 'mockup.svg').write_bytes(b'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180"><rect width="320" height="180" fill="#111"/><rect x="188" y="20" width="108" height="140" rx="12" fill="#d8d8d8"/><text x="24" y="76" font-family="sans-serif" font-size="19" font-weight="700" fill="white">Synthetic</text><text x="24" y="102" font-family="sans-serif" font-size="19" font-weight="700" fill="white">proof style</text><text x="24" y="130" font-family="sans-serif" font-size="10" fill="#ccc">aesthetic mockup</text></svg>\n')
    (root / 'proof.svg').write_bytes(b'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180"><rect width="320" height="180" fill="#111"/><rect x="188" y="20" width="108" height="140" rx="12" fill="#d8d8d8"/><text x="24" y="76" font-family="sans-serif" font-size="19" font-weight="700" fill="white">Synthetic</text><text x="24" y="102" font-family="sans-serif" font-size="19" font-weight="700" fill="white">proof style</text><text x="24" y="130" font-family="sans-serif" font-size="10" fill="#aaa">executable proof</text></svg>\n')


def install_test_catalog(test, package):
    """Supply a real synthetic image and manifest to the unchanged validators."""
    from PIL import Image

    bundled = ROOT / REFERENCE_PACKAGE_REL
    reference = package / REFERENCE_PACKAGE_REL
    shutil.copytree(bundled / 'manifests', reference / 'manifests')
    image_path = reference / 'synthetic-reference.png'
    Image.new('RGB', (64, 36), (27, 57, 87)).save(image_path)
    manifest = reference / 'manifests' / 'reference-assets.json'
    data = vp.read(manifest)
    data.update(image_count=1, assets=[{
        'asset_id': SYNTHETIC_REFERENCE,
        'local_path': image_path.name,
        'sha256': vp.sha(image_path),
        'transfer_principle': 'Use visual separation to protect the subject area.',
        'do_not_copy': 'Rebuild the layout for the current project.',
    }])
    vp.write(manifest, data)
    patcher = patch.multiple(
        vp, PACKAGE_ROOT=package, REFERENCE_PACKAGE=reference,
        REFERENCE_MANIFEST=manifest, LEGACY_REFERENCE_MANIFEST=manifest,
        STRUCTURE_CARD_MANIFEST=reference / 'manifests' / 'reference-structure-cards.json',
        EXTERNAL_REFERENCE_MANIFEST=reference / 'manifests' / 'external-references.json',
    )
    patcher.start()
    test.addCleanup(patcher.stop)
