#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
version=$(python -c 'from writewatch import __version__; print(__version__)')
appdir=build/WriteWatch.AppDir
rm -rf "$appdir"
mkdir -p "$appdir/usr"
cp -a dist/WriteWatch "$appdir/usr/WriteWatch"
cp build/assets/writewatch.png "$appdir/writewatch.png"
cat > "$appdir/AppRun" <<'LAUNCH'
#!/bin/sh
APPDIR=$(dirname "$(readlink -f "$0")")
exec "$APPDIR/usr/WriteWatch/WriteWatch" "$@"
LAUNCH
chmod +x "$appdir/AppRun"
cat > "$appdir/writewatch.desktop" <<'DESKTOP'
[Desktop Entry]
Name=WriteWatch
Exec=WriteWatch
Icon=writewatch
Type=Application
Categories=Office;
Comment=Private writing sessions and shareable progress
DESKTOP
curl --fail --location --retry 3 https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-x86_64.AppImage -o build/appimagetool
chmod +x build/appimagetool
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 build/appimagetool "$appdir" "dist/WriteWatch-${version}-x86_64.AppImage"
