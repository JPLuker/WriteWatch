import hashlib
from pathlib import Path
import runpy
import tempfile
import unittest

MODULE = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'packaging/validate_release.py'))
prepare = MODULE['prepare']
SUFFIXES = MODULE['SUFFIXES']


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.files = [self.folder / ('WriteWatch-0.11.1-' + suffix) for suffix in SUFFIXES]
        for path in self.files:
            path.write_bytes(b'package fixture')

    def tearDown(self):
        self.temp.cleanup()

    def test_manifest_covers_every_package_and_is_repeatable(self):
        path = prepare(self.folder, '0.11.1', 'refs/tags/v0.11.1')
        before = path.read_bytes()
        lines = path.read_text().splitlines()
        self.assertEqual(len(lines), 9)
        self.assertEqual({line.split('  ')[1] for line in lines}, {p.name for p in self.files})
        self.assertTrue(all(line.startswith(hashlib.sha256(b'package fixture').hexdigest()) for line in lines))
        self.assertEqual(prepare(self.folder, '0.11.1').read_bytes(), before)

    def test_missing_package_blocks_publication(self):
        self.files[0].unlink()
        with self.assertRaisesRegex(ValueError, 'missing='):
            prepare(self.folder, '0.11.1')
        self.assertFalse((self.folder / 'SHA256SUMS.txt').exists())

    def test_extra_or_wrong_version_package_blocks_publication(self):
        (self.folder / 'WriteWatch-0.11.0-amd64.deb').write_bytes(b'old')
        with self.assertRaisesRegex(ValueError, 'unexpected='):
            prepare(self.folder, '0.11.1')

    def test_empty_package_blocks_publication(self):
        self.files[0].write_bytes(b'')
        with self.assertRaisesRegex(ValueError, 'nonempty'):
            prepare(self.folder, '0.11.1')

    def test_mismatched_tag_and_invalid_version_rejected(self):
        with self.assertRaisesRegex(ValueError, 'tag'):
            prepare(self.folder, '0.11.1', 'refs/tags/v0.11.0')
        with self.assertRaisesRegex(ValueError, 'version'):
            prepare(self.folder, '../unsafe')
