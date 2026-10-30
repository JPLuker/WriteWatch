# Changelog

## [Unreleased]

## [0.14.1] — 2026-10-29
### Fixed
- Replace recursive cache/data deletion with file-by-file cleanup; preserve documents, nested folders, links and known watched paths.
- Refuse to overwrite existing backup exports or share images, including hard links and symbolic links.
- Refuse linked app-data files and unrelated history databases; keep unique migration backups and never replace migration destinations.
- Protect updater downloads, helper scripts and logs against overwriting existing files; use unique logs and partial-download names.
- Keep existing AppImage staging/backup files if an update filename collides.

## [0.14.0] — 2026-10-25
### Added
- Delete an individual completed or interrupted session from History, with confirmation identifying the selected session.
- Refresh weekly totals and streaks after deletion; keep filters and select a nearby remaining session.
### Changed
- Label the bulk action Delete all history to distinguish it from deleting one session.

## [0.13.1] — 2026-10-25
### Fixed
- Update the active goal when switching Writing/Revision, without resetting session progress or pause state.
- Restore each mode's chosen goal when switching back, including skipped goals and page estimates, for the current app run.

## [0.13.0] — 2026-10-25
### Changed
- Open History and Settings in separate, reusable windows while keeping the session screen in place.
- Simplify the hamburger menu to History and Settings, with larger rows and a consistent icon button.
- Put update notices on the Settings menu item without widening the hamburger button.
- Support the system Settings keyboard shortcut and Escape to close History or Settings.

## [0.12.0] — 2026-10-24
### Added
- Twelve configurable saved-file session metrics with separate Writing/Revision selections and reset-to-default controls.
- Apply selections to live sessions, session reviews, copied text and share images, and hide disabled word/time history values.
- Add derived change totals, session-average pace, changed observations, changes per observation and removal share.
### Changed
- Export metric preferences in backup format 3; versions 1 and 2 remain importable. History schema is unchanged.
- Omit unavailable measurements rather than inventing values for old sessions or zero denominators. Disabled metrics remain tracked as aggregate statistics.

## [0.11.2] — 2026-10-24
### Fixed
- Standardize platform/architecture download names and group release links by platform.
- Preserve identical legacy filename aliases for older updaters; prefer canonical names in new clients with legacy fallback.
- Validate alias contents and include all published packages in the checksum manifest.

## [0.11.1] — 2026-10-24
### Fixed
- Block publication of incomplete, empty or mismatched release package sets; generate checksums only after validation.
### Maintenance
- Add grouped weekly Dependabot checks for Python dependencies and Actions, plus private vulnerability-reporting guidance.

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
