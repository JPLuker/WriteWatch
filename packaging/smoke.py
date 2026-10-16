"""Launch the packaged executable, verify storage initialization, then stop it."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

root = Path(__file__).resolve().parents[1]
if sys.platform == 'darwin':
    binary = root / 'dist/WriteWatch.app/Contents/MacOS/WriteWatch'
elif sys.platform == 'win32':
    binary = root / 'dist/WriteWatch/WriteWatch.exe'
else:
    binary = root / 'dist/WriteWatch/WriteWatch'
with tempfile.TemporaryDirectory() as folder:
    env = dict(os.environ, WRITEWATCH_DISABLE_UPDATES='1', QT_QPA_PLATFORM='offscreen', WRITEWATCH_DATA_DIR=folder)
    process = subprocess.Popen([str(binary)], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 20
        ready = False
        while time.monotonic() < deadline and process.poll() is None:
            if list(Path(folder).rglob('history.sqlite3')):
                ready = True
                break
            time.sleep(0.1)
        if not ready or process.poll() is not None:
            raise RuntimeError('Packaged app failed startup or did not create its isolated history database')
        time.sleep(1)
        if process.poll() is not None:
            raise RuntimeError('Packaged app exited unexpectedly after initialization')
        print('Packaged app startup: PASS')
    finally:
        if process.poll() is None:
            process.terminate()
        _, errors = process.communicate(timeout=10)
        if errors:
            print(errors.decode('utf-8', errors='replace'), file=sys.stderr)
