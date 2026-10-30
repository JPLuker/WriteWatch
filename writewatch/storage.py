"""Platform storage, copy-first migration and bounded updater-file retention."""
from contextlib import closing
from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import tempfile
import time

from .protection import safe_directory, regular_unlinked, matches, remove_file

APP_ID = 'io.github.jpluker.writewatch'
RETENTION = 14 * 86400
LOG_LIMIT = 10 * 1024 * 1024


@dataclass(frozen=True)
class Storage:
    data: Path
    cache: Path
    logs: Path
    legacy: Path | None = None

    @classmethod
    def local(cls, folder):
        folder = Path(folder)
        return cls(folder, folder / 'updates', folder / 'logs')


def locations(legacy, env=None, platform=None, home=None):
    env = os.environ if env is None else env
    platform = sys.platform if platform is None else platform
    home = Path.home() if home is None else Path(home)
    if env.get('WRITEWATCH_DATA_DIR'):
        return Storage.local(Path(env['WRITEWATCH_DATA_DIR']).expanduser().absolute())
    if platform == 'win32' and getattr(sys, 'frozen', False):
        portable = Path(sys.executable).parent
        if (portable / 'WriteWatch.portable').is_file():
            return Storage.local(portable / 'data')
    def base(key, fallback):
        path = Path(env.get(key) or fallback)
        return path if path.is_absolute() else Path(fallback)
    if platform == 'win32':
        data = base('APPDATA', home / 'AppData/Roaming') / APP_ID
        local = base('LOCALAPPDATA', home / 'AppData/Local') / APP_ID
        result = Storage(data, local / 'cache', local / 'logs', Path(legacy))
    elif platform == 'darwin':
        result = Storage(home / 'Library/Application Support' / APP_ID,
                         home / 'Library/Caches' / APP_ID, home / 'Library/Logs' / APP_ID, Path(legacy))
    else:
        result = Storage(base('XDG_DATA_HOME', home / '.local/share') / 'writewatch',
                         base('XDG_CACHE_HOME', home / '.cache') / 'writewatch',
                         base('XDG_STATE_HOME', home / '.local/state') / 'writewatch/logs', Path(legacy))
    return result if result.data != result.legacy else Storage(result.data, result.cache, result.logs)


def migrate(storage):
    """Caller holds both old/new single-instance locks. Never overwrite new data.

    Copy settings first and history last. A failed attempt can resume safely;
    original files remain available for recovery until Delete all app data.
    """
    old = storage.legacy
    target = storage.data
    if old is None or not safe_directory(old) or (target / 'history.sqlite3').exists():
        return False
    target.mkdir(parents=True, exist_ok=True)
    if not safe_directory(target):
        raise ValueError('App storage must not be a linked folder.')
    sources = [old / n for n in ('appearance.ini', 'updates.ini', 'recents.ini', 'metrics.ini')]
    sources += [p for p in old.glob('history.sqlite3.backup-v*') if re.fullmatch(r'history\.sqlite3\.backup-v\d+(?:-[a-f0-9]+)?', p.name)]
    for source in sources:
        dest = target / source.name
        if regular_unlinked(source) and not os.path.lexists(dest):
            fd, name = tempfile.mkstemp(prefix='.migration-', dir=target)
            os.close(fd)
            try:
                shutil.copyfile(source, name)
                os.link(name, dest)
            finally:
                Path(name).unlink(missing_ok=True)
    source = old / 'history.sqlite3'
    if not regular_unlinked(source):
        return False
    fd, name = tempfile.mkstemp(prefix='.migration-', dir=target)
    os.close(fd)
    try:
        with closing(sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True)) as original:
            with closing(sqlite3.connect(name)) as copy:
                original.backup(copy)
                if copy.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                    raise ValueError('History integrity check failed.')
        os.link(name, target / 'history.sqlite3')
    finally:
        Path(name).unlink(missing_ok=True)
    return True


def owned_artifact(path, logs=False):
    log = bool(re.fullmatch(r'last-update(?:-[A-Za-z0-9_-]+)?\.log', path.name))
    cache = bool(re.fullmatch(
        r'(?:WriteWatch-\d+\.\d+\.\d+-[A-Za-z0-9_-]+\.(?:exe|AppImage|zip|deb|tar\.gz)(?:\.part)?|apply-[a-f0-9]+\.(?:sh|ps1)|download-[a-f0-9]+\.part)', path.name))
    return log or (not logs and cache)


def clear_artifacts(folder, logs=False, protected=()):
    folder = Path(folder)
    if not safe_directory(folder):
        return
    for path in folder.iterdir():
        if owned_artifact(path, logs):
            remove_file(path, protected)
    # Only an empty directory may be removed. User-created contents stay put.
    try:
        folder.rmdir()
    except OSError:
        pass


def cleanup(storage, now=None, protected=()):
    """Nonrecursive age/budget cleanup with the same protections as manual clear."""
    now = time.time() if now is None else now
    folders = [(storage.cache, False), (storage.logs, True)]
    if storage.legacy:
        folders.append((storage.legacy / 'updates', False))
    remaining = []
    for folder, logs in folders:
        if not safe_directory(folder):
            continue
        try:
            entries = list(folder.iterdir())
        except OSError:
            continue
        for path in entries:
            try:
                if not regular_unlinked(path) or matches(path, protected) or not owned_artifact(path, logs):
                    continue
                info = path.stat()
                if now - info.st_mtime > RETENTION:
                    remove_file(path, protected)
                elif path.suffix == '.log':
                    remaining.append((info.st_mtime, info.st_size, path))
            except OSError:
                continue
    total = sum(size for _, size, _ in remaining)
    for modified, size, path in sorted(remaining):
        if total <= LOG_LIMIT:
            break
        if now - modified < 60:
            continue
        try:
            if remove_file(path, protected):
                total -= size
        except OSError:
            pass
