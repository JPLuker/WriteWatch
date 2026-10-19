- Added standard platform data, cache and log locations with automatic copy-first migration from the old default profile. Existing destination history is never overwritten; original data remains for recovery.
- Added startup/daily cleanup of recognized updater files older than 14 days, pending-update protection, rotated logs and a 10 MB inactive-log retention budget.
- Kept WRITEWATCH_DATA_DIR profiles in place. Windows portable copies can use an adjacent WriteWatch.portable marker to store an independent profile in data/.
- Diagnostics show current data/cache/log locations. Clear downloads and Delete all app data include the appropriate new and retained legacy locations.
- History and JSON backup formats are unchanged from 0.10.0. Older app versions use the original location and do not see new sessions from this version.

Select Settings → Updates → Testing to receive development builds; Stable is the default. DEB updates still require installation through the system package installer.

Testing release with automated migration, retention, update and session tests plus package/startup checks on all four platform runners. Hands-on upgrade validation remains outstanding.

Requires Windows x64, Linux glibc 2.39+, or macOS 15+. Windows builds are unsigned; Mac builds are not notarized. SHA256SUMS.txt is included.
