import unittest
from writewatch.theme import LIGHT, DARK


def luminance(hex_value):
    rgb = [int(hex_value[n:n+2], 16) / 255 for n in (1, 3, 5)]
    rgb = [x/12.92 if x <= .04045 else ((x+.055)/1.055)**2.4 for x in rgb]
    return sum(x*w for x,w in zip(rgb, (.2126,.7152,.0722)))


class ContrastTests(unittest.TestCase):
    def test_text_and_focus_contrast_in_both_themes(self):
        for theme in (LIGHT, DARK):
            for fg, bg, minimum in [('text','surface',4.5), ('secondary','surface',4.5),
                                    ('tertiary','surface2',4.5), ('onaccent','accent',4.5),
                                    ('accent','surface',3), ('tertiary','surface',3)]:
                high, low = sorted((luminance(theme[fg]), luminance(theme[bg])), reverse=True)
                with self.subTest(theme=theme['canvas'], pair=(fg,bg)):
                    self.assertGreaterEqual((high+.05)/(low+.05), minimum)


class AppearanceTests(unittest.TestCase):
    def test_settings_persist_without_enabling_updates(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from PySide6.QtCore import QCoreApplication, QEvent
        from PySide6.QtWidgets import QApplication
        from writewatch.app import Window
        from writewatch.core import Store
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, WRITEWATCH_DISABLE_UPDATES='1'):
            store = Store(Path(folder) / 'history.sqlite3')
            window = Window(store, folder)
            window.theme_choice.setCurrentText('Dark')
            window.ambient_choice.setChecked(False)
            window.preferences.sync()
            self.assertTrue(app.property('auroraDark'))
            self.assertFalse(app.property('auroraAmbient'))
            self.assertIsNone(window.updates)
            window.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            window = Window(store, folder)
            self.assertEqual(window.theme_choice.currentText(), 'Dark')
            self.assertFalse(window.ambient_choice.isChecked())
            window.theme_choice.setCurrentText('Light')
            self.assertFalse(app.property('auroraDark'))
            window.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            app.processEvents()
            store.close()
