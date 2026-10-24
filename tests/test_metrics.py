from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QDialog
from writewatch.core import Session, Store, Tracker
from writewatch.metrics import CATALOG, defaults, rows, summary, validate_preferences
from writewatch.app import Window, ShareDialog, card
from writewatch.data import backup_payload, write_backup, read_backup


class MetricTests(unittest.TestCase):
    def session(self):
        s = Session.new('Revision', 100)
        s.status, s.seconds, s.net, s.added, s.removed, s.saves = 'done', 120, -10, 20, 30, 2
        s.revision_metrics = True
        return s

    def test_derived_values_and_unavailable_data(self):
        s = self.session()
        values = {key: value for key, _, value in rows(s, CATALOG)}
        self.assertEqual(values['changes'], '50')
        self.assertEqual(values['net_pace'], '-5.0')
        self.assertEqual(values['change_pace'], '25.0')
        self.assertEqual(values['change_size'], '25.0')
        self.assertEqual(values['removed_share'], '60.0%')
        s.seconds, s.saves, s.added, s.removed = 0, 0, 0, 0
        keys = {key for key, _, _ in rows(s, CATALOG)}
        self.assertTrue({'net_pace', 'change_pace', 'change_size', 'removed_share'}.isdisjoint(keys))
        s.revision_metrics = False
        self.assertTrue({'added', 'removed', 'changes'}.isdisjoint({key for key, _, _ in rows(s, CATALOG)}))

    def test_disabled_metrics_do_not_enter_summary(self):
        s = self.session()
        text = summary(s, ['observations'])
        self.assertIn('Observed changes: 2', text)
        for unwanted in ('net words', 'Session time', 'Goal', 'Words added', 'Words removed'):
            self.assertNotIn(unwanted, text)
        self.assertIn('#WriteWatch', summary(s, []))
        self.assertIn('added', defaults('Revision'))
        self.assertNotIn('added', defaults('Writing'))

    def test_preferences_reject_unknown_or_duplicate_metrics(self):
        for choice in (['keystrokes'], ['net', 'net'], [True]):
            with self.assertRaises(ValueError):
                validate_preferences({'Writing': choice, 'Revision': []})


class MetricUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_preferences_apply_to_session_sharing_history_and_backups(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            store = Store(folder / 'history.sqlite3')
            window = Window(store)
            window.timer.stop()
            path = folder / 'script.txt'
            path.write_text('private words')
            window.tracker = Tracker(path, 'Writing', 100)
            def choose(dialog):
                for checkbox in dialog.findChildren(QCheckBox):
                    checkbox.setChecked(checkbox.text() == 'Observed changes')
                return QDialog.DialogCode.Accepted
            with patch.object(QDialog, 'exec', choose):
                window.edit_metrics()
            self.assertEqual(window.enabled_metrics('Writing'), ['observations'])
            self.assertTrue(window.time_label.isHidden())
            self.assertTrue(window.words.isHidden())
            s = window.tracker.session
            s.status = 'done'
            store.save(s)
            window.tracker.discard_snapshot()
            window.tracker = None
            dialog = ShareDialog(s, window)
            dialog.copy_summary()
            self.assertIn('Observed changes', self.app.clipboard().text())
            self.assertNotIn('net words', self.app.clipboard().text())
            self.assertFalse(card(s, list(CATALOG)).isNull())
            self.assertFalse(card(s, []).isNull())
            payload = backup_payload(store, window.export_preferences())
            self.assertEqual(payload['version'], 3)
            exported = folder / 'backup.json'
            write_backup(exported, payload)
            self.assertEqual(read_backup(exported)['settings']['metrics']['Writing'], ['observations'])
            restored = Window(store)
            restored.timer.stop()
            self.assertEqual(restored.enabled_metrics('Writing'), ['observations'])
            restored.deleteLater()
            window.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            self.app.processEvents()
            store.close()

    def test_cancel_keeps_preferences(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(Path(temporary) / 'history.sqlite3')
            window = Window(store)
            before = window.metric_preferences()
            def cancel(dialog):
                for checkbox in dialog.findChildren(QCheckBox):
                    checkbox.setChecked(False)
                return QDialog.DialogCode.Rejected
            with patch.object(QDialog, 'exec', cancel):
                window.edit_metrics()
            self.assertEqual(window.metric_preferences(), before)
            window.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            self.app.processEvents()
            store.close()
