"""Exercise the entry point, including storage and single-instance locking."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


class LaunchTests(unittest.TestCase):
    def test_entrypoint_stays_open_and_creates_history(self):
        with tempfile.TemporaryDirectory() as folder:
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen', XDG_DATA_HOME=folder,
                       LOCALAPPDATA=folder, APPDATA=folder, WRITEWATCH_DATA_DIR=folder)
            process = subprocess.Popen([sys.executable, '-m', 'writewatch'], env=env,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline and process.poll() is None:
                    if list(Path(folder).rglob('history.sqlite3')):
                        break
                    time.sleep(0.1)
                self.assertIsNone(process.poll(), 'Application exited before entering its event loop')
                self.assertTrue(list(Path(folder).rglob('history.sqlite3')), 'History database missing')
            finally:
                process.terminate()
                process.communicate(timeout=5)
