import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication, QEvent
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
            self.assertFalse(window.goal.isEnabled())
            window.start.click()
            self.assertEqual(window.tracker.session.goal, 0)
            self.assertFalse(window.skip_goal.isEnabled())
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
