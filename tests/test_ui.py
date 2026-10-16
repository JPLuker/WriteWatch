import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication
from writewatch.app import Window, ShareDialog, STYLE, card
from writewatch.core import Store
from tests.test_core import write_script


class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyleSheet(STYLE)

    def test_real_session_done_copy_history_and_png(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            store = Store(path / 'history.sqlite3')
            script = path / 'private-title.fadein'
            write_script(script, 'PRIVATE CONTENT')
            window = Window(store)
            window.timer.stop()
            window.path = script
            window.update_view()
            window.start.click()
            self.assertIsNotNone(window.tracker)
            write_script(script, 'PRIVATE CONTENT plus more words')
            window.poll()
            self.assertEqual(window.words.text(), '+3')
            window.pause_button.click()
            self.assertEqual(window.pause_button.text(), 'Resume')
            window.pause_button.click()
            with patch.object(ShareDialog, 'exec', return_value=0):
                window.done.click()
            self.assertIsNone(window.tracker)
            self.assertEqual(len(store.history()), 1)
            session = store.history()[0]
            dialog = ShareDialog(session, window)
            dialog.copy.click()
            copied = self.app.clipboard().text()
            self.assertIn('+3 net words', copied)
            for secret in ('PRIVATE', 'CONTENT', 'private-title', '🟩', '⬜'):
                self.assertNotIn(secret, copied)
            png = path / 'card.png'
            self.assertTrue(card(session).save(str(png), 'PNG'))
            self.assertGreater(png.stat().st_size, 1000)
            dialog.close()
            window.close()
            store.close()


if __name__ == '__main__':
    unittest.main()
