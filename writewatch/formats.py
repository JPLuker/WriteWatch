"""Read-only adapters. Only integer word counts escape this module."""
from __future__ import annotations
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
import gzip
import logging
import re
import zipfile

from defusedxml import ElementTree
from markdown_it import MarkdownIt
from striprtf.striprtf import rtf_to_text

MAX_BYTES = 16 * 1024 * 1024
WORDS = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*", re.UNICODE)
FORMATS = {
    'Fade In / OSF': ('.fadein', '.osf'),
    'Final Draft': ('.fdx',),
    'Word document': ('.docx',),
    'OpenDocument': ('.odt', '.fodt'),
    'Rich text': ('.rtf',),
    'Markdown': ('.md', '.markdown', '.mdown'),
    'Fountain': ('.fountain',),
    'Plain text': ('.txt', '.text'),
    'HTML': ('.html', '.htm', '.xhtml'),
    'EPUB': ('.epub',),
    'PDF (selectable text)': ('.pdf',),
    'AbiWord': ('.abw', '.zabw'),
}
EXTENSIONS = {ext for extensions in FORMATS.values() for ext in extensions}


class ScriptError(ValueError):
    pass


def file_filter():
    all_patterns = ' '.join('*' + ext for ext in sorted(EXTENSIONS))
    return 'Supported writing files (' + all_patterns + ');;' + ';;'.join(
        name + ' (' + ' '.join('*' + ext for ext in extensions) + ')'
        for name, extensions in FORMATS.items())


def format_name(path):
    return next((name for name, exts in FORMATS.items() if path.suffix.lower() in exts), 'Unsupported')


def count(text):
    return len(WORDS.findall(text))


def bounded(data):
    if len(data) > MAX_BYTES:
        raise ScriptError('This document exceeds the 16 MB text safety limit.')
    return data


def decode(data):
    # UTF-16 needs a BOM; all other plain-text files must be UTF-8.
    return data.decode('utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')


def xml(data):
    root = ElementTree.fromstring(data)
    for node in root.iter():
        node.tag = node.tag.split('}')[-1]
    return root


def member(archive, name):
    info = archive.getinfo(name)
    if info.file_size > MAX_BYTES:
        raise ScriptError('This document exceeds the 16 MB text safety limit.')
    return bounded(archive.read(info))


def flow(node, skip=(), only=None):
    """Preserve inline run joins and paragraph/explicit whitespace boundaries."""
    if node.tag in skip:
        return ''
    parts = []
    if only is None or node.tag in only:
        parts.append(node.text or '')
    for child in node:
        parts.append(flow(child, skip, only))
        if only is None:
            parts.append(child.tail or '')
    if node.tag in ('p', 'h', 'Paragraph', 'para', 'br', 'tab', 's', 'line-break', 'cr'):
        parts.append('\n')
    return ''.join(parts)


class VisibleHTML(HTMLParser):
    BLOCKS = {'p','div','br','li','h1','h2','h3','h4','h5','h6','td','th','tr','section','article','hr','pre'}
    SKIP = {'head','script','style','template','noscript'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.hidden.append(tag)
        if not self.hidden and tag in self.BLOCKS:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if self.hidden and tag == self.hidden[-1]:
            self.hidden.pop()
        elif not self.hidden and tag in self.BLOCKS:
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def html_text(text):
    parser = VisibleHTML()
    parser.feed(text)
    parser.close()
    return ''.join(parser.parts)


def fountain(text):
    # Fountain's title-page metadata is an optional initial block.
    if re.match(r'(?i)^(title|credit|author|authors|source|draft date|contact|copyright|notes):', text):
        text = re.split(r'\n\s*\n', text, maxsplit=1)[-1] if re.search(r'\n\s*\n', text) else ''
    text = re.sub(r'/\*.*?\*/|\[\[.*?\]\]', '', text, flags=re.S)
    return '\n'.join(line for line in text.splitlines() if not re.match(r'^\s*(#|=(?!=))', line))


def epub(archive):
    container = xml(member(archive, 'META-INF/container.xml'))
    rootfile = container.find('.//rootfile')
    if rootfile is None:
        raise ValueError('missing package')
    package_path = rootfile.attrib['full-path']
    package = xml(member(archive, package_path))
    manifest = {item.attrib['id']: item for item in package.findall('./manifest/item')}
    spine = package.find('spine')
    if spine is None:
        raise ValueError('missing spine')
    total = consumed = 0
    seen = set()
    for ref in spine:
        item = manifest[ref.attrib['idref']]
        if ref.get('linear') == 'no' or 'nav' in item.get('properties', '').split():
            continue
        if item.get('media-type') not in ('application/xhtml+xml', 'text/html'):
            raise ScriptError('This EPUB has non-text chapters that cannot be counted reliably.')
        href = urlsplit(item.attrib['href'])
        if href.scheme or href.netloc:
            raise ScriptError('Remote EPUB chapters are not supported. Nothing was downloaded.')
        path = str(PurePosixPath(package_path).parent / unquote(href.path))
        # Normalize archive-only paths; never extract or open links on disk.
        import posixpath
        path = posixpath.normpath(path)
        if path.startswith('../') or path.startswith('/'):
            raise ValueError('invalid member path')
        if path in seen:
            continue
        seen.add(path)
        data = member(archive, path)
        consumed += len(data)
        if consumed > MAX_BYTES:
            raise ScriptError('This EPUB exceeds the 16 MB text safety limit.')
        total += count(html_text(decode(data)))
    return total


def word_count(path: Path) -> int:
    """Parse selected file only; never save content, resolve URLs or edit files."""
    try:
        ext = path.suffix.lower()
        if ext not in EXTENSIONS:
            raise ScriptError('Unsupported format. Save or export to one of the formats in the file picker.')
        if path.stat().st_size > MAX_BYTES:
            raise ScriptError('This file exceeds the 16 MB safety limit.')
        data = bounded(path.read_bytes())
        if ext in ('.fadein', '.osf', '.docx', '.odt', '.epub') and zipfile.is_zipfile(BytesIO(data)):
            with zipfile.ZipFile(BytesIO(data)) as archive:
                if ext == '.epub':
                    return epub(archive)
                name = 'word/document.xml' if ext == '.docx' else 'content.xml' if ext == '.odt' else 'document.xml'
                data = member(archive, name)
        if ext == '.epub':
            raise ValueError('EPUB must be a ZIP archive')
        if ext in ('.fadein', '.osf'):
            root = xml(data)
            paragraphs = root.find('paragraphs')
            if root.tag != 'document' or paragraphs is None:
                raise ValueError('not OSF')
            return sum(count(''.join(''.join(t.itertext()) for t in p.findall('text')))
                       for p in paragraphs.iter('para'))
        if ext == '.fdx':
            root = xml(data)
            body = root.find('Content')
            if root.tag != 'FinalDraft' or body is None:
                raise ValueError('not FDX')
            return sum(count(''.join(''.join(t.itertext()) for t in p.findall('Text')))
                       for p in body.iter('Paragraph'))
        if ext == '.docx':
            root = xml(data)
            body = root.find('body')
            if root.tag != 'document' or body is None:
                raise ValueError('not DOCX')
            return count(flow(body, skip={'del','moveFrom','instrText','Fallback'}, only={'t'}))
        if ext in ('.odt', '.fodt'):
            body = xml(data).find('./body/text')
            if body is None:
                raise ValueError('not ODT')
            return count(flow(body, skip={'annotation','tracked-changes','note','change-info'}))
        if ext in ('.abw', '.zabw'):
            if ext == '.zabw':
                with gzip.GzipFile(fileobj=BytesIO(data)) as compressed:
                    data = bounded(compressed.read(MAX_BYTES + 1))
            root = xml(data)
            if root.tag != 'abiword':
                raise ValueError('not AbiWord')
            return sum(count(flow(s, skip={'footnote','endnote','annotation'}))
                       for s in root.findall('section') if s.get('type', 'doc') == 'doc')
        if ext == '.rtf':
            text = data.decode('latin-1')
            if not text.lstrip().startswith('{\\rtf'):
                raise ValueError('not RTF')
            return count(rtf_to_text(text, errors='strict'))
        if ext == '.pdf':
            # pypdf diagnostics can contain source strings; keep them out of logs.
            logging.getLogger('pypdf').addHandler(logging.NullHandler())
            logging.getLogger('pypdf').propagate = False
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(data), strict=True)
            if reader.is_encrypted:
                raise ScriptError('Encrypted PDFs are not supported. Use an unencrypted text export.')
            if len(reader.pages) > 1000:
                raise ScriptError('PDFs are limited to 1,000 pages.')
            total = size = 0
            for page in reader.pages:
                text = page.extract_text() or ''
                size += len(text)
                if size > MAX_BYTES:
                    raise ScriptError('This PDF exceeds the text safety limit.')
                total += count(text)
            if not total:
                raise ScriptError('No selectable PDF text found. Export DOCX, RTF or plain text; OCR is not included.')
            return total
        text = decode(data)
        if '\x00' in text:
            raise ValueError('binary text')
        if ext in ('.md', '.markdown', '.mdown'):
            text = re.sub(r'\A---\s*\n.*?\n(?:---|\.\.\.)\s*(?:\n|$)', '', text, count=1, flags=re.S)
            text = html_text(MarkdownIt('commonmark').render(text))
        elif ext in ('.html', '.htm', '.xhtml'):
            text = html_text(text)
        elif ext == '.fountain':
            text = fountain(text)
        return count(text)
    except ScriptError:
        raise
    except Exception:
        raise ScriptError('Could not read the saved document. Save in your editor, then retry. Plain text must be UTF-8 or BOM-marked UTF-16.') from None
