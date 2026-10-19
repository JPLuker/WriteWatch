# Changelog

## [Unreleased]

## [0.11.0] — 2026-10-18
### Added
- Standard platform storage directories with copy-first migration of history/settings and locks for both old and new profiles.
- Separate update cache/log locations; explicit custom profiles and Windows portable marker support.
- Startup/daily updater cleanup with 14-day retention, pending-download protection and a 10 MB inactive-log budget.
### Changed
- Rotate update logs and include new cache/log locations in diagnostics.
- Clear retained legacy app-owned data during full deletion to prevent reimporting deleted history.

## [0.10.0] — 2026-10-18
### Added
- Stable/default and opt-in Testing update channels, preserved in version 2 backups; version 1 backups remain importable.
- Windows registry policy to disable updater checks and installation.
### Changed
- Persist update attempt timestamps across restarts and limit automatic checks to once per 24 hours.
- Keep restart-to-update for Windows installers and AppImages; make portable Windows, Linux tar/DEB and current macOS builds notify-only.
- Clear pending downloads from the active update action when switching channels, without downgrading installed versions.

## [0.9.0] — 2026-10-18
### Added
- Export and import versioned JSON backups of session history, preferences and recent-file paths, without document contents.
- Validate imports before writing and merge history transactionally, preserving existing session IDs.
- Open the data folder, clear update downloads/logs, and delete all app-owned data with confirmation before quitting.
- Copy diagnostic information from About without document names or contents.

### Fixed
- Retry transient macOS disk-image resource-busy failures during packaging, with a bounded retry count.

## [0.8.1] — 2026-10-18
### Fixed
- Enabled update checks and release-download notices for DEB installations. Package installation remains under the system package manager.
- Published successful versioned builds as downloadable testing releases with SHA-256 checksums.

## [0.8.0] — 2026-10-18
### Breaking
- Upgraded history to store revision totals, with a backup for returning to an older version.
### Added
- Added cumulative words added and removed to revision sessions, reviews and shared summaries.
### Changed
- Kept older session totals unavailable instead of displaying invented revision measurements.

## [0.7.0] — 2026-10-18
### Breaking
- Upgraded history for page goals; kept a pre-upgrade backup. Older app versions require restoring that backup to read history.
### Added
- Added page goals with self-reported progress or clearly labeled word-based estimates.
- Added recent files, with controls to clear or disable the list.
### Changed
- Started tracking immediately when a readable file is selected.
- Allowed goals and session mode to change during a session without resetting progress.
- Shortened the share button to “Copy” and omitted the default Writing label from copied summaries.
### Fixed
- Added an explicit option to finish with the last recorded counts when the final file save cannot be read.
