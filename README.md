# WriteWatch

A local Windows/macOS/Linux writing companion for Fade In, Final Draft, Word, LibreOffice, Markdown editors and more. Start a writing session, finish it, and copy your progress into your writers group. Your document stays on your computer.

## Download

Download the latest **prerelease** from [Releases](https://github.com/JPLuker/WriteWatch/releases).

- **Windows x64:** run `WriteWatch-…-Windows-Setup.exe` (per-user installer), or extract the portable ZIP and run `WriteWatch.exe` inside its folder. Keep `_internal` alongside the executable. The initial builds are unsigned; Windows may show its unknown-publisher prompt.
- **macOS 15+:** download the AppleSilicon DMG for M-series Macs or the Intel DMG for Intel Macs. Open it and drag WriteWatch into Applications. ZIP bundles are also available. These builds are ad-hoc signed for bundle integrity, but are **not Developer ID signed or notarized**. If the first launch is blocked, use System Settings → Privacy & Security → Open Anyway for this app. See [Mac installation notes](packaging/MAC_INSTALL.md).
- **Linux x86_64:** make the AppImage executable in its Properties → Permissions and run it. If FUSE is unavailable, launch with `--appimage-extract-and-run`. Alternatively, extract the `.tar.gz` and run `WriteWatch/WriteWatch`. Targets Ubuntu 24.04 and similarly recent distributions (glibc 2.39+); Wayland and X11 use Qt. No keyboard hooks or compositor extensions.
- Each main-branch build also provides downloads under [Actions](https://github.com/JPLuker/WriteWatch/actions). Successful versioned main-branch builds publish downloadable testing prereleases after all four platform builds pass. These are available for hands-on testing, not a claim of validation on every desktop. Published binaries are never replaced; each change requires a version bump.

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

## Updates (0.10.0+)

In **Settings → Updates**, choose **Stable** (the default) or **Testing**. Stable ignores GitHub prereleases; Testing includes them. Select **Testing** to receive our ongoing development builds. Neither channel downgrades your installed version. Switching channels clears any pending update from the previous channel; use **Check for updates** to check the new selection.

Automatic checks run at most once per 24 hours, with the last attempt saved across restarts. A manual check is always available and starts a new 24-hour window. Failures count as attempts to avoid repeated network requests. Clock rollback rebases the timestamp and postpones automatic checks for a day. Disable the automatic checkbox to stop automatic checks; source builds make no automatic requests.

| Installation | Update behavior |
| --- | --- |
| Windows installer | Check, verify and download; restart to run the installer |
| Linux AppImage | Check, verify and download; restart to replace the AppImage |
| Windows portable | Check and notify; download and replace manually |
| Linux DEB | Check and notify; install the new DEB through the system package installer |
| Linux tar archive | Check and notify; download and replace manually |
| Current macOS builds | Check and notify; install manually (ad-hoc signed, not notarized) |
| Source | Manual updates |

Downloads are verified against GitHub's file size and SHA-256 metadata. Finish your session before restarting to update. AppImages must be in a writable folder and keep the previous executable with a `.previous-…` suffix for recovery. History stays in the app data folder. Cached installers and logs can be cleared in **Data & storage**. DEB packages do not configure an APT repository.

Set `WRITEWATCH_DISABLE_UPDATES=1` to disable updater checks and installation entirely. Windows administrators can also set `DisableUpdates` (DWORD `1`) under `HKLM\SOFTWARE\Policies\WriteWatch` or `HKCU\SOFTWARE\Policies\WriteWatch`; either enabled policy disables the updater. Installation failures are recorded in `updates/last-update.log`.

## Appearance

WriteWatch follows [DESIGN.md](DESIGN.md). **Settings** offers System (default), Light and Dark themes, plus an ambient-background toggle. Qt uses the design system’s opaque material fallback and static ambient light. Format and privacy details expand on demand; history goal details live in session review. Update controls are now in Settings.

### Session workflow

Choose a session type, then open a file to start. Goals are optional and editable during a session. Setup is replaced by the active session view until you finish. The top-right menu opens Session, History or Settings. Formats and Privacy are in **Settings → About WriteWatch**. Navigating away does not pause or end a session.

### Linux installer (.deb)

Use the `amd64.deb` download on Ubuntu 24.04 or newer compatible Debian-based systems (glibc 2.39+). Install with your software installer, or from the download folder:

```bash
sudo apt install ./WriteWatch-0.6.1-amd64.deb
```

WriteWatch appears in the application menu. Remove with `sudo apt remove writewatch`; personal history remains in your user data folder. Install a newer `.deb` the same way to upgrade. Starting in 0.8.1, the `.deb` automatically checks for newer versions and shows an update notice with a release-download button. Install 0.8.1 manually once to get these checks. The `.deb` is managed by the system package manager and does not replace itself through the in-app updater. There is no apt repository configured for automatic upgrades. The AppImage remains available and supports in-app updates.

Session setup now uses Writing / Revision and No goal / Set goal toggles. A target appears only for Set goal; writing targets count net words, revision targets count minutes.

Goal controls are now under **Goal settings** at the bottom left of setup. Save applies the selected target; Cancel or Escape restores the previous choice. **Start session** stays on the bottom right.

### History compatibility

The page-goal update upgrades history to schema version 1, retaining all existing sessions and backing up the old database as `history.sqlite3.backup-v0` before migration. Newer unknown schema versions are refused. Older WriteWatch releases do not understand the additional page fields; to downgrade, first preserve your current database and restore the pre-migration backup (sessions created after the backup will not be available in the old app).

A failed final file read now offers a choice to retry later or finish using the last recorded counts. Negative net words are retained as valid session results.

### Revision metrics (0.8.0)

Revision sessions show **words added** and **words removed** in the active view, history summaries, copied text and share images. Totals accumulate differences in word occurrences between observed saves. Equal-length word substitutions can therefore register activity even when net words stays at zero. Case changes count; punctuation-only changes and moving/reordering existing words do not. Changes undone before the next observation cannot be measured; saved undos and repeated rewrites count again. These are change totals, not typing counts or a quality score. Paused edits remain excluded.

The parser extracts text locally, then builds session-keyed word fingerprints in memory. No text or fingerprints are saved in history or sent anywhere. Only numeric totals persist. Switching session mode retains totals for the whole session. Older sessions do not acquire invented revision totals.

History schema version 2 backs up the previous database before adding these numeric fields. Keep the backup if you need to return to an older WriteWatch version.

## Backups and data controls (0.9.0+)

Finish your active session, then open **Settings → Data & storage**:

- **Export everything…** saves an open, versioned JSON backup of completed/interrupted sessions, appearance/update preferences and recent-file paths. It contains no document text. Keep the backup private if your file paths are sensitive.
- **Import backup…** validates the entire backup before adding history. Existing session IDs win; importing the same backup twice does not duplicate sessions. Appearance, update preferences and recent files are replaced after confirmation. New history rows are committed together or rolled back together. A settings-write failure is reported separately.
- **Open data folder** opens the local storage location.
- **Clear update downloads and logs** removes cached packages and updater logs, including any pending downloaded update; check again to download it later. History and preferences are kept.
- **Delete all app data…** confirms removal of history, settings, recent paths, migration backups, updater downloads and logs, then quits. Documents and exported JSON backups are kept. This is not forensic secure erasure and cannot remove operating-system backups.

Backup format version 2 includes the update-channel preference and accepts up to 32 MB. Version 1 backups remain importable and select Stable; 0.9.0 cannot import version 2 exports. Unknown versions, unsupported fields, invalid measurements and inconsistent revision totals are rejected. Data controls that change or export data are unavailable during sessions or update checks/downloads.

**About → Copy diagnostic info** copies the app version, operating system, architecture and local data/log locations. It contains no recent document paths, document contents or session statistics; local storage paths may contain your account name. Nothing is sent automatically.

## Storage and retention (0.11.0+)

History and preferences now use standard platform locations. Existing default-location data is copied automatically on first launch; an existing destination history is never overwritten. SQLite's backup API includes committed WAL data. Both old and new locations are locked while this version is running. Failed migrations preserve the original files and can be retried after fixing permissions or disk space.

| Platform | History and preferences | Update cache | Update logs |
| --- | --- | --- | --- |
| Windows | `%APPDATA%/io.github.jpluker.writewatch` | `%LOCALAPPDATA%/io.github.jpluker.writewatch/cache` | `%LOCALAPPDATA%/io.github.jpluker.writewatch/logs` |
| Linux | `$XDG_DATA_HOME/writewatch` | `$XDG_CACHE_HOME/writewatch` | `$XDG_STATE_HOME/writewatch/logs` |
| macOS | `~/Library/Application Support/io.github.jpluker.writewatch` | `~/Library/Caches/io.github.jpluker.writewatch` | `~/Library/Logs/io.github.jpluker.writewatch` |

Linux defaults are `~/.local/share`, `~/.cache`, and `~/.local/state` when the respective XDG variable is unset or relative. **Open data folder** and **Copy diagnostic info** show the actual locations.

`WRITEWATCH_DATA_DIR` continues to use exactly the specified folder for history/settings, with `updates` and `logs` subfolders; it does not migrate another profile. For a portable Windows profile, create an empty `WriteWatch.portable` file beside `WriteWatch.exe`; storage then lives in an adjacent `data` folder. An explicit environment override takes precedence over the marker. Portable profiles start independently; import an exported backup to transfer history.

Original default-location data remains as a recovery copy. Older app versions still use that old location, so do not alternate versions expecting their histories to stay synchronized. **Delete all app data** also removes retained app-owned legacy files, preserving documents and exported backups. Removing only the new data folder manually can cause legacy data to be imported again.

Startup and daily cleanup remove recognized update downloads/helpers/logs older than 14 days. A currently pending update is protected, and cleanup is deferred while an update worker runs. Rotated update logs share a 10 MB retention budget; logs modified within the last minute are left alone for active helpers and reconsidered at the next cleanup. Unknown files, directories and symlinks are not followed or removed by automatic cleanup. Manual cache clearing remains available. Migration recovery copies are retained until full app-data deletion; AppImage executable rollback copies beside the app are also kept for manual recovery.

## Download names (0.11.2+)

Release notes group downloads by platform. Canonical names include platform and architecture, such as `WriteWatch-0.11.2-Linux-x64.deb`, `WriteWatch-0.11.2-Windows-x64-Setup.exe`, and `WriteWatch-0.11.2-macOS-arm64.dmg`.

Older filenames remain attached as identical compatibility aliases so previously shipped updaters keep working. New updater clients prefer canonical names and fall back to the legacy name. SHA256SUMS.txt covers both sets, and publication rejects mismatched aliases. Choose downloads from the table in the release notes; duplicate names in the asset list are compatibility copies, not different builds.

## Custom session metrics (0.12.0+)

Open **Settings → Metrics…** and choose Writing or Revision. Each mode has its own toggles, a reset-to-defaults button, and Save/Cancel. Writing defaults to time, net words, pages when applicable and goal progress. Revision additionally shows additions/removals. You can select none, a few, or all 12 metrics:

- Session time; net words; words added; words removed; total word changes.
- Net words per minute; word changes per minute.
- Observed changes; word changes per observation; removal share.
- Pages (manual or explicitly estimated); goal progress.

Selections apply to the live session, individual history reviews, copied summaries and share images. Disabled net-word/time values are omitted from history rows and aggregate word/time totals where appropriate. Session counts, dates, mode and history streak remain navigation/context information.

Toggles control display and sharing, not collection: local aggregate session statistics continue to be recorded so metrics can be re-enabled later. There is still no keystroke logging or stored script content. Pace divides saved word changes by the manual session clock; it is **not typing speed or active typing time**. Observed changes are saves/polls where word occurrences changed, **not every editor save**. Ratios with zero denominators and unavailable historical revision measurements are omitted. Word movement, punctuation-only edits and changes undone between observations are not captured.

Metric selections are stored in `metrics.ini` and included in JSON backup format 3. Versions 1/2 still import with default metric selections; older apps cannot import version 3 exports. Import replaces metric preferences after confirmation. History database schema remains version 2. Full app-data deletion removes metric preferences too.
