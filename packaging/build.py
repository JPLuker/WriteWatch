"""Run on the target OS. PyInstaller does not cross-compile."""
from pathlib import Path
import os
import shutil
import subprocess
import sys

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
subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed',
                '--name', 'WriteWatch', '--icon', str(assets / 'writewatch.ico'),
                '--collect-data', 'defusedxml', 'main.py'], check=True)
shutil.copy('README.md', 'dist/WriteWatch/README.md')
shutil.copy('PRIVACY.md', 'dist/WriteWatch/PRIVACY.md')
shutil.copy('THIRD_PARTY_NOTICES.md', 'dist/WriteWatch/THIRD_PARTY_NOTICES.md')
# Preserve wheel license notices alongside dynamically loaded Qt libraries.
import importlib.metadata
licenses = ROOT / 'dist' / 'WriteWatch' / 'licenses'
for name in ('PySide6', 'PySide6_Essentials', 'PySide6_Addons', 'shiboken6', 'defusedxml', 'striprtf', 'markdown-it-py', 'mdurl', 'pypdf'):
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
else:
    shutil.make_archive(f'dist/WriteWatch-{__version__}-Linux-x86_64', 'gztar', 'dist', 'WriteWatch')
