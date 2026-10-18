import gzip
import tempfile
import unittest
import zipfile
from pathlib import Path

from writewatch.formats import ScriptError, word_count, file_filter, extract_text
from writewatch.core import Tracker, Store


class FormatTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def file(self, suffix, text):
        path = self.folder / ('private' + suffix)
        path.write_text(text, encoding='utf-8')
        return path

    def archive(self, suffix, members):
        path = self.folder / ('private' + suffix)
        with zipfile.ZipFile(path, 'w') as z:
            for name, text in members.items():
                z.writestr(name, text)
        return path

    def test_text_unicode_and_utf16(self):
        self.assertEqual(word_count(self.file('.TXT', "Hello café don't well-known")), 4)
        path = self.folder / 'utf16.txt'
        path.write_bytes('Hello café'.encode('utf-16'))
        self.assertEqual(word_count(path), 2)

    def test_markdown_no_frontmatter_comments_or_link_urls(self):
        text = '---\nsecret: title here\n---\n# Hello\n\n**brave** [world](https://private.example/hidden)\n<!-- secret note -->\n'
        self.assertEqual(word_count(self.file('.md', text)), 3)

    def test_fountain_title_notes_and_synopsis(self):
        text = 'Title: SECRET TITLE\nAuthor: SECRET NAME\n\nINT. ROOM - DAY\n\nHello world.\n[[secret note]]\n/* discarded text */\n# Act One\n= Synopsis text\n'
        self.assertEqual(word_count(self.file('.fountain', text)), 5)

    def test_fdx_body_only_split_runs_dual_dialogue(self):
        text = '<FinalDraft><TitlePage><Content><Paragraph><Text>SECRET TITLE</Text></Paragraph></Content></TitlePage><Content><Paragraph><Text>Hel</Text><Text>lo world</Text><ScriptNote><Text>secret note</Text></ScriptNote></Paragraph><DualDialogue><Paragraph><Text>Good morning</Text></Paragraph></DualDialogue></Content></FinalDraft>'
        self.assertEqual(word_count(self.file('.fdx', text)), 4)

    def test_docx_tables_and_accepted_revision_view(self):
        text = '<w:document xmlns:w="urn:word"><w:body><w:p><w:r><w:t>Hel</w:t></w:r><w:r><w:t>lo world</w:t></w:r><w:del><w:r><w:delText>deleted secret</w:delText></w:r></w:del><w:r><w:instrText>hidden field code</w:instrText></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:ins><w:r><w:t>New row</w:t></w:r></w:ins></w:p></w:tc></w:tr></w:tbl></w:body></w:document>'
        path = self.archive('.docx', {'word/document.xml': text, 'word/comments.xml': '<secret>secret comment</secret>', 'word/header1.xml': '<header>secret header</header>'})
        self.assertEqual(word_count(path), 4)

    def test_odt_and_flat_odt_exclude_annotations_and_change_history(self):
        text = '<office:document xmlns:office="urn:office" xmlns:text="urn:text"><office:body><office:text><text:tracked-changes><text:p>deleted history</text:p></text:tracked-changes><text:h>Heading</text:h><text:p>Hello<text:s/>world<office:annotation><text:p>secret comment</text:p></office:annotation></text:p></office:text></office:body></office:document>'
        self.assertEqual(word_count(self.archive('.odt', {'content.xml': text})), 3)
        self.assertEqual(word_count(self.file('.fodt', text)), 3)

    def test_rtf_unicode_controls_metadata(self):
        text = r'{\rtf1\ansi{\fonttbl{\f0 SECRET FONT;}}{\info{\title SECRET TITLE}}Hello \b world\b0\par caf\u233?}'
        self.assertEqual(word_count(self.file('.rtf', text)), 3)

    def test_html_no_metadata_script_style_or_inline_join_changes(self):
        text = '<html><head><title>secret title</title><style>hidden styles</style></head><body><p>hel<b>lo</b> world</p><script>secret script</script><div>Good morning</div></body></html>'
        self.assertEqual(word_count(self.file('.html', text)), 4)

    def test_abiword_and_gzip_body_only(self):
        text = '<abiword><metadata><m>secret title</m></metadata><section><p>Hello <c>world</c></p></section><section type="header"><p>secret header</p></section><data>secret attachment</data></abiword>'
        self.assertEqual(word_count(self.file('.abw', text)), 2)
        path = self.folder / 'private.zabw'
        path.write_bytes(gzip.compress(text.encode()))
        self.assertEqual(word_count(path), 2)

    def epub_members(self, href='text/chapter.xhtml'):
        return {'META-INF/container.xml': '<container><rootfiles><rootfile full-path="OPS/book.opf"/></rootfiles></container>',
                'OPS/book.opf': '<package><metadata>secret title</metadata><manifest><item id="chapter" href="' + href + '" media-type="application/xhtml+xml"/><item id="nav" href="nav.xhtml" properties="nav" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="chapter"/><itemref idref="nav"/></spine></package>',
                'OPS/text/chapter.xhtml': '<html><head><title>secret title</title></head><body><p>Hello world</p></body></html>',
                'OPS/nav.xhtml': '<html><body>secret navigation</body></html>',
                'OPS/unused.xhtml': '<html><body>unused chapter</body></html>'}

    def test_epub_reads_only_linear_spine_chapters(self):
        self.assertEqual(word_count(self.archive('.epub', self.epub_members())), 2)

    def test_epub_rejects_remote_and_missing_chapters(self):
        for href in ('https://private.example/chapter.xhtml', '../../../outside.xhtml', 'missing.xhtml'):
            with self.subTest(href=href), self.assertRaises(ScriptError):
                word_count(self.archive('.epub', self.epub_members(href)))

    def test_pdf_text_and_image_only_rejection(self):
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
        path = self.folder / 'private.pdf'
        writer = PdfWriter()
        page = writer.add_blank_page(width=612, height=792)
        with path.open('wb') as f:
            writer.write(f)
        with self.assertRaisesRegex(ScriptError, 'No selectable'):
            word_count(path)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
        stream = DecodedStreamObject()
        stream.set_data(b'BT /F1 12 Tf 40 700 Td (Hello world) Tj ET')
        page[NameObject('/Contents')] = writer._add_object(stream)
        with path.open('wb') as f:
            writer.write(f)
        self.assertEqual(word_count(path), 2)
        writer.encrypt('secret')
        with path.open('wb') as f:
            writer.write(f)
        with self.assertRaisesRegex(ScriptError, 'Encrypted'):
            word_count(path)

    def test_unsupported_and_corrupt_files_do_not_become_zero(self):
        for ext in ('.doc', '.pages', '.scrivx', '.gdoc', '.docx', '.fdx', '.rtf', '.epub'):
            with self.subTest(ext=ext), self.assertRaises(ScriptError):
                word_count(self.file(ext, 'secret invalid document'))

    def test_file_picker_lists_formats(self):
        for ext in ('.fdx', '.docx', '.odt', '.md', '.fountain', '.rtf', '.epub', '.pdf', '.abw'):
            self.assertIn('*' + ext, file_filter())

    def test_unchanged_files_are_not_reparsed(self):
        from unittest.mock import patch
        path = self.file('.txt', 'Hello world')
        tracker = Tracker(path, 'Writing', 100)
        with patch('writewatch.core.extract_text', wraps=extract_text) as parser:
            tracker.observe()
            tracker.observe()
            parser.assert_not_called()
            tracker.finish()
            parser.assert_called_once()

    def test_live_text_atomic_save_and_numeric_only_history(self):
        path = self.file('.md', 'Secret beginning')
        tracker = Tracker(path, 'Writing', 100)
        replacement = self.file('.tmp', 'Secret beginning with three additions')
        replacement.replace(path)
        tracker.observe()
        self.assertEqual(tracker.session.net, 3)
        session = tracker.finish()
        store = Store(self.folder / 'history.sqlite3')
        store.save(session)
        self.assertEqual(store.history()[0].net, 3)
        store.close()
        self.assertNotIn(b'Secret', (self.folder / 'history.sqlite3').read_bytes())
        self.assertNotIn('private.md', session.summary())


if __name__ == '__main__':
    unittest.main()
