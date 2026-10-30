"""Local JSON backups of aggregate statistics and preferences, never documents."""
from dataclasses import asdict, fields
from datetime import datetime
import json
import math
import os
from pathlib import Path
import re

from .protection import write_new, remove_file, safe_directory
from .core import Session
from .metrics import default_preferences, validate_preferences

MAX_BACKUP = 32 * 1024 * 1024
PREFS = {'theme', 'ambient', 'remember', 'recents', 'automatic_updates'}


def validate(payload):
    if not isinstance(payload, dict) or set(payload) != {'format', 'version', 'sessions', 'settings'}:
        raise ValueError('Not a WriteWatch backup.')
    if payload['format'] != 'WriteWatch' or type(payload['version']) is not int or payload['version'] not in (1, 2, 3):
        raise ValueError('Unsupported backup version.')
    rows, prefs = payload['sessions'], payload['settings']
    if not isinstance(rows, list) or len(rows) > 100000 or not isinstance(prefs, dict) or set(prefs) != (PREFS | ({'update_channel'} if payload['version'] >= 2 else set()) | ({'metrics'} if payload['version'] == 3 else set())):
        raise ValueError('Invalid backup structure.')
    if payload['version'] >= 2 and prefs['update_channel'] not in ('Stable', 'Testing'):
        raise ValueError('Invalid update channel.')
    if payload['version'] == 3:
        validate_preferences(prefs['metrics'])
    if prefs['theme'] not in ('System', 'Light', 'Dark'):
        raise ValueError('Invalid theme.')
    for key in ('ambient', 'remember', 'automatic_updates'):
        if type(prefs[key]) is not bool:
            raise ValueError('Invalid preference.')
    if not isinstance(prefs['recents'], list) or len(prefs['recents']) > 10 or any(
            not isinstance(p, str) or len(p) > 32768 or '\x00' in p for p in prefs['recents']):
        raise ValueError('Invalid recent files.')
    sessions, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {f.name for f in fields(Session)}:
            raise ValueError('Invalid session fields.')
        if not isinstance(row['id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', row['id']) or row['id'] in seen:
            raise ValueError('Invalid or duplicate session ID.')
        seen.add(row['id'])
        if not isinstance(row['started'], str) or len(row['started']) > 64:
            raise ValueError('Invalid date.')
        try:
            stamp = datetime.fromisoformat(row['started'])
            if stamp.tzinfo is None:
                raise ValueError()
        except ValueError:
            raise ValueError('Invalid date.') from None
        if row['mode'] not in ('Writing', 'Revision') or row['status'] not in ('done', 'interrupted'):
            raise ValueError('Invalid session state.')
        if row['goal_unit'] not in ('', 'words', 'minutes', 'pages', 'estimated_pages'):
            raise ValueError('Invalid goal unit.')
        for key in ('goal', 'net', 'saves', 'words_per_page', 'added', 'removed'):
            lower = -10**12 if key == 'net' else 1 if key == 'words_per_page' else 0
            upper = 100000 if key == 'goal' else 2000 if key == 'words_per_page' else 10**12
            if type(row[key]) is not int or not lower <= row[key] <= upper:
                raise ValueError('Invalid count.')
        for key in ('seconds', 'pages'):
            if type(row[key]) not in (int, float) or not 0 <= row[key] <= 10**12 or not math.isfinite(row[key]):
                raise ValueError('Invalid measurement.')
        if type(row['revision_metrics']) is not bool or (row['revision_metrics'] and row['added'] - row['removed'] != row['net']):
            raise ValueError('Invalid revision totals.')
        sessions.append(Session(**row))
    return sessions, prefs


def backup_payload(store, preferences):
    rows = [dict(asdict(s), revision_metrics=bool(s.revision_metrics)) for s in store.history()]
    payload = {'format': 'WriteWatch', 'version': 3, 'sessions': rows, 'settings': dict(preferences, update_channel=preferences.get('update_channel', 'Stable'), metrics=preferences.get('metrics', default_preferences()))}
    validate(payload)
    return payload


def write_backup(path, payload):
    validate(payload)
    data = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8')
    if len(data) > MAX_BACKUP:
        raise ValueError('Backup exceeds 32 MB.')
    write_new(path, data)


def read_backup(path):
    with Path(path).open('rb') as source:
        data = source.read(MAX_BACKUP + 1)
    if len(data) > MAX_BACKUP:
        raise ValueError('Backup exceeds 32 MB.')
    try:
        payload = json.loads(data)
        validate(payload)
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        raise ValueError('Invalid or unsupported backup.') from None
    return payload


def merge_sessions(store, payload):
    sessions, _ = validate(payload)  # Validate everything before opening a transaction.
    added = 0
    with store.db:
        for session in sessions:
            row = asdict(session)
            cursor = store.db.execute('INSERT INTO sessions (' + ','.join(row) + ') VALUES (' +
                                     ','.join(':' + k for k in row) + ') ON CONFLICT(id) DO NOTHING', row)
            added += cursor.rowcount
    return added


def clear_cache(folder, protected=()):
    from .storage import clear_artifacts
    clear_artifacts(Path(folder) / 'updates', protected=protected)
    clear_artifacts(Path(folder) / 'logs', logs=True, protected=protected)


def delete_owned_data(folder, protected=()):
    """Remove app files only; preserve links, documents and every nested folder."""
    folder = Path(folder)
    if not safe_directory(folder):
        return
    clear_cache(folder, protected)
    for name in ('appearance.ini', 'updates.ini', 'recents.ini', 'metrics.ini'):
        remove_file(folder / name, protected)
    for path in folder.glob('history.sqlite3.backup-v*'):
        if re.fullmatch(r'history\.sqlite3\.backup-v\d+(?:-[a-f0-9]+)?', path.name):
            remove_file(path, protected)
    for suffix in ('-wal', '-shm', '-journal', ''):
        remove_file(folder / ('history.sqlite3' + suffix), protected)
