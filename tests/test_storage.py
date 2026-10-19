from contextlib import closing
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from writewatch.storage import Storage, locations, migrate, cleanup, RETENTION, LOG_LIMIT, APP_ID
from writewatch.core import Store, Session


class StorageTests(unittest.TestCase):
    def test_platform_paths_and_explicit_override(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            linux = locations(root / 'legacy', env={'XDG_DATA_HOME': str(root / 'data'), 'XDG_CACHE_HOME': str(root / 'cache'), 'XDG_STATE_HOME': str(root / 'state')}, platform='linux', home=root)
            self.assertEqual(linux.data, root / 'data/writewatch')
            self.assertEqual(linux.cache, root / 'cache/writewatch')
            self.assertEqual(linux.logs, root / 'state/writewatch/logs')
            win = locations(root / 'legacy', env={'APPDATA': str(root / 'roaming'), 'LOCALAPPDATA': str(root / 'local')}, platform='win32', home=root)
            self.assertEqual(win.data, root / 'roaming' / APP_ID)
            self.assertEqual(win.cache, root / 'local' / APP_ID / 'cache')
            mac = locations(root / 'legacy', env={}, platform='darwin', home=root)
            self.assertEqual(mac.logs, root / 'Library/Logs' / APP_ID)
            override = locations(root / 'legacy', env={'WRITEWATCH_DATA_DIR': str(root / 'custom')}, platform='linux', home=root)
            self.assertEqual(override, Storage.local(root / 'custom'))
            self.assertIsNone(override.legacy)
            relative = locations(root / 'legacy', env={'XDG_DATA_HOME': 'relative'}, platform='linux', home=root)
            self.assertEqual(relative.data, root / '.local/share/writewatch')

    def test_portable_marker_selects_adjacent_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'WriteWatch.portable').touch()
            with patch('sys.frozen', True, create=True), patch('sys.executable', str(root / 'WriteWatch.exe')):
                self.assertEqual(locations(root / 'old', env={}, platform='win32', home=root), Storage.local(root / 'data'))

    def test_migration_captures_wal_and_keeps_original_without_overwriting_new(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old, new = root / 'old', root / 'new'
            old.mkdir()
            storage = Storage(new, root / 'cache', root / 'logs', old)
            store = Store(old / 'history.sqlite3')
            try:
                store.db.execute('PRAGMA journal_mode=WAL')
                session = Session.new('Revision', 12)
                session.status = 'done'
                store.save(session)
                (old / 'updates.ini').write_text('[General]\nchannel=Testing\n')
                self.assertTrue(migrate(storage))
                self.assertTrue((old / 'history.sqlite3').exists())
                self.assertEqual((new / 'updates.ini').read_text(), (old / 'updates.ini').read_text())
                with closing(sqlite3.connect(new / 'history.sqlite3')) as db:
                    self.assertEqual(db.execute('SELECT id FROM sessions').fetchone()[0], session.id)
                (new / 'updates.ini').write_text('new preference')
                self.assertFalse(migrate(storage))
                self.assertEqual((new / 'updates.ini').read_text(), 'new preference')
            finally:
                store.close()

    def test_failed_copy_keeps_source_and_retry_finishes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old = root / 'old'
            old.mkdir()
            store = Store(old / 'history.sqlite3')
            store.close()
            storage = Storage(root / 'new', root / 'cache', root / 'logs', old)
            with patch('writewatch.storage.os.replace', side_effect=OSError('full disk')):
                with self.assertRaises(OSError):
                    migrate(storage)
            self.assertTrue((old / 'history.sqlite3').exists())
            self.assertFalse((storage.data / 'history.sqlite3').exists())
            self.assertFalse(list(storage.data.glob('.migration-*')))
            self.assertTrue(migrate(storage))

    def test_retention_preserves_pending_and_unrelated_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            storage = Storage.local(root)
            storage.cache.mkdir()
            now = 2000000
            old = storage.cache / 'WriteWatch-0.9.0-x86_64.AppImage'
            pending = storage.cache / 'WriteWatch-0.10.0-x86_64.AppImage'
            document = storage.cache / 'my-script.txt'
            fresh = storage.cache / 'WriteWatch-0.11.0-x86_64.AppImage'
            for path in (old, pending, document, fresh):
                path.write_text('content')
                os.utime(path, (now - RETENTION - 1, now - RETENTION - 1))
            os.utime(fresh, (now, now))
            cleanup(storage, now=now, protected=[pending])
            self.assertFalse(old.exists())
            self.assertTrue(pending.exists())
            self.assertTrue(document.exists())
            self.assertTrue(fresh.exists())

    def test_log_budget_and_age_retention(self):
        with tempfile.TemporaryDirectory() as temporary:
            storage = Storage.local(temporary)
            storage.logs.mkdir()
            old = storage.logs / 'last-update-old.log'
            recent = storage.logs / 'last-update.log'
            expired = storage.logs / 'last-update-expired.log'
            old.write_bytes(b'x' * (LOG_LIMIT // 2 + 1))
            recent.write_bytes(b'x' * (LOG_LIMIT // 2))
            expired.write_text('expired')
            now = 2000000
            for path, age in ((old, 1000), (recent, 100), (expired, RETENTION + 1)):
                os.utime(path, (now-age, now-age))
            cleanup(storage, now=now)
            self.assertFalse(old.exists())
            self.assertFalse(expired.exists())
            self.assertTrue(recent.exists())

    def test_startup_refuses_migration_while_older_app_is_locked(self):
        from PySide6.QtCore import QLockFile
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old = root / 'old'
            old.mkdir()
            lock = QLockFile(str(old / 'writewatch.lock'))
            self.assertTrue(lock.tryLock(0))
            code = """
from pathlib import Path
import sys
from unittest.mock import patch
from writewatch.storage import Storage
from writewatch.app import main
root = Path(sys.argv[1])
with patch('writewatch.storage.locations', return_value=Storage(root/'new', root/'cache', root/'logs', root/'old')), patch('writewatch.app.QMessageBox.information'):
    sys.exit(main())
"""
            try:
                result = subprocess.run([sys.executable, '-c', code, str(root)], env=dict(os.environ, QT_QPA_PLATFORM='offscreen', WRITEWATCH_DISABLE_UPDATES='1'), capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertFalse((root / 'new/history.sqlite3').exists())
            finally:
                lock.unlock()

    def test_cleanup_unreadable_directory_is_nonfatal(self):
        with tempfile.TemporaryDirectory() as temporary:
            storage = Storage.local(temporary)
            storage.cache.mkdir()
            with patch.object(Path, 'iterdir', side_effect=PermissionError()):
                cleanup(storage)
