"""Public-release updater. Never receives document or session data."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import ssl
import subprocess
import sys
import threading
import urllib.request
from urllib.parse import urlsplit
import uuid

import certifi
from PySide6.QtCore import QThread, Signal
from . import __version__

RELEASES = 'https://github.com/JPLuker/WriteWatch/releases'
API = 'https://api.github.com/repos/JPLuker/WriteWatch/releases?per_page=50'
MAX_DOWNLOAD = 600 * 1024 * 1024


def version(value):
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', value)
    return tuple(map(int, match.groups())) if match else None


@dataclass(frozen=True)
class Installation:
    kind: str
    target: Path
    suffix: str


def installation():
    if not getattr(sys, 'frozen', False):
        return None
    exe = Path(sys.executable).absolute()
    if sys.platform == 'win32':
        installed = (exe.parent / 'unins000.exe').is_file()
        return Installation('windows-setup' if installed else 'windows-portable', exe.parent,
                            'Windows-Setup.exe' if installed else 'Windows-portable.zip')
    if sys.platform == 'darwin':
        bundle = next((p for p in exe.parents if p.suffix == '.app'), None)
        if bundle and not str(bundle).startswith('/Volumes/') and 'AppTranslocation' not in str(bundle):
            arch = 'AppleSilicon' if platform.machine() == 'arm64' else 'Intel'
            return Installation('mac', bundle, f'macOS-{arch}.zip')
    if sys.platform.startswith('linux') and os.environ.get('APPIMAGE'):
        path = Path(os.environ['APPIMAGE']).absolute()
        if path.is_file() and path.suffix == '.AppImage' and platform.machine() == 'x86_64':
            return Installation('appimage', path, 'x86_64.AppImage')
    if sys.platform.startswith('linux') and exe == Path('/opt/writewatch/WriteWatch') and platform.machine() == 'x86_64':
        return Installation('deb', exe.parent, 'amd64.deb')
    return None


def select_release(releases, current, suffix):
    candidates = []
    for release in releases:
        number = version(release.get('tag_name', ''))
        if release.get('draft') or not number or number <= version(current):
            continue
        name = f"WriteWatch-{'.'.join(map(str, number))}-{suffix}"
        for asset in release.get('assets', []):
            if asset.get('name') != name or asset.get('state') != 'uploaded':
                continue
            url = asset.get('browser_download_url', '')
            expected = f"{RELEASES}/download/{release['tag_name']}/{name}"
            if url != expected:
                continue
            digest = asset.get('digest', '') or ''
            size = asset.get('size', 0)
            if not re.fullmatch(r'sha256:[a-f0-9]{64}', digest) or not isinstance(size, int) or not 0 < size <= MAX_DOWNLOAD:
                raise ValueError('The release is missing valid download verification metadata.')
            candidates.append((number, dict(asset, release_version='.'.join(map(str, number)))))
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


class TrustedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlsplit(newurl)
        if parsed.scheme != 'https' or parsed.hostname not in {
            'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'
        } or parsed.username or parsed.password or parsed.port not in (None, 443):
            raise ValueError('Unexpected update download redirect.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def opener():
    return urllib.request.build_opener(TrustedRedirect(), urllib.request.HTTPSHandler(
        context=ssl.create_default_context(cafile=certifi.where())))


def request(url):
    return urllib.request.Request(url, headers={'User-Agent': f'WriteWatch/{__version__}',
                                               'Accept': 'application/vnd.github+json' if url == API else 'application/octet-stream'})


def verify(path, asset):
    if path.stat().st_size != asset['size']:
        raise ValueError('Update size verification failed.')
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    if 'sha256:' + digest.hexdigest() != asset['digest']:
        raise ValueError('Update checksum verification failed.')


class UpdateWorker(QThread):
    status = Signal(str)
    progress = Signal(int, int)
    ready = Signal(object, object)
    available = Signal(object)
    failed = Signal(str)

    def __init__(self, install, folder, parent=None):
        super().__init__(parent)
        self.install, self.folder = install, folder
        self.cancel = threading.Event()

    def run(self):
        partial = None
        try:
            client = opener()
            self.status.emit('Checking GitHub releases…')
            with client.open(request(API), timeout=15) as response:
                raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                raise ValueError('Release response is too large.')
            asset = select_release(json.loads(raw), __version__, self.install.suffix)
            if self.cancel.is_set():
                return
            if not asset:
                self.status.emit('Up to date')
                return
            if self.install.kind == 'deb':
                self.available.emit(asset)
                return
            self.folder.mkdir(parents=True, exist_ok=True)
            destination = self.folder / asset['name']
            partial = destination.with_suffix(destination.suffix + '.part')
            count = 0
            with client.open(request(asset['browser_download_url']), timeout=15) as response, partial.open('wb') as output:
                while not self.cancel.is_set():
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    count += len(block)
                    if count > asset['size']:
                        raise ValueError('Download exceeds expected size.')
                    output.write(block)
                    self.progress.emit(count, asset["size"])
            if self.cancel.is_set():
                return
            verify(partial, asset)
            partial.replace(destination)
            self.ready.emit(destination, asset)
        except Exception as error:
            if not self.cancel.is_set():
                self.failed.emit(f'Update unavailable: {error}. You can try again later.')
        finally:
            if partial:
                try:
                    partial.unlink(missing_ok=True)
                except OSError:
                    pass


def psquote(value):
    return "'" + str(value).replace("'", "''") + "'"


def helper_script(install, payload, pid, token):
    """Wait for graceful exit; stage on the same volume and preserve a backup."""
    target = install.target
    backup = target.with_name(target.name + '.previous-' + token)
    stage = target.with_name(target.name + '.update-' + token)
    if install.kind.startswith('windows'):
        q = psquote
        script = f"""$ErrorActionPreference = 'Stop'
$old = Get-Process -Id {pid} -ErrorAction SilentlyContinue
if ($old) {{ if (-not $old.WaitForExit(120000)) {{ throw 'WriteWatch did not exit; update cancelled.' }} }}
"""
        if install.kind == 'windows-setup':
            # Inno handles rollback; custom flag restarts only for updater installs.
            args = f'/SILENT /SUPPRESSMSGBOXES /NORESTART /WRITEWATCHUPDATE=1 /DIR="{target}"'
            return script + f"$p = Start-Process -FilePath {q(payload)} -ArgumentList {q(args)} -PassThru -Wait\nif ($p.ExitCode -ne 0) {{ throw 'Installer failed.' }}\n"
        extract = payload.parent / ('extract-' + token)
        return script + f"""Expand-Archive -LiteralPath {q(payload)} -DestinationPath {q(extract)}
Move-Item -LiteralPath {q(extract / 'WriteWatch')} -Destination {q(stage)}
if (-not (Test-Path -LiteralPath {q(stage / 'WriteWatch.exe')})) {{ throw 'Executable missing.' }}
Move-Item -LiteralPath {q(target)} -Destination {q(backup)}
try {{
  Move-Item -LiteralPath {q(stage)} -Destination {q(target)}
  Start-Process -FilePath {q(target / 'WriteWatch.exe')}
}} catch {{
  if (Test-Path -LiteralPath {q(target)}) {{ Move-Item -LiteralPath {q(target)} -Destination {q(stage)} }}
  Move-Item -LiteralPath {q(backup)} -Destination {q(target)}
  throw
}}
"""
    q = lambda p: shlex.quote(str(p))
    script = f"""#!/bin/sh
set -eu
n=0
while kill -0 {pid} 2>/dev/null; do
  n=$((n + 1))
  [ "$n" -lt 120 ] || exit 1
  sleep 1
done
"""
    if install.kind == 'appimage':
        script += f'cp {q(payload)} {q(stage)}\nchmod +x {q(stage)}\n'
        launch = f'{q(target)} >/dev/null 2>&1 &'
    else:
        extract = payload.parent / ('extract-' + token)
        script += f'/usr/bin/ditto -x -k {q(payload)} {q(extract)}\n/usr/bin/codesign --verify --deep --strict {q(extract / "WriteWatch.app")}\n/usr/bin/ditto {q(extract / "WriteWatch.app")} {q(stage)}\n'
        launch = f'/usr/bin/open {q(target)}'
    script += f"""mv {q(target)} {q(backup)}
if ! mv {q(stage)} {q(target)}; then
  mv {q(backup)} {q(target)}
  exit 1
fi
{launch}
"""
    return script


def install_update(install, payload, asset):
    if install.kind == 'deb':
        raise ValueError('Install Debian updates using your system package installer.')
    verify(payload, asset)  # Verify again immediately before executing.
    if not os.access(install.target.parent, os.W_OK):
        raise ValueError('This installation folder is not writable. Move WriteWatch to a writable folder or install manually.')
    token = uuid.uuid4().hex[:12]
    windows = install.kind.startswith('windows')
    helper = payload.parent / ('apply-' + token + ('.ps1' if windows else '.sh'))
    helper.write_text(helper_script(install, payload, os.getpid(), token), encoding='utf-8-sig' if windows else 'utf-8')
    env = os.environ.copy()
    for key in ('LD_LIBRARY_PATH', 'DYLD_LIBRARY_PATH'):
        if key + '_ORIG' in env:
            env[key] = env[key + '_ORIG']
        else:
            env.pop(key, None)
    for key in ('APPIMAGE', 'APPDIR'):
        env.pop(key, None)
    env['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    if windows:
        command = [str(Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'),
                   '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(helper)]
        import ctypes
        ctypes.windll.kernel32.SetDllDirectoryW(None)
        options = {'creationflags': subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS}
    else:
        command, options = ['/bin/sh', str(helper)], {'start_new_session': True}
    with (payload.parent / 'last-update.log').open('wb') as log:
        subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                         cwd=str(payload.parent), env=env, **options)
