# WriteWatch

A local Windows/Linux writing companion for Fade In, Final Draft, Word, LibreOffice, Markdown editors and more. Start a writing session, finish it, and copy your progress into your writers group. Your document stays on your computer.

## Download

Download the latest **prerelease** from [Releases](https://github.com/JPLuker/WriteWatch/releases).

- **Windows x64:** run `WriteWatch-…-Windows-Setup.exe` (per-user installer), or extract the portable ZIP and run `WriteWatch.exe` inside its folder. Keep `_internal` alongside the executable. The initial builds are unsigned; Windows may show its unknown-publisher prompt.
- **Linux x86_64:** make the AppImage executable in its Properties → Permissions and run it. If FUSE is unavailable, launch with `--appimage-extract-and-run`. Alternatively, extract the `.tar.gz` and run `WriteWatch/WriteWatch`. Targets Ubuntu 24.04 and similarly recent distributions (glibc 2.39+); Wayland and X11 use Qt. No keyboard hooks or compositor extensions.
- Each main-branch build also provides downloads under [Actions](https://github.com/JPLuker/WriteWatch/actions). A successful main-branch build publishes a versioned prerelease automatically; bump the app version for each release.

## Your first session

1. Save your document in your editor.
2. Open WriteWatch and **Choose writing file**. Selection stays in memory and is not saved to history.
3. Pick **Writing** with a net-word goal, or **Revision** with a minute goal.
4. Click **Start session**, then write normally. WriteWatch checks your selected file every two seconds and parses it when it changes.
5. Save before **Pause** or **Done**. Resume excludes changes saved during the pause.
6. Click **Done — share progress**, then **Copy for writers group**. Paste it wherever you want. No automatic posting.

Example copied summary (no squares, script title or text):

```text
WriteWatch · Oct 15, 2026
Writing · Session complete
Goal progress: 100%
Time: 58m 00s · +624 net words
Goal: 500 net words
#WriteWatch
```

History lets you copy older sessions again and shows weekly totals and a writing streak. A PNG share card is optional. **Delete history** removes local completed/interrupted statistics; it never touches your script.

## What the numbers mean

- **Time** is the manual session timer minus pauses, not measured keyboard activity. It keeps running if you switch apps. A long suspension/event-loop stall pauses it.
- **Net words** compares saved document word counts, using format-specific extraction. See the compatibility table below. Counts may differ from your editor's report. Equal-length rewrites yield zero; deleted words can make the total negative.
- **Revision** goals use elapsed session minutes so editing needn't increase the word count.
- Unsaved changes cannot be measured. Save before finishing. Changes made and undone between checks cannot be reconstructed.
- Interrupted sessions keep their most recent numeric checkpoint (normally within two seconds), appear as interrupted in history, and do not extend the completed-session streak. They are not automatically resumed.
- Week totals group sessions by their local start date; a session spanning midnight remains on its start day.

## Supported files and apps

Support follows the **saved format**, not the app name. Select the file that your editor actually updates. A one-time export will not track subsequent edits until you overwrite that same export.

| File type | Editors / workflow | Counting behavior |
| --- | --- | --- |
| `.fadein`, `.osf` | Fade In | Script body; excludes title page, notes and synopses |
| `.fdx` | Final Draft; local exports from WriterDuet / WriterSolo and other screenwriting tools | Script body; excludes title page and script notes |
| `.docx` | Microsoft Word, LibreOffice, ONLYOFFICE, WPS and compatible editors | Body and tables; includes insertions, excludes deletions and separate headers, footers, comments and footnotes |
| `.odt`, `.fodt` | LibreOffice Writer, OpenOffice Writer and compatible editors | Document text; excludes annotations, tracked-change history and notes |
| `.rtf` | Rich-text editors; Scrivener exports, Word exports | Extracted RTF text; editor-specific annotation behavior can vary |
| `.md`, `.markdown`, `.mdown` | Obsidian, Typora, MarkText, Zettlr, iA Writer and Markdown editors | Rendered CommonMark text; excludes YAML front matter, comments and link destinations; includes code text |
| `.fountain` | Fountain editors; screenplay exports | Excludes initial title metadata, notes, boneyards, sections and synopses |
| `.txt`, `.text` | Notepad, Kate, Gedit, VS Code and text editors | Plain text; UTF-8 or BOM-marked UTF-16 |
| `.html`, `.htm`, `.xhtml` | HTML editors and local web exports | Text without head/script/style/template content; CSS visibility is not evaluated |
| `.epub` | Sigil, calibre's ebook editor, ebook exports | Linear text chapters in reading order; skips navigation and non-linear extras |
| `.pdf` | Selectable-text exports from writing apps | Extracted text, including headers, footers and page numbers; no OCR or encrypted PDFs |
| `.abw`, `.zabw` | AbiWord | Main document sections; excludes header/footer sections and annotations |

**Google Docs, Notion, Pages, Scrivener, Ulysses and cloud/project formats:** export to a supported local format, then refresh that file as you work. Native `.gdoc`, `.pages`, `.scrivx`, legacy `.doc`, and browser storage are not supported. This app cannot observe edits that never reach the selected file. Nothing is fetched from online accounts or links inside documents.

The **Formats & apps** tab gives the same guidance in the app. Files and extracted text have a 16 MB limit; PDFs have a 1,000-page limit. UTF-8 and BOM-marked UTF-16 are supported for plain/markup text; XML follows its encoding declaration and RTF follows its control words. PDFs and exports can give approximate counts; use your native editable format when available. Each session still watches one file.

Adapter references: [WordprocessingML](https://learn.microsoft.com/en-us/office/open-xml/word/structure-of-a-wordprocessingml-document), [OpenDocument](https://docs.oasis-open.org/office/v1.3/OpenDocument-v1.3-part3-schema.html), [EPUB](https://www.w3.org/TR/epub-33/), [Fountain](https://fountain.io/syntax/).

## Privacy

No network requests, accounts, telemetry, global typing hooks, script snapshots or script uploads. Only aggregate session statistics are persisted. See [PRIVACY.md](PRIVACY.md).

## Development

Requires Python 3.12+.

```sh
python -m venv .venv
# Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m writewatch
python -m unittest discover -v
```

Build **on each target OS**:

```sh
python -m pip install -r requirements-build.txt
python packaging/build.py
# Linux AppImage: bash packaging/appimage.sh
# Windows installer: ISCC packaging/windows.iss (Inno Setup 6)
```

CI runs parser, session, privacy, clipboard and UI tests on Windows and Linux before packaging. Source verification does not replace testing with your actual documents and desktop. Format adapters have fixture tests; unusual files still need hands-on validation.

## Project status

0.2.0 is a testing release with 12 format families / 20 file extensions. No official relationship with Fade In. This repository currently grants no license to WriteWatch source; Joseph retains rights. Dependency notices are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
