# WriteWatch privacy model

The application opens the file you choose read-only. It temporarily parses its screenplay body to count words. It does not modify the script, save text snapshots, send requests over a network, log your typing, read your clipboard, or publish to any service.

## Stored data

The SQLite session table contains ONLY:

- Random session ID
- Session start timestamp and timezone offset
- Writing/revision mode and numeric goal
- Accumulated manual timer seconds
- Net word-count change
- Number of observations where the word count changed
- Running, paused, completed or interrupted state

No filename, path, script title, character name, word list, content hash or text is stored in this database. A selected file path and last observed word count exist in memory until the application closes. Script content exists transiently while parsing; this is not a promise of protection from operating-system swap, memory inspection, or crash dumps.

History is stored in Qt's AppLocalDataLocation (normally `%LOCALAPPDATA%/WriteWatch/WriteWatch` on Windows and `~/.local/share/WriteWatch/WriteWatch` on Linux). An optional `WRITEWATCH_DATA_DIR` environment variable overrides that storage folder (useful for portable installs). History → Delete history clears completed/interrupted rows and vacuums the database. This is not forensic secure erasure and cannot delete OS backups. Removing the app does not automatically erase history.

## Sharing

The Done dialog shows the exact text copied. It contains only session type, date, duration, net words and goal progress. The optional PNG is rendered from those same numeric/session fields. No script text or image of the editor is included. The clipboard or a saved PNG can be retained by your OS, backup tools or clipboard-sync service. Posting to your group is your action.

## Failure behavior

Unreadable/partially saved files preserve the last good count and show a generic error without XML content or paths. A failed final read leaves the session open for retry. Numeric checkpoints allow interrupted-session recovery after a crash. A single-instance lock prevents simultaneous writers from duplicating/recovering one another's active sessions. No automatic update checks are included.
