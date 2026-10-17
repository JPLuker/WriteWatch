"""Build a native amd64 Debian package from the Linux PyInstaller output."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from writewatch import __version__


def build():
    source = ROOT / 'dist/WriteWatch'
    if not (source / 'WriteWatch').is_file():
        raise RuntimeError('Run packaging/build.py on Linux first.')
    with tempfile.TemporaryDirectory(prefix='writewatch-deb-') as temporary:
        stage = Path(temporary)
        application = stage / 'opt/writewatch'
        application.parent.mkdir(parents=True)
        shutil.copytree(source, application, symlinks=True)
        (stage / 'DEBIAN').mkdir()
        size = sum(p.stat().st_size for p in application.rglob('*') if p.is_file() and not p.is_symlink()) // 1024
        (stage / 'DEBIAN/control').write_text(f'''Package: writewatch
Version: {__version__}
Section: editors
Priority: optional
Architecture: amd64
Maintainer: Joseph Luker <JPLuker@pm.me>
Installed-Size: {size}
Depends: libc6 (>= 2.39), libstdc++6, libegl1, libopengl0, libgl1, libdbus-1-3, libfontconfig1, libx11-6, libx11-xcb1, libxext6, libxrender1, libxkbcommon0, libxkbcommon-x11-0, libxcb1, libxcb-cursor0, libxcb-icccm4, libxcb-keysyms1, libxcb-shape0, libxcb-xinerama0, libxcb-randr0, libxcb-render-util0, libxcb-image0, libxcb-render0, libxcb-shm0, libxcb-sync1, libxcb-xfixes0, libxcb-xkb1
Homepage: https://github.com/JPLuker/WriteWatch
Description: Private writing sessions and shareable progress
 Track saved word-count changes and session goals locally.
 Script text is never included in history or shared summaries.
''', encoding='utf-8')
        binary = stage / 'usr/bin'
        binary.mkdir(parents=True)
        (binary / 'writewatch').write_text('#!/bin/sh\nexec /opt/writewatch/WriteWatch "$@"\n', encoding='utf-8')
        (binary / 'writewatch').chmod(0o755)
        desktop = stage / 'usr/share/applications'
        desktop.mkdir(parents=True)
        (desktop / 'writewatch.desktop').write_text('''[Desktop Entry]
Type=Application
Name=WriteWatch
Comment=Writing sessions and progress
Exec=writewatch
TryExec=writewatch
Icon=writewatch
Terminal=false
Categories=Office;
StartupWMClass=WriteWatch
''', encoding='utf-8')
        icons = stage / 'usr/share/icons/hicolor/256x256/apps'
        icons.mkdir(parents=True)
        shutil.copy(ROOT / 'build/assets/writewatch.png', icons / 'writewatch.png')
        # Deterministic, readable permissions; dpkg handles ownership without sudo.
        for path in stage.rglob('*'):
            if path.is_symlink():
                continue
            path.chmod(0o755 if path.is_dir() or os.access(path, os.X_OK) else 0o644)
        destination = ROOT / 'dist' / f'WriteWatch-{__version__}-amd64.deb'
        subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(stage), str(destination)], check=True)
        subprocess.run(['dpkg-deb', '--info', str(destination)], check=True)
        print(destination)


if __name__ == '__main__':
    build()
