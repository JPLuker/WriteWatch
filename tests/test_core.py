import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from writewatch.core import ScriptError, Session, Store, Tracker, word_count


def write_script(path, text):
    xml = '<document><paragraphs><para><style basestyle="Action"/><text>' + escape(text) + '</text></para></paragraphs></document>'
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('document.xml', xml)


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.path = self.folder / 'secret-title.fadein'
        write_script(self.path, 'one two three')
        self.now = 0.0

    def tearDown(self):
        self.temp.cleanup()

    def tracker(self):
        return Tracker(self.path, 'Writing', 10, lambda: self.now)

    def test_archive_and_plain_xml(self):
        self.assertEqual(word_count(self.path), 3)
        path = self.folder / 'script.osf'
        path.write_text('<document><paragraphs><para><text>One two.</text></para></paragraphs></document>')
        self.assertEqual(word_count(path), 2)

    def test_format_runs_namespaces_and_private_metadata(self):
        self.path.write_text('''<document xmlns="urn:osf"><titlepage><para><text>Secret Title</text></para></titlepage>
        <paragraphs><para synopsis="secret"><text>hel</text><text>lo <b>world</b> café don't well-known</text>
        <note><text>hidden note here</text></note></para></paragraphs></document>''')
        self.assertEqual(word_count(self.path), 5)

    def test_reject_entities_without_leaking_content(self):
        self.path.write_text('<!DOCTYPE document [<!ENTITY secret "SENSITIVE">]><document><paragraphs><para><text>&secret;</text></para></paragraphs></document>')
        with self.assertRaises(ScriptError) as caught:
            word_count(self.path)
        self.assertNotIn('SENSITIVE', str(caught.exception))
        self.assertNotIn('secret-title', str(caught.exception))

    def test_missing_archive_member_and_invalid_xml(self):
        with zipfile.ZipFile(self.path, 'w') as archive:
            archive.writestr('wrong.xml', '<document/>')
        with self.assertRaises(ScriptError):
            word_count(self.path)
        self.path.write_text('secret broken xml')
        with self.assertRaises(ScriptError):
            word_count(self.path)

    def test_reject_oversized_uncompressed_member(self):
        with zipfile.ZipFile(self.path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('document.xml', b' ' * (16 * 1024 * 1024 + 1))
        with self.assertRaises(ScriptError):
            word_count(self.path)

    def test_timer_net_and_finish(self):
        tracker = self.tracker()
        self.now = 12
        tracker.tick()
        write_script(self.path, 'one two three four five')
        tracker.observe()
        self.now = 20
        session = tracker.finish()
        self.assertEqual((session.seconds, session.net, session.status), (20, 2, 'done'))

    def test_pause_excludes_time_and_saved_edits(self):
        tracker = self.tracker()
        self.now = 10
        tracker.pause()
        write_script(self.path, 'one two three four five six')
        self.now = 100
        tracker.resume()
        write_script(self.path, 'one two three four five six seven')
        self.now = 110
        session = tracker.finish()
        self.assertEqual((session.net, session.seconds), (1, 20))

    def test_finish_while_paused_does_not_read_paused_changes(self):
        tracker = self.tracker()
        self.now = 4
        tracker.pause()
        write_script(self.path, 'one')
        self.now = 15
        session = tracker.finish()
        self.assertEqual((session.net, session.seconds), (0, 4))

    def test_failed_read_keeps_previous_baseline(self):
        tracker = self.tracker()
        self.path.write_text('partial save')
        with self.assertRaises(ScriptError):
            tracker.observe()
        self.assertEqual(tracker.session.net, 0)
        write_script(self.path, 'one two three four')
        tracker.observe()
        self.assertEqual(tracker.session.net, 1)

    def test_failed_finish_does_not_complete(self):
        tracker = self.tracker()
        self.path.unlink()
        with self.assertRaises(ScriptError):
            tracker.finish()
        self.assertEqual(tracker.session.status, 'running')

    def test_long_suspension_pauses_clock(self):
        tracker = self.tracker()
        self.now = 20
        tracker.tick()
        self.now = 600
        tracker.tick()
        self.assertEqual((tracker.session.seconds, tracker.session.status), (20, 'paused'))

    def test_revision_goal_and_negative_net(self):
        session = Session.new('Revision', 30)
        session.seconds = 900
        session.net = -200
        session.status = 'done'
        self.assertEqual(session.progress, 0.5)
        self.assertIn('-200 net words', session.summary())
        self.assertIn('50%', session.summary())
        self.assertNotIn('🟩', session.summary())
        self.assertNotIn('⬜', session.summary())

    def test_store_recovers_numeric_only_checkpoint(self):
        tracker = self.tracker()
        tracker.session.net = 12
        db_path = self.folder / 'history.sqlite3'
        store = Store(db_path)
        store.save(tracker.session)
        store.close()
        store = Store(db_path)
        history = store.history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].status, 'interrupted')
        self.assertEqual(history[0].net, 12)
        columns = [row[1] for row in store.db.execute('PRAGMA table_info(sessions)')]
        self.assertEqual(columns, ['id', 'started', 'mode', 'goal', 'seconds', 'net', 'saves', 'status'])
        self.assertNotIn(b'secret-title', db_path.read_bytes())
        self.assertNotIn(b'one two three', db_path.read_bytes())
        store.clear()
        self.assertEqual(store.history(), [])
        store.close()

    def test_zero_word_script_is_valid(self):
        write_script(self.path, '')
        self.assertEqual(word_count(self.path), 0)


if __name__ == '__main__':
    unittest.main()
