import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import sqlite3
import unittest
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication, QEvent, QTimer
from PySide6.QtWidgets import QApplication
from writewatch.core import Session, Store
from writewatch.app import Window, ShareDialog, card
from tests.test_core import write_script


class GoalsHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        # Dispose native widgets while QApplication is alive, before Python's
        # module/class teardown can destroy the application out of order.
        for widget in self.app.topLevelWidgets():
            widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def test_no_goal_summary_and_image(self):
        for mode in ('Writing', 'Revision'):
            session = Session.new(mode, 0)
            session.net = -42
            session.seconds = 600
            session.status = 'done'
            self.assertEqual(session.progress, 0)
            self.assertEqual(session.goal_label, 'No goal set')
            self.assertNotIn('Goal', session.summary())
            self.assertNotIn('%', session.summary())
            self.assertIn('-42 net words', session.summary())
            self.assertFalse(card(session).isNull())

    def test_goal_results(self):
        session = Session.new('Writing', 500)
        session.net = 250
        self.assertEqual(session.goal_result, '50% of goal')
        session.net = 600
        self.assertEqual(session.goal_result, 'Goal reached')
        session = Session.new('Revision', 30)
        session.seconds = 1800
        self.assertEqual(session.goal_result, 'Goal reached')
        with self.assertRaises(ValueError):
            Session.new('Writing', -1)

    def test_existing_and_skipped_goals_persist_together(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'history.sqlite3'
            store = Store(path)
            old = Session.new('Writing', 500)
            old.status = 'done'
            store.save(old)
            store.close()
            store = Store(path)
            new = Session.new('Revision', 0)
            new.status = 'done'
            store.save(new)
            store.close()
            store = Store(path)
            self.assertEqual({s.goal for s in store.history()}, {0, 500})
            store.close()

    def test_skip_goal_full_session_then_review(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            store = Store(folder / 'history.sqlite3')
            window = Window(store)
            window.timer.stop()
            script = folder / 'secret.fadein'
            write_script(script, 'one two')
            window.path = script
            window.skip_goal.setChecked(True)
            window.update_view()
            self.assertFalse(window.goal.isEnabled())
            window.start.click()
            self.assertEqual(window.tracker.session.goal, 0)
            self.assertTrue(window.skip_goal.isEnabled())
            self.assertTrue(window.progress.isHidden())
            write_script(script, 'one two three')
            with patch.object(ShareDialog, 'exec', return_value=0):
                window.done.click()
            self.assertEqual(window.table.rowCount(), 1)
            self.assertEqual(window.table.item(0, 4).text(), 'No goal set')
            with patch('writewatch.app.ShareDialog') as dialog:
                window.review_button.click()
                self.assertTrue(dialog.call_args.kwargs['review'])
                self.assertEqual(dialog.call_args.args[0].net, 1)
            window.skip_goal.setChecked(False)
            self.assertTrue(window.goal.isEnabled())
            window.close()
            store.close()

    def test_segmented_choices_update_goal_units(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(Path(d) / 'history.sqlite3')
            window = Window(store)
            self.assertTrue(window.skip_goal.isChecked())
            self.assertTrue(window.goal_row.isHidden())
            window.skip_goal.buttons['Set goal'].click()
            self.assertFalse(window.goal_row.isHidden())
            self.assertEqual(window.goal.value(), 500)
            window.mode.buttons['Revision'].click()
            self.assertEqual(window.mode.currentText(), 'Revision')
            self.assertEqual(window.goal.value(), 30)
            self.assertEqual(window.goal.suffix(), ' minutes')
            window.mode.buttons['Writing'].click()
            self.assertEqual(window.goal.suffix(), ' net words')
            window.skip_goal.buttons['No goal'].click()
            self.assertTrue(window.goal_row.isHidden())
            window.close()
            store.close()

    def test_live_mode_switch_updates_goal_without_resetting_session(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(Path(d) / 'history.sqlite3')
            script = Path(d) / 'draft.fadein'
            write_script(script, 'one two three')
            window = Window(store)
            window.timer.stop()
            window.skip_goal.setChecked(False)
            window.goal_unit.setCurrentText('Pages')
            window.page_method.setCurrentText('Estimate')
            window.page_rate.setValue(300)
            window.goal.setValue(7)
            window.path = script
            window.begin()
            session = window.tracker.session
            session.seconds, session.net, session.pages = 600, -5, 2
            session.status = 'paused'
            identity = (session.id, session.started)
            window.mode.buttons['Revision'].click()
            self.assertEqual((session.mode, session.unit, session.goal), ('Revision', 'minutes', 30))
            self.assertIn('30 minutes', window.goal_settings_button.toolTip())
            self.assertAlmostEqual(session.progress, 1 / 3)
            window.goal.setValue(45)
            window.apply_goal()
            window.mode.buttons['Writing'].click()
            self.assertEqual((session.unit, session.goal, session.words_per_page), ('estimated_pages', 7, 300))
            window.mode.buttons['Revision'].click()
            self.assertEqual((session.unit, session.goal), ('minutes', 45))
            self.assertEqual((session.id, session.started), identity)
            self.assertEqual((session.seconds, session.net, session.pages, session.status), (600, -5, 2, 'paused'))
            window.skip_goal.setChecked(True)
            window.apply_goal()
            window.mode.buttons['Writing'].click()
            window.mode.buttons['Revision'].click()
            self.assertTrue(window.skip_goal.isChecked())
            self.assertEqual(session.goal, 0)
            with sqlite3.connect(store.path) as db:
                saved = db.execute('SELECT mode, goal, goal_unit FROM sessions WHERE id = ?', (session.id,)).fetchone()
            self.assertEqual(tuple(saved), ('Revision', 0, 'minutes'))
            window.tracker = None
            window.close()
            store.close()

    def test_goal_dialog_save_and_cancel(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(Path(d) / 'history.sqlite3')
            window = Window(store)
            def change_and_cancel():
                window.skip_goal.setChecked(False)
                window.goal.setValue(900)
                window.goal_dialog.reject()
            QTimer.singleShot(0, change_and_cancel)
            window.edit_goal()
            self.assertTrue(window.skip_goal.isChecked())
            self.assertEqual(window.goal.value(), 500)
            def change_and_save():
                window.skip_goal.setChecked(False)
                window.goal.setValue(750)
                window.goal_dialog.accept()
            QTimer.singleShot(0, change_and_save)
            window.edit_goal()
            self.assertFalse(window.skip_goal.isChecked())
            self.assertIn('750 words', window.goal_settings_button.text())
            self.assertFalse(window.goal_dialog.isVisible())
            window.close()
            store.close()

    def test_history_filters_and_reopen(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'history.sqlite3'
            store = Store(path)
            recent = Session.new('Writing', 500)
            recent.status = 'done'
            older = Session.new('Revision', 0)
            older.started = (datetime.now().astimezone() - timedelta(days=15)).isoformat()
            older.status = 'interrupted'
            store.save(recent)
            store.save(older)
            store.close()
            store = Store(path)
            window = Window(store)
            window.timer.stop()
            self.assertEqual(window.table.rowCount(), 2)
            window.history_period.setCurrentText('Last 7 days')
            self.assertEqual([s.id for s in window.history], [recent.id])
            window.history_mode.setCurrentText('Revision')
            self.assertEqual(window.table.rowCount(), 0)
            self.assertFalse(window.review_button.isEnabled())
            window.history_period.setCurrentText('Last 30 days')
            self.assertEqual([s.id for s in window.history], [older.id])
            self.assertTrue(window.review_button.isEnabled())
            dialog = ShareDialog(older, window, review=True)
            dialog.copy_summary()
            self.assertIn('Interrupted session', self.app.clipboard().text())
            self.assertNotIn('Goal', self.app.clipboard().text())
            dialog.close()
            window.close()
            store.close()
