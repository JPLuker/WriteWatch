import tempfile
import sqlite3
from contextlib import closing
import unittest
from pathlib import Path
from writewatch.core import Tracker, Store, Session
from tests.test_core import write_script


class RevisionTests(unittest.TestCase):
    def test_equal_length_rewrite_moves_undo_and_pause(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'private.fadein'
            write_script(path, 'the red house')
            t = Tracker(path, 'Revision', 30)
            write_script(path, 'the blue house')
            t.observe(force=True)
            self.assertEqual((t.session.added, t.session.removed, t.session.net), (1, 1, 0))
            write_script(path, 'house the blue')
            t.observe(force=True)
            self.assertEqual((t.session.added, t.session.removed), (1, 1))
            write_script(path, 'the red house')
            t.observe(force=True)
            self.assertEqual((t.session.added, t.session.removed), (2, 2))
            t.pause()
            write_script(path, 'outside paused words')
            t.resume()
            write_script(path, 'outside paused words more')
            t.observe(force=True)
            self.assertEqual((t.session.added, t.session.removed, t.session.net), (3, 2, 1))
            session = t.finish()
            self.assertIn('Words added: 3 · Words removed: 2', session.summary())
            t.discard_snapshot()
            self.assertFalse(t.previous)
            self.assertFalse(t._key)

    def test_repeated_words_invalid_save_and_history_privacy(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'private.fadein'
            write_script(path, 'secret secret draft')
            t = Tracker(path, 'Revision', 0)
            fingerprints = list(t.previous)
            self.assertTrue(all(isinstance(x, bytes) and len(x) == 16 for x in fingerprints))
            write_script(path, 'secret draft draft draft')
            t.observe(force=True)
            self.assertEqual((t.session.added, t.session.removed, t.session.net), (2, 1, 1))
            path.write_text('broken file')
            with self.assertRaises(ValueError):
                t.observe(force=True)
            self.assertEqual((t.session.added, t.session.removed), (2, 1))
            write_script(path, 'secret draft draft draft')
            session = t.finish()
            dbpath = Path(d) / 'history.sqlite3'
            store = Store(dbpath)
            store.save(session)
            store.close()
            store = Store(dbpath)
            saved = store.history()[0]
            self.assertEqual((saved.added, saved.removed, saved.net), (2, 1, 1))
            store.close()
            data = dbpath.read_bytes()
            for secret in (b'secret', b'private.fadein', *fingerprints):
                self.assertNotIn(secret, data)

    def test_old_sessions_do_not_claim_revision_totals(self):
        session = Session.new('Revision', 0)
        self.assertNotIn('Words added', session.summary())

    def test_page_goal_database_migrates_without_invented_metrics(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'history.sqlite3'
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("CREATE TABLE sessions (id TEXT PRIMARY KEY, started TEXT, mode TEXT, goal INTEGER, seconds REAL, net INTEGER, saves INTEGER, status TEXT, goal_unit TEXT, pages REAL, words_per_page INTEGER)")
                db.execute("INSERT INTO sessions VALUES ('old','2026-10-18T12:00:00+00:00','Revision',5,600,-4,2,'done','pages',2.5,250)")
                db.execute('PRAGMA user_version=1')
            store = Store(path)
            old = store.history()[0]
            self.assertEqual((old.pages, old.goal, old.net, old.unit), (2.5, 5, -4, 'pages'))
            self.assertFalse(old.revision_metrics)
            self.assertNotIn('Words added', old.summary())
            self.assertEqual(store.db.execute('PRAGMA user_version').fetchone()[0], 2)
            store.close()
            with closing(sqlite3.connect(str(path) + '.backup-v1')) as db:
                self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 1)
                self.assertEqual(db.execute('SELECT pages FROM sessions').fetchone()[0], 2.5)
