import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QCoreApplication, QEvent, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox
from writewatch.app import Window, ShareDialog
from writewatch.core import Store, Session
from tests.test_core import write_script


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.store = Store(self.folder / 'history.sqlite3')
        self.window = Window(self.store)
        self.window.timer.stop()
        self.file = self.folder / 'private.fadein'
        write_script(self.file, 'one two three')

    def tearDown(self):
        for widget in self.app.topLevelWidgets():
            widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.store.close()
        self.temp.cleanup()

    def test_open_starts_once_and_remembers_only_success(self):
        self.window.open_path(self.file)
        original = self.window.tracker.session.id
        self.window.open_path(self.file)
        self.assertEqual(self.window.tracker.session.id, original)
        self.assertEqual(self.window.recent_files(), [str(self.file)])
        self.assertNotIn(b'private.fadein', self.store.path.read_bytes())
        self.window.set_remember_files(False)
        self.assertEqual(self.window.recent_files(), [])
        with patch.object(ShareDialog, 'exec', return_value=0):
            self.window.finish()
        self.window.open_path(self.file)
        self.assertEqual(self.window.recent_files(), [])

    def test_manual_pages_and_live_goal_survive_reopen(self):
        w = self.window
        w.open_path(self.file)
        identity = w.tracker.session.id
        def save():
            w.skip_goal.setChecked(False)
            w.goal_unit.setCurrentText('Pages')
            w.goal.setValue(5)
            w.goal_dialog.accept()
        QTimer.singleShot(0, save)
        w.edit_goal()
        self.assertEqual(w.tracker.session.id, identity)
        w.pages_done.setValue(2.5)
        self.assertEqual(w.tracker.session.progress, .5)
        def cancel():
            w.goal_unit.setCurrentText('Minutes')
            w.goal_dialog.reject()
        QTimer.singleShot(0, cancel)
        w.edit_goal()
        self.assertEqual(w.tracker.session.unit, 'pages')
        self.assertEqual(w.goal.value(), 5)
        with patch.object(ShareDialog, 'exec', return_value=0):
            w.finish()
        session = self.store.history()[0]
        self.assertEqual((session.pages, session.goal, session.unit), (2.5, 5, 'pages'))
        self.assertIn('Pages (self-reported): 2.5', session.summary())
        self.assertNotIn('Writing', session.summary())

    def test_estimated_pages_follow_net_words_and_pause(self):
        w = self.window
        w.skip_goal.setChecked(False)
        w.goal_unit.setCurrentText('Pages')
        w.page_method.setCurrentText('Estimate')
        w.page_rate.setValue(10)
        w.open_path(self.file)
        write_script(self.file, 'one two three ' + 'word ' * 25)
        w.poll()
        self.assertEqual(w.tracker.session.page_count, 2.5)
        w.pause_resume()
        write_script(self.file, 'one')
        w.pause_resume()
        self.assertEqual(w.tracker.session.page_count, 2.5)
        with patch.object(ShareDialog, 'exec', return_value=0):
            w.finish()
        self.assertIn('Estimated pages: 2.5', self.store.history()[0].summary())

    def test_negative_count_finishes_with_or_without_goal(self):
        for goal in (0, 10):
            write_script(self.file, 'one two three')
            self.window.skip_goal.setChecked(not goal)
            self.window.goal.setValue(goal or 1)
            self.window.open_path(self.file)
            write_script(self.file, '')
            self.window.poll()
            self.assertEqual(self.window.tracker.session.net, -3)
            self.assertTrue(self.window.done.isEnabled())
            with patch.object(ShareDialog, 'exec', return_value=0):
                self.window.finish()
            self.assertIsNone(self.window.tracker)
        self.assertEqual(len(self.store.history()), 2)
        self.assertTrue(all(s.net == -3 and s.status == 'done' for s in self.store.history()))

    def test_failed_final_save_can_retry_or_finish_last_counts(self):
        self.window.open_path(self.file)
        write_script(self.file, 'one')
        self.window.poll()
        self.file.unlink()
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No):
            self.window.finish()
        self.assertIsNotNone(self.window.tracker)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes), patch.object(ShareDialog, 'exec', return_value=0):
            self.window.finish()
        self.assertIsNone(self.window.tracker)
        self.assertEqual(self.store.history()[0].net, -2)


class MigrationTests(unittest.TestCase):
    def test_legacy_migration_preserves_history_and_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'history.sqlite3'
            with closing(sqlite3.connect(path)) as db, db:
                db.execute('CREATE TABLE sessions (id TEXT PRIMARY KEY, started TEXT, mode TEXT, goal INTEGER, seconds REAL, net INTEGER, saves INTEGER, status TEXT)')
                db.execute("INSERT INTO sessions VALUES ('old','2026-10-17T12:00:00+00:00','Revision',30,900,-100,2,'done')")
            original = path.read_bytes()
            store = Store(path)
            session = store.history()[0]
            self.assertEqual((session.unit, session.progress, session.net), ('minutes', .5, -100))
            store.close()
            backup = next(path.parent.glob(path.name + '.backup-v0-*'))
            with closing(sqlite3.connect(backup)) as db:
                self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 0)
                self.assertEqual(db.execute('SELECT net FROM sessions').fetchone()[0], -100)
                self.assertEqual(len(db.execute('PRAGMA table_info(sessions)').fetchall()), 8)
            original_backup = backup.read_bytes()
            store = Store(path)
            store.close()
            self.assertEqual(backup.read_bytes(), original_backup)

    def test_newer_database_is_not_modified(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'history.sqlite3'
            with closing(sqlite3.connect(path)) as db, db:
                db.execute('PRAGMA user_version=99')
            before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, 'newer version'):
                Store(path)
            self.assertEqual(path.read_bytes(), before)
