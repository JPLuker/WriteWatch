# WriteWatch

A local Windows/macOS/Linux writing companion for Fade In, Final Draft, Word, LibreOffice, Markdown editors and more. Start a writing session, finish it, and copy your progress into your writers group. Your document stays on your computer.

## Download

Download the latest **prerelease** from [Releases](https://github.com/JPLuker/WriteWatch/releases).

- **Windows x64:** run `WriteWatch-…-Windows-Setup.exe` (per-user installer), or extract the portable ZIP and run `WriteWatch.exe` inside its folder. Keep `_internal` alongside the executable. The initial builds are unsigned; Windows may show its unknown-publisher prompt.
- **macOS 15+:** download the AppleSilicon DMG for M-series Macs or the Intel DMG for Intel Macs. Open it and drag WriteWatch into Applications. ZIP bundles are also available. These builds are ad-hoc signed for bundle integrity, but are **not Developer ID signed or notarized**. If the first launch is blocked, use System Settings → Privacy & Security → Open Anyway for this app. See [Mac installation notes](packaging/MAC_INSTALL.md).
- **Linux x86_64:** make the AppImage executable in its Properties → Permissions and run it. If FUSE is unavailable, launch with `--appimage-extract-and-run`. Alternatively, extract the `.tar.gz` and run `WriteWatch/WriteWatch`. Targets Ubuntu 24.04 and similarly recent distributions (glibc 2.39+); Wayland and X11 use Qt. No keyboard hooks or compositor extensions.
- Each main-branch build also provides downloads under [Actions](https://github.com/JPLuker/WriteWatch/actions). Main-branch builds provide development artifacts. Tagged builds prepare a draft release for validation before publication.

## Your first session

1. Save your document in your editor.
2. Pick Writing or Revision, then **Open file**. Selecting a readable file starts the session immediately. Recent files appear here after the first successful selection.
3. Use **Goal settings** before or during a session: Words, Pages, Minutes, or No goal. Changing a target does not reset progress.
4. For Pages, choose **Enter pages** to record pages completed/reviewed yourself, or **Estimate** to divide net words by a configurable words-per-page value (default 250). Estimates are not your editor's pagination. Manual page totals can include rereading and revision without word-count growth.
5. Save before **Pause** or **Finish session**. Resume excludes changes saved during the pause.
6. Select **Copy**, then paste wherever you want. No automatic posting. Revision summaries retain their mode label; ordinary writing summaries omit it.

Settings → Files lets you disable or clear recent files. These local paths are separate from session history and never appear in shared summaries.

Example copied summary (no squares, script title or text):

```text
WriteWatch · Oct 15, 2026
Session complete
Goal progress: 100%
Time: 58m 00s · +624 net words
Goal: 500 net words
#WriteWatch
```

History saves completed and interrupted sessions locally across restarts. Filter by date range or Writing/Revision, then select **Review session** (or double-click a row) to see its date, time, net words, target and result. You can copy or export it again from that review. Weekly totals and a writing streak remain visible. Skipped goals show “No goal set” in history and are omitted from shared summaries. A PNG share card is optional. **Delete history** removes local completed/interrupted statistics; it never touches your script.

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

**Settings → About WriteWatch → Formats** gives the same guidance in the app. Files and extracted text have a 16 MB limit; PDFs have a 1,000-page limit. UTF-8 and BOM-marked UTF-16 are supported for plain/markup text; XML follows its encoding declaration and RTF follows its control words. PDFs and exports can give approximate counts; use your native editable format when available. Each session still watches one file.

Adapter references: [WordprocessingML](https://learn.microsoft.com/en-us/office/open-xml/word/structure-of-a-wordprocessingml-document), [OpenDocument](https://docs.oasis-open.org/office/v1.3/OpenDocument-v1.3-part3-schema.html), [EPUB](https://www.w3.org/TR/epub-33/), [Fountain](https://fountain.io/syntax/).

## Privacy

No accounts, telemetry, global typing hooks, script snapshots or script uploads. Optional automatic updates contact GitHub for release metadata and app downloads; no writing or session data is sent. Only aggregate session statistics are persisted. See [PRIVACY.md](PRIVACY.md).

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
# macOS: build.py also creates the DMG and app ZIP on the native architecture
```

CI runs parser, session, privacy, clipboard and UI tests on Windows, Linux, Apple Silicon macOS and Intel macOS before packaging. Every packaged app also gets an isolated startup smoke test. Source verification does not replace testing with your actual documents and desktop. Format adapters have fixture tests; unusual files still need hands-on validation.

## Project status

0.8.0 is in development with 12 format families / 20 file extensions. No official relationship with Fade In. This repository currently grants no license to WriteWatch source; Joseph retains rights. Dependency notices are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Automatic updates (v0.4.0+)

Install v0.4.0 manually once to enable future updates. WriteWatch checks GitHub five seconds after launch and every six hours, including preview releases, then downloads the newest compatible version in the background. Turn this off in **Updates**, or use **Check for updates** manually. Downloads are verified against GitHub's size and SHA-256 metadata. Offline or failed checks leave the current app usable.

When **Update ready** appears, finish your session and select **Restart to Update**. Windows installer and portable builds, Linux AppImages, and installed macOS apps support this flow. The helper waits for WriteWatch to exit; it does not force-close a session. Session history remains in the app data folder. Portable, AppImage and Mac updates retain the previous app alongside the replacement with a `.previous-…` suffix for recovery. You can remove that backup after confirming the new version works. Downloaded installers are retained in the app data `updates` folder.

Run an AppImage from a writable folder. On Mac, first move WriteWatch out of the DMG into a writable Applications folder; disk-image and App Translocation launches cannot update themselves. Source and Linux tar builds use manual installation. macOS builds remain ad-hoc signed, not notarized. Updates do not bypass macOS security settings. Installation errors are recorded in `updates/last-update.log` in the app data folder.

Set `WRITEWATCH_DISABLE_UPDATES=1` to disable the updater completely, including network access, for managed deployments and tests.

## Appearance

WriteWatch follows [DESIGN.md](DESIGN.md). **Settings** offers System (default), Light and Dark themes, plus an ambient-background toggle. Qt uses the design system’s opaque material fallback and static ambient light. Format and privacy details expand on demand; history goal details live in session review. Update controls are now in Settings.

### Session workflow

Choose a session type, then open a file to start. Goals are optional and editable during a session. Setup is replaced by the active session view until you finish. The top-right menu opens Session, History or Settings. Formats and Privacy are in **Settings → About WriteWatch**. Navigating away does not pause or end a session.

### Linux installer (.deb)

Use the `amd64.deb` download on Ubuntu 24.04 or newer compatible Debian-based systems (glibc 2.39+). Install with your software installer, or from the download folder:

```bash
sudo apt install ./WriteWatch-0.6.1-amd64.deb
```

WriteWatch appears in the application menu. Remove with `sudo apt remove writewatch`; personal history remains in your user data folder. Install a newer `.deb` the same way to upgrade. The `.deb` is managed by the system package manager and does not replace itself through the in-app updater. There is no apt repository configured for automatic upgrades. The AppImage remains available and supports in-app updates.

Session setup now uses Writing / Revision and No goal / Set goal toggles. A target appears only for Set goal; writing targets count net words, revision targets count minutes.

Goal controls are now under **Goal settings** at the bottom left of setup. Save applies the selected target; Cancel or Escape restores the previous choice. **Start session** stays on the bottom right.

### History compatibility

The page-goal update upgrades history to schema version 1, retaining all existing sessions and backing up the old database as `history.sqlite3.backup-v0` before migration. Newer unknown schema versions are refused. Older WriteWatch releases do not understand the additional page fields; to downgrade, first preserve your current database and restore the pre-migration backup (sessions created after the backup will not be available in the old app).

A failed final file read now offers a choice to retry later or finish using the last recorded counts. Negative net words are retained as valid session results.

### Revision metrics (0.8.0)

Revision sessions show **words added** and **words removed** in the active view, history summaries, copied text and share images. Totals accumulate differences in word occurrences between observed saves. Equal-length word substitutions can therefore register activity even when net words stays at zero. Case changes count; punctuation-only changes and moving/reordering existing words do not. Changes undone before the next observation cannot be measured; saved undos and repeated rewrites count again. These are change totals, not typing counts or a quality score. Paused edits remain excluded.

The parser extracts text locally, then builds session-keyed word fingerprints in memory. No text or fingerprints are saved in history or sent anywhere. Only numeric totals persist. Switching session mode retains totals for the whole session. Older sessions do not acquire invented revision totals.

History schema version 2 backs up the previous database before adding these numeric fields. Keep the backup if you need to return to an older WriteWatch version.
