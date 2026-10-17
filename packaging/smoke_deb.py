"""Run after apt installs the package in a disposable Linux CI runner."""
import os
from pathlib import Path
import subprocess
import tempfile
import time

assert Path('/usr/share/applications/writewatch.desktop').is_file()
assert Path('/usr/share/icons/hicolor/256x256/apps/writewatch.png').is_file()
with tempfile.TemporaryDirectory() as folder:
    environment = dict(os.environ, QT_QPA_PLATFORM='offscreen', WRITEWATCH_DISABLE_UPDATES='1', WRITEWATCH_DATA_DIR=folder)
    app = subprocess.Popen(['/usr/bin/writewatch'], env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and app.poll() is None:
            if (Path(folder) / 'history.sqlite3').exists():
                break
            time.sleep(.1)
        assert app.poll() is None, 'Installed app exited during startup'
        assert (Path(folder) / 'history.sqlite3').exists(), 'History database not created'
    finally:
        app.terminate()
        app.communicate(timeout=10)
