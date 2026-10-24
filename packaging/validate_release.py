"""Validate a complete release before publishing; keep existing updater names."""
import hashlib
from pathlib import Path
import re
import sys

SUFFIXES = (
    'Windows-portable.zip', 'Windows-Setup.exe',
    'Linux-x86_64.tar.gz', 'x86_64.AppImage', 'amd64.deb',
    'macOS-AppleSilicon.dmg', 'macOS-AppleSilicon.zip',
    'macOS-Intel.dmg', 'macOS-Intel.zip',
)


def prepare(folder, version, ref=''):
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Invalid release version')
    if ref.startswith('refs/tags/') and ref != 'refs/tags/v' + version:
        raise ValueError('Release tag does not match the application version')
    folder = Path(folder)
    expected = {f'WriteWatch-{version}-{suffix}' for suffix in SUFFIXES}
    actual = {p.name for p in folder.iterdir() if p.name != 'SHA256SUMS.txt'}
    if actual != expected:
        raise ValueError(f'Package set mismatch: missing={sorted(expected-actual)}, unexpected={sorted(actual-expected)}')
    lines = []
    for name in sorted(expected):
        path = folder / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f'Package is not a nonempty regular file: {name}')
        digest = hashlib.sha256()
        with path.open('rb') as source:
            for block in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(block)
        lines.append(f'{digest.hexdigest()}  {name}\n')
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
    print('Release package set and checksums: PASS')
