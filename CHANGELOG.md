# Changelog

## [Unreleased]

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
