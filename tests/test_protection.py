"""Regression checks for writer-owned bytes, not just reported word counts."""
from contextlib import closing
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
import zipfile
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from writewatch.app import Window, ShareDialog
from writewatch.core import Store, Session, Tracker
from writewatch.data import delete_owned_data, write_backup
from writewatch.protection import write_new
from writewatch.storage import Storage, clear_artifacts, cleanup, RETENTION
from writewatch.updates import Installation, UpdateWorker
from tests.test_core import write_script
from tests.test_data import PREFS
from tests.test_updates import release


class ProtectionTests(unittest.TestCase):
    def test_all_cleanup_preserves_documents_and_nested_folders(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            storage = Storage.local(root)
            kept = []
            for folder in (root, storage.cache, storage.logs):
                folder.mkdir(exist_ok=True)
                for name in ('script.fadein', 'draft.docx', 'notes.txt', 'notes.md', 'backup.json', 'WriteWatch-notes.zip'):
                    path = folder / name
                    path.write_bytes(b'WRITER CONTENT')
                    os.utime(path, (1, 1))
                    kept.append(path)
                nested = folder / 'history.sqlite3.backup-v1'
                nested.mkdir()
                (nested / 'draft.txt').write_bytes(b'WRITER CONTENT')
                kept.append(nested / 'draft.txt')
            cleanup(storage, now=RETENTION + 10)
            clear_artifacts(storage.cache)
            clear_artifacts(storage.logs, logs=True)
            delete_owned_data(root)
            for path in kept:
                self.assertEqual(path.read_bytes(), b'WRITER CONTENT', str(path))

    def test_cleanup_preserves_protected_file_and_hardlink_alias(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / 'draft.txt'
            source.write_bytes(b'WRITER CONTENT')
            alias = root / 'last-update.log'
            try:
                os.link(source, alias)
            except OSError:
                self.skipTest('Hard links unavailable')
            protected = root / 'WriteWatch-1.0.0-Linux-x64.AppImage'
            protected.write_bytes(b'WRITER CONTENT')
            clear_artifacts(root, protected=[protected])
            self.assertEqual(source.read_bytes(), b'WRITER CONTENT')
            self.assertEqual(alias.read_bytes(), b'WRITER CONTENT')
            self.assertTrue(protected.exists())

    def test_cleanup_never_follows_linked_root_or_ancestor(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            docs = root / 'documents'
            docs.mkdir()
            nested = docs / 'updates'
            nested.mkdir()
            artifact = nested / 'last-update.log'
            artifact.write_bytes(b'WRITER CONTENT')
            link = root / 'link'
            try:
                link.symlink_to(docs, target_is_directory=True)
            except OSError:
                self.skipTest('Symlinks unavailable')
            clear_artifacts(link / 'updates')
            delete_owned_data(link)
            self.assertEqual(artifact.read_bytes(), b'WRITER CONTENT')
            self.assertTrue(link.is_symlink())

    def test_exports_refuse_existing_files_and_links_and_clean_failed_new_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = root / 'draft.txt'
            original.write_bytes(b'WRITER CONTENT')
            with self.assertRaises(FileExistsError):
                write_new(original, b'replacement')
            for kind in ('hard', 'symbolic'):
                alias = root / (kind + '.png')
                try:
                    os.link(original, alias) if kind == 'hard' else alias.symlink_to(original)
                except OSError:
                    continue
                with self.assertRaises(FileExistsError):
                    write_new(alias, b'image')
                self.assertTrue(alias.exists())
            self.assertEqual(original.read_bytes(), b'WRITER CONTENT')
            failed = root / 'failed.json'
            with patch('writewatch.protection.os.fsync', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    write_new(failed, b'new data')
            self.assertFalse(failed.exists())

    def test_store_refuses_linked_files_and_unrelated_database(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = root / 'draft.txt'
            original.write_bytes(b'WRITER CONTENT')
            destination = root / 'history.sqlite3'
            try:
                os.link(original, destination)
            except OSError:
                self.skipTest('Hard links unavailable')
            with self.assertRaises(ValueError):
                Store(destination)
            self.assertEqual(original.read_bytes(), b'WRITER CONTENT')
            destination.unlink()
            with closing(sqlite3.connect(destination)) as db:
                db.execute('CREATE TABLE writing (text TEXT)')
                db.commit()
            before = destination.read_bytes()
            with self.assertRaises(ValueError):
                Store(destination)
            self.assertEqual(destination.read_bytes(), before)

    def test_tracking_never_changes_document_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            paths = [root / 'draft.fadein', root / 'draft.txt', root / 'draft.md']
            write_script(paths[0], 'Private writing')
            for path in paths[1:]:
                path.write_text('Private writing')
            for path in paths:
                before = path.read_bytes()
                tracker = Tracker(path, 'Revision', 0)
                tracker.observe(force=True)
                tracker.pause()
                tracker.resume()
                tracker.finish()
                tracker.discard_snapshot()
                self.assertEqual(path.read_bytes(), before)

    def test_readers_leave_every_supported_extension_unchanged_on_errors(self):
        from writewatch.formats import EXTENSIONS, extract_text, ScriptError
        with tempfile.TemporaryDirectory() as d:
            for extension in EXTENSIONS:
                path = Path(d) / ('draft' + extension)
                path.write_bytes(b'Private writing, including incomplete saves.\x00')
                before = path.read_bytes()
                try:
                    extract_text(path)
                except ScriptError:
                    pass
                self.assertEqual(path.read_bytes(), before, extension)
            path = Path(d) / 'draft.docx'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('word/document.xml', '<document><body><p><t>Private writing</t></p></body></document>')
            before = path.read_bytes()
            tracker = Tracker(path, 'Writing', 0)
            tracker.finish()
            self.assertEqual(path.read_bytes(), before)

    def test_windows_junction_cleanup_preserves_target(self):
        import subprocess
        import sys
        if sys.platform != 'win32':
            self.skipTest('Windows junctions only')
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            target = root / 'documents'
            target.mkdir()
            path = target / 'last-update.log'
            path.write_bytes(b'WRITER CONTENT')
            junction = root / 'updates'
            subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(target)], check=True, capture_output=True)
            try:
                clear_artifacts(junction)
                self.assertEqual(path.read_bytes(), b'WRITER CONTENT')
                self.assertTrue(junction.is_junction())
            finally:
                junction.rmdir()

    def test_updater_preserves_existing_destination_and_partial_collision(self):
        for collision in ('destination', 'partial'):
            with self.subTest(collision=collision), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                asset = release()['assets'][0]
                path = root / (asset['name'] if collision == 'destination' else 'download-fixed.part')
                path.write_bytes(b'WRITER CONTENT')
                worker = UpdateWorker(Installation('appimage', root / 'app.AppImage', 'x86_64.AppImage'), root)
                errors = []
                worker.failed.connect(errors.append)
                with patch('writewatch.updates.__version__', '0.4.0'), patch('writewatch.updates.opener') as client, patch('writewatch.updates.uuid.uuid4') as token:
                    token.return_value.hex = 'fixed'
                    client.return_value.open.side_effect = [io.BytesIO(json.dumps([release()]).encode()), io.BytesIO(b'new version')]
                    worker.run()
                self.assertTrue(errors)
                self.assertEqual(path.read_bytes(), b'WRITER CONTENT')


class ProtectionUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        for widget in self.app.topLevelWidgets():
            widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def test_share_image_cannot_overwrite_existing_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'draft.png'
            path.write_bytes(b'WRITER CONTENT')
            session = Session.new('Writing', 0)
            dialog = ShareDialog(session)
            with patch.object(QFileDialog, 'getSaveFileName', return_value=(str(path), '')), patch.object(QMessageBox, 'warning') as warning:
                dialog.save_image(session)
                warning.assert_called_once()
            self.assertEqual(path.read_bytes(), b'WRITER CONTENT')
            dialog.close()

    def test_settings_link_is_refused_without_touching_document(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            store = Store(root / 'history.sqlite3')
            source = root / 'draft.txt'
            source.write_bytes(b'WRITER CONTENT')
            try:
                os.link(source, root / 'metrics.ini')
            except OSError:
                store.close()
                self.skipTest('Hard links unavailable')
            with self.assertRaises(ValueError):
                Window(store)
            self.assertEqual(source.read_bytes(), b'WRITER CONTENT')
            store.close()
