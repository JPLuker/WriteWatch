# WriteWatch privacy model

The application opens the file you choose read-only. It temporarily parses its document text to count words. It does not modify the script, save text snapshots, log your typing, read your clipboard, or publish to any service.

## Stored data

The SQLite session table contains ONLY:

- Random session ID
- Session start timestamp and timezone offset
- Writing/revision mode, goal unit and numeric goal (zero records a skipped goal)
- Self-reported pages and the words-per-page value used for estimates
- Accumulated manual timer seconds
- Net word-count change, cumulative word additions/removals, and whether those revision metrics were collected
- Number of observations where word occurrences changed
- Running, paused, completed or interrupted state

No filename, path, script title, character name, word list, content fingerprint or text is stored in this database. Recent file paths (up to ten) are saved separately in `recents.ini` beside the history database. Settings → Files can disable or clear this list; paths never enter shared summaries. File size/modification/inode signatures, session-keyed word fingerprints and occurrence counts remain in memory. The random key changes with each session; fingerprints are never persisted or transmitted, and are discarded after successfully finishing. Script content exists transiently while parsing; this is not a promise of protection from operating-system swap, memory inspection, or crash dumps.

History is stored in Qt's AppLocalDataLocation (normally `%LOCALAPPDATA%/WriteWatch/WriteWatch` on Windows and `~/.local/share/WriteWatch/WriteWatch` on Linux, and `~/Library/Application Support/WriteWatch/WriteWatch` on macOS). An optional `WRITEWATCH_DATA_DIR` environment variable overrides that storage folder (useful for portable installs). History → Delete history clears completed/interrupted rows and vacuums the database. This is not forensic secure erasure and cannot delete OS backups. Removing the app does not automatically erase history.

## Backups and deletion

Settings → Data & storage exports session statistics, preferences and recent-file paths to a JSON file you choose. Exports contain no document contents; filenames and paths in the recent list may still be sensitive. Import validates the full backup, merges session history without overwriting matching IDs and replaces preferences after confirmation. No backup is uploaded.

Delete all app data removes the app-owned history database, migration backups, preferences, recent-file list, update cache and update logs, then quits. It preserves documents, exported backups and unrelated files in the same directory. It does not securely erase disk sectors or remove OS/cloud backups. Cache clearing keeps history and preferences. About can copy diagnostics containing app/OS versions and local storage paths (which may include your account name), but no document paths or contents. Diagnostics are not sent automatically.

## Sharing

The Done dialog shows the exact text copied. It contains only session type when relevant, date, duration, net words, revision additions/removals when collected, labeled page measurements and goal progress. The optional PNG is rendered from those same numeric/session fields. No script text or image of the editor is included. The clipboard or a saved PNG can be retained by your OS, backup tools or clipboard-sync service. Posting to your group is your action.

## Failure behavior

Unreadable/partially saved files preserve the last good count and show a generic error without XML content or paths. A failed final read offers retry or finishing with the last recorded counts; finishing requires explicit confirmation. Numeric checkpoints allow interrupted-session recovery after a crash. A single-instance lock prevents simultaneous writers from duplicating/recovering one another's active sessions.

All format adapters operate locally. Links in Markdown, HTML, EPUB, DOCX or other documents are never followed over the network. Archives are read in memory without extracting their paths onto disk. XML entities are disabled. Encrypted PDFs and external EPUB chapters are rejected. New formats do not add any fields to stored history or shared summaries.

## Optional software updates

Packaged installations can check GitHub's public WriteWatch releases at most daily; the last check attempt is stored locally across restarts. Manual checks are available. Stable is the default update channel and excludes prereleases; Testing must be selected to receive development builds. The selected channel is included in exported backups; operational check timestamps are not.

Windows installers and AppImages download compatible updates. DEB, Linux tar, portable Windows and current macOS builds only check and notify; installation remains manual. Source builds do not check automatically. Disable automatic checks in Settings → Updates to stop automatic requests; manual checks still work. `WRITEWATCH_DISABLE_UPDATES=1` or the documented Windows policy disables updater requests and installation entirely.

Requests contain the app version in the user agent. GitHub and its download infrastructure receive normal connection metadata, including your IP address, and the requested platform-specific asset. No document text, filenames, document paths, goals or session statistics are sent. There is no account, token, analytics or tracking identifier. Preferences and downloaded update packages are stored locally separately from history. Downloads are checked using GitHub's published size and SHA-256 checksum. This verifies integrity against release metadata; it is not an independent publisher signature.
