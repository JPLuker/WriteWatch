import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QMessageBox
from writewatch.updates import (Installation, select_release, verify, version, helper_script,
                                TrustedRedirect, installation, UpdateWorker)
from writewatch.update_ui import UpdatesPanel
from writewatch.app import Window
from writewatch.core import Store


def release(number='0.5.0', suffix='x86_64.AppImage', data=b'new version'):
    name = f'WriteWatch-{number}-{suffix}'
    return {'tag_name': 'v' + number, 'prerelease': True, 'assets': [{
        'name': name, 'state': 'uploaded', 'size': len(data),
        'digest': 'sha256:' + hashlib.sha256(data).hexdigest(),
        'browser_download_url': f'https://github.com/JPLuker/WriteWatch/releases/download/v{number}/{name}'}]}


class UpdateTests(unittest.TestCase):
    def test_versions_and_preview_release_selection(self):
        self.assertEqual(version('v0.10.0'), (0, 10, 0))
        self.assertIsNone(version('0.4.0; touch something'))
        selected = select_release([release('0.5.0'), release('0.10.0'), release('0.2.0')], '0.4.0', 'x86_64.AppImage')
        self.assertEqual(selected['release_version'], '0.10.0')
        self.assertIsNone(select_release([release('0.4.0')], '0.4.0', 'x86_64.AppImage'))
        self.assertIsNone(select_release([release()], '0.4.0', 'Windows-Setup.exe'))

    def test_draft_untrusted_url_and_missing_digest(self):
        item = release()
        item['draft'] = True
        self.assertIsNone(select_release([item], '0.4.0', 'x86_64.AppImage'))
        item['draft'] = False
        item['assets'][0]['browser_download_url'] = 'https://evil.example/app'
        self.assertIsNone(select_release([item], '0.4.0', 'x86_64.AppImage'))
        item = release()
        del item['assets'][0]['digest']
        with self.assertRaises(ValueError):
            select_release([item], '0.4.0', 'x86_64.AppImage')

    def test_checksum_and_size(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'download'
            asset = release()['assets'][0]
            path.write_bytes(b'new version')
            verify(path, asset)
            path.write_bytes(b'bad version')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                verify(path, asset)
            path.write_bytes(b'partial')
            with self.assertRaisesRegex(ValueError, 'size'):
                verify(path, asset)

    def test_redirect_rejects_untrusted_host(self):
        with self.assertRaises(ValueError):
            TrustedRedirect().redirect_request(None, None, 302, '', {}, 'https://example.org/payload')
        with self.assertRaises(ValueError):
            TrustedRedirect().redirect_request(None, None, 302, '', {}, 'http://github.com/payload')

    def test_source_build_is_unmanaged(self):
        with patch.object(sys, 'frozen', False, create=True):
            self.assertIsNone(installation())

    @unittest.skipIf(sys.platform == 'win32', 'POSIX helper')
    def test_appimage_swap_preserves_old_and_restarts(self):
        with tempfile.TemporaryDirectory(prefix="writewatch ' update ") as folder:
            folder = Path(folder)
            target, payload = folder / 'WriteWatch.AppImage', folder / 'download'
            target.write_text('old executable', encoding='utf-8')
            # Synthetic executable leaves evidence of restart without launching Qt.
            marker = folder / 'restarted'
            import shlex
            payload.write_text('#!/bin/sh\ntouch ' + shlex.quote(str(marker)) + '\n', encoding='utf-8')
            script = helper_script(Installation('appimage', target, ''), payload, 99999999, 'test')
            subprocess.run(['/bin/sh', '-c', script], check=True, timeout=10)
            import time
            for _ in range(20):
                if marker.exists():
                    break
                time.sleep(.05)
            self.assertTrue(marker.exists())
            self.assertEqual(target.with_name(target.name + '.previous-test').read_text(), 'old executable')
            self.assertEqual(target.read_bytes(), payload.read_bytes())

    def test_worker_download_and_reject_corruption(self):
        import io
        import json
        for data, success in [(b'new version', True), (b'bad version', False)]:
            with self.subTest(success=success), tempfile.TemporaryDirectory() as folder:
                item = release()
                worker = UpdateWorker(Installation('appimage', Path('/app'), 'x86_64.AppImage'), Path(folder))
                ready, errors = [], []
                worker.ready.connect(lambda path, asset: ready.append(path))
                worker.failed.connect(errors.append)
                with patch('writewatch.updates.opener') as client, patch('writewatch.updates.__version__', '0.4.0'):
                    client.return_value.open.side_effect = [io.BytesIO(json.dumps([item]).encode()), io.BytesIO(data)]
                    worker.run()
                self.assertEqual(bool(ready), success)
                self.assertEqual(bool(errors), not success)
                self.assertFalse(list(Path(folder).glob('*.part')))
                if success:
                    self.assertEqual(ready[0].read_bytes(), data)

    def test_platform_helpers_wait_before_replacing(self):
        for kind in ('mac', 'windows-setup', 'windows-portable'):
            text = helper_script(Installation(kind, Path('/apps/WriteWatch'), ''), Path('/cache/update.zip'), 12345, 'test')
            self.assertIn('12345', text)
            self.assertNotIn('Stop-Process', text)
            if kind.startswith('windows'):
                self.assertIn('WaitForExit(120000)', text)
            if kind == 'windows-setup':
                self.assertIn('/WRITEWATCHUPDATE=1', text)
            if kind == 'mac':
                self.assertIn('codesign --verify', text)


class UpdateUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_active_session_blocks_restart_and_preference_persists(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / 'history.sqlite3')
            window = Window(store)
            panel = UpdatesPanel(window, folder)
            window.tabs.addTab(panel, 'Updates')
            panel.timer.stop()
            panel.pending = (Path(folder) / 'download', {})
            window.tracker = object()
            with patch('writewatch.update_ui.install_update') as install, patch.object(QMessageBox, 'information') as message:
                panel.apply()
                install.assert_not_called()
                message.assert_called_once()
            panel.automatic.setChecked(False)
            self.assertFalse(panel.settings.value('automatic', True, type=bool))
            window.tracker = None
            window.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            self.app.processEvents()
            store.close()
