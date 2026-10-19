import copy
from dataclasses import asdict
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from writewatch.core import Store, Session
from writewatch.app import Window
from writewatch.data import backup_payload, write_backup, read_backup, merge_sessions, delete_owned_data, clear_cache

PREFS = dict(theme='Dark', ambient=False, remember=True, recents=['/private/script.fadein'], automatic_updates=False, update_channel='Testing')


class DataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.store = Store(self.folder / 'history.sqlite3')
        self.session = Session.new('Revision', 5)
        self.session.status = 'done'
        self.session.goal_unit = 'pages'
        self.session.pages = 2.5
        self.session.added, self.session.removed, self.session.net = 10, 20, -10
        self.session.revision_metrics = True
        self.store.save(self.session)
        self.payload = backup_payload(self.store, copy.deepcopy(PREFS))

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_roundtrip_preserves_revision_pages_and_existing_ids(self):
        path = self.folder / 'export.json'
        write_backup(path, self.payload)
        loaded = read_backup(path)
        self.assertEqual(loaded['settings'], PREFS)
        self.assertEqual(loaded['sessions'][0], asdict(self.session))
        self.assertEqual(merge_sessions(self.store, loaded), 0)
        loaded['sessions'][0]['pages'] = 9
        merge_sessions(self.store, loaded)
        self.assertEqual(self.store.history()[0].pages, 2.5)
        loaded['sessions'][0]['id'] = 'new-session'
        self.assertEqual(merge_sessions(self.store, loaded), 1)
        self.assertEqual(len(self.store.history()), 2)

    def test_legacy_backup_without_channel_still_imports(self):
        legacy = copy.deepcopy(self.payload)
        legacy['version'] = 1
        del legacy['settings']['update_channel']
        path = self.folder / 'legacy.json'
        write_backup(path, legacy)
        self.assertEqual(merge_sessions(self.store, read_backup(path)), 0)

    def test_malformed_imports_leave_history_unchanged(self):
        for key, value in [('net', True), ('seconds', float('nan')), ('added', -1), ('goal_unit', 'unknown'), ('revision_metrics', 1), ('started', 'not-a-date')]:
            with self.subTest(key=key):
                payload = copy.deepcopy(self.payload)
                payload['sessions'][0][key] = value
                with self.assertRaises(ValueError):
                    merge_sessions(self.store, payload)
        for mutate in (lambda p: p.update(version=99), lambda p: p['sessions'][0].update(script='PRIVATE TEXT'), lambda p: p['sessions'].append(p['sessions'][0])):
            payload = copy.deepcopy(self.payload)
            mutate(payload)
            with self.assertRaises(ValueError):
                merge_sessions(self.store, payload)
        self.assertEqual(len(self.store.history()), 1)
        self.assertEqual(self.store.history()[0].net, -10)

    def test_import_rolls_back_all_new_rows_on_database_error(self):
        payload = copy.deepcopy(self.payload)
        payload['sessions'][0]['id'] = 'first'
        second = dict(payload['sessions'][0], id='second')
        payload['sessions'].append(second)
        self.store.db.execute("CREATE TRIGGER fail_import BEFORE INSERT ON sessions WHEN NEW.id='second' BEGIN SELECT RAISE(ABORT, 'simulated failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            merge_sessions(self.store, payload)
        self.assertEqual([s.id for s in self.store.history()], [self.session.id])

    def test_failed_export_preserves_existing_backup(self):
        path = self.folder / 'export.json'
        path.write_text('old backup')
        with patch('writewatch.data.os.replace', side_effect=OSError('full disk')):
            with self.assertRaises(OSError):
                write_backup(path, self.payload)
        self.assertEqual(path.read_text(), 'old backup')
        self.assertFalse(list(self.folder.glob('.writewatch-export-*')))

    def test_oversized_and_invalid_json_rejected(self):
        path = self.folder / 'bad.json'
        path.write_text('x' * 65)
        with patch('writewatch.data.MAX_BACKUP', 64), self.assertRaises(ValueError):
            read_backup(path)
        path.write_text('{invalid')
        with self.assertRaises(ValueError):
            read_backup(path)

    def test_delete_only_owned_data_and_keep_documents_exports(self):
        self.store.close()
        for name in ('appearance.ini', 'updates.ini', 'recents.ini', 'history.sqlite3.backup-v2', 'script.fadein', 'backup.json', 'history.sqlite3.backup-vnotes'):
            (self.folder / name).write_text('keep or remove')
        updates = self.folder / 'updates'
        updates.mkdir()
        (updates / 'last-update.log').write_text('log')
        delete_owned_data(self.folder)
        self.assertEqual({p.name for p in self.folder.iterdir()}, {'script.fadein', 'backup.json', 'history.sqlite3.backup-vnotes'})

    def test_cache_symlink_does_not_delete_target(self):
        target = self.folder / 'documents'
        target.mkdir()
        (target / 'script.txt').write_text('secret')
        try:
            (self.folder / 'updates').symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest('Creating symlinks requires privileges on this host')
        clear_cache(self.folder)
        self.assertEqual((target / 'script.txt').read_text(), 'secret')
        self.assertFalse((self.folder / 'updates').is_symlink())


class DataUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.store = Store(self.folder / 'history.sqlite3')
        with patch.dict(os.environ, {'WRITEWATCH_DISABLE_UPDATES': '1'}):
            self.window = Window(self.store, update_folder=self.folder)
        self.window.timer.stop()

    def tearDown(self):
        self.window.tracker = None
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.store.close()
        self.temp.cleanup()

    def test_export_import_and_diagnostics(self):
        path = self.folder / 'backup.json'
        session = Session.new('Writing', 0)
        session.status = 'done'
        self.store.save(session)
        self.window.theme_choice.setCurrentText('Dark')
        with patch.object(QFileDialog, 'getSaveFileName', return_value=(str(path), '')), patch.object(QMessageBox, 'information'):
            self.window.export_data()
        self.store.clear()
        self.window.theme_choice.setCurrentText('Light')
        with patch.object(QFileDialog, 'getOpenFileName', return_value=(str(path), '')), patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes), patch.object(QMessageBox, 'information'):
            self.window.import_data()
        self.assertEqual(self.window.theme_choice.currentText(), 'Dark')
        self.assertEqual(len(self.store.history()), 1)
        self.window.recent_settings.setValue('files', ['/private/secret-title.fadein'])
        self.window.copy_diagnostics()
        self.assertNotIn('secret-title', self.app.clipboard().text())

    def test_active_session_blocks_data_changes(self):
        self.window.tracker = object()
        with patch.object(QMessageBox, 'information'), patch.object(QFileDialog, 'getSaveFileName') as dialog:
            self.window.export_data()
            dialog.assert_not_called()
        self.assertTrue(self.store.path.exists())

    def test_clear_cache_resets_pending_update_and_preserves_history(self):
        from writewatch.update_ui import UpdatesPanel
        from writewatch.updates import Installation
        with patch('writewatch.update_ui.installation', return_value=Installation('appimage', self.folder / 'app.AppImage', 'x86_64.AppImage')):
            panel = UpdatesPanel(self.window, self.folder)
        self.window.updates = panel
        panel.timer.stop()
        panel.automatic.setChecked(False)
        panel.folder.mkdir()
        download = panel.folder / 'update.AppImage'
        download.write_text('download')
        panel.downloaded(download, {'release_version': '9.0.0'})
        with patch.object(QMessageBox, 'information'):
            self.window.clear_update_cache()
        self.assertIsNone(panel.pending)
        self.assertFalse(panel.restart.isEnabled())
        self.assertTrue(panel.check.isEnabled())
        self.assertFalse(panel.folder.exists())
        self.assertTrue(self.store.path.exists())
        self.assertEqual(self.window.tabs.tabText(self.window.tabs.indexOf(self.window.settings_tab)), 'Settings')

    def test_delete_cancel_preserves_data_then_confirm_quits(self):
        from writewatch.storage import Storage
        legacy = self.folder / 'legacy'
        legacy.mkdir()
        (legacy / 'history.sqlite3').write_text('old history')
        self.window.storage = Storage(self.folder, self.folder / 'updates', self.folder / 'logs', legacy)
        doc = self.folder / 'script.fadein'
        doc.write_text('private document')
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No):
            self.window.delete_all_data()
        self.assertTrue(self.store.path.exists())
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes), patch.object(QApplication, 'quit') as quit_app:
            self.window.delete_all_data()
            quit_app.assert_called_once()
        self.assertFalse(self.store.path.exists())
        self.assertFalse((legacy / 'history.sqlite3').exists())
        self.assertEqual(doc.read_text(), 'private document')
