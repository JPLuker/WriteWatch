"""Run on the target OS. PyInstaller does not cross-compile."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import platform
import plistlib

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from writewatch.app import icon
from writewatch import __version__

app = QApplication([])
assets = ROOT / 'build' / 'assets'
assets.mkdir(parents=True, exist_ok=True)
image = icon().pixmap(256, 256)
image.save(str(assets / 'writewatch.png'))
image.save(str(assets / 'writewatch.ico'))
icon_path = assets / 'writewatch.ico'
if sys.platform == 'darwin':
    iconset = assets / 'writewatch.iconset'
    iconset.mkdir(exist_ok=True)
    for size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            suffix = '@2x' if scale == 2 else ''
            image.scaled(size * scale, size * scale).save(str(iconset / f'icon_{size}x{size}{suffix}.png'))
    icon_path = assets / 'writewatch.icns'
    subprocess.run(['iconutil', '-c', 'icns', str(iconset), '-o', str(icon_path)], check=True)
command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed',
           '--name', 'WriteWatch', '--icon', str(icon_path), '--collect-data', 'defusedxml', '--collect-data', 'writewatch']
if sys.platform == 'darwin':
    command += ['--osx-bundle-identifier', 'com.jpluker.writewatch', '--target-arch', platform.machine()]
subprocess.run(command + ['main.py'], check=True)
resources = ROOT / 'dist' / ('WriteWatch.app/Contents/Resources' if sys.platform == 'darwin' else 'WriteWatch')
for filename in ('README.md', 'PRIVACY.md', 'THIRD_PARTY_NOTICES.md'):
    shutil.copy(filename, resources / filename)
# Preserve wheel license notices alongside dynamically loaded Qt libraries.
import importlib.metadata
licenses = resources / 'licenses'
for name in ('PySide6', 'PySide6_Essentials', 'PySide6_Addons', 'shiboken6', 'defusedxml', 'striprtf', 'markdown-it-py', 'mdurl', 'pypdf', 'certifi'):
    dist = importlib.metadata.distribution(name)
    for file in dist.files or []:
        if any(part.lower() in ('licenses', 'license', 'copying') for part in file.parts) or 'license' in file.name.lower():
            source = Path(dist.locate_file(file))
            if source.is_file():
                target = licenses / name / str(file).replace('..', '_')
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(source, target)
if sys.platform == 'win32':
    shutil.make_archive(f'dist/WriteWatch-{__version__}-Windows-portable', 'zip', 'dist', 'WriteWatch')
elif sys.platform == 'darwin':
    bundle = ROOT / 'dist' / 'WriteWatch.app'
    info = bundle / 'Contents' / 'Info.plist'
    with info.open('rb') as handle:
        metadata = plistlib.load(handle)
    metadata.update(CFBundleShortVersionString=__version__, CFBundleVersion=__version__,
                    LSMinimumSystemVersion='15.0', NSHighResolutionCapable=True)
    with info.open('wb') as handle:
        plistlib.dump(metadata, handle)
    # Ad-hoc signing makes the bundle internally valid; this is NOT Developer ID
    # signing or notarization. Gatekeeper will still require user approval.
    subprocess.run(['codesign', '--force', '--deep', '--sign', '-', str(bundle)], check=True)
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(bundle)], check=True)
    architecture = 'AppleSilicon' if platform.machine() == 'arm64' else 'Intel'
    base = f'WriteWatch-{__version__}-macOS-{architecture}'
    subprocess.run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(bundle),
                    str(ROOT / 'dist' / (base + '.zip'))], check=True)
    staging = ROOT / 'build' / 'dmg-content'
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()
    subprocess.run(['ditto', str(bundle), str(staging / 'WriteWatch.app')], check=True)
    (staging / 'Applications').symlink_to('/Applications')
    shutil.copy('packaging/MAC_INSTALL.md', staging / 'READ ME FIRST.txt')
    subprocess.run(['hdiutil', 'create', '-volname', 'WriteWatch', '-srcfolder', str(staging),
                    '-ov', '-format', 'UDZO', str(ROOT / 'dist' / (base + '.dmg'))], check=True)
else:
    shutil.make_archive(f'dist/WriteWatch-{__version__}-Linux-x86_64' , 'gztar', 'dist', 'WriteWatch')
