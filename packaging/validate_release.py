"""Validate a complete release before publishing; keep existing updater names."""
import hashlib
from pathlib import Path
import re
import sys
import shutil
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from writewatch.release_assets import ASSETS, download_notes

SUFFIXES = tuple(ASSETS)


def prepare(folder, version, ref=''):
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Invalid release version')
    if ref.startswith('refs/tags/') and ref != 'refs/tags/v' + version:
        raise ValueError('Release tag does not match the application version')
    folder = Path(folder)
    expected = {f'WriteWatch-{version}-{suffix}' for suffix in SUFFIXES}
    aliases = {f'WriteWatch-{version}-{suffix}' for suffix in ASSETS.values()}
    actual = {p.name for p in folder.iterdir() if p.name != 'SHA256SUMS.txt'}
    if not expected <= actual or actual - expected - aliases:
        raise ValueError(f'Package set mismatch: missing={sorted(expected-actual)}, unexpected={sorted(actual-expected-aliases)}')
    hashes = {}
    for name in sorted(actual):
        path = folder / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f'Package is not a nonempty regular file: {name}')
        digest = hashlib.sha256()
        with path.open('rb') as source:
            for block in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(block)
        hashes[name] = digest.hexdigest()
    for old, new in ASSETS.items():
        source, alias = f'WriteWatch-{version}-{old}', f'WriteWatch-{version}-{new}'
        if alias in hashes and hashes[alias] != hashes[source]:
            raise ValueError('Compatibility alias differs from original package: ' + alias)
    for old, new in ASSETS.items():
        source, alias = f'WriteWatch-{version}-{old}', f'WriteWatch-{version}-{new}'
        if alias not in hashes:
            shutil.copyfile(folder / source, folder / alias)
            hashes[alias] = hashes[source]
    lines = [f'{digest}  {name}\n' for name, digest in sorted(hashes.items())]
    manifest = folder / 'SHA256SUMS.txt'
    if manifest.is_symlink():
        raise ValueError('Checksum manifest must not be a symlink')
    manifest.write_text(''.join(lines), encoding='utf-8')
    return manifest


if __name__ == '__main__':
    import os
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from writewatch import __version__
    prepare(sys.argv[1], __version__, os.environ.get('GITHUB_REF', ''))
    root = Path(__file__).resolve().parents[1]
    (root / 'release-notes.generated.md').write_text(download_notes(__version__, (root / 'RELEASE_NOTES.md').read_text(encoding='utf-8')), encoding='utf-8')
    print('Release package set and checksums: PASS')
