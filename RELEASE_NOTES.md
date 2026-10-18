- Added Settings → Data & storage: export/import JSON backups, open data folder, clear update downloads/logs, and delete all app data with confirmation before quitting.
- Backups contain aggregate session history, preferences and recent-file paths, never document text. Keep exports private if paths are sensitive.
- Imports reject invalid backups before writing. Existing session IDs are preserved and new rows are merged in one transaction; settings-write failures are reported separately.
- Added Copy diagnostic info in About. Includes local storage locations, not document names or contents.
- Includes 0.8.1 DEB update notifications. Existing older DEB users must install a new DEB manually once; installation uses the system package installer, with no APT repository configured.

Testing build: automated tests and packaging checks run on Windows, Linux and both Mac architectures. Hands-on desktop validation remains outstanding; this is not final 1.0.

Requires Windows x64, Linux glibc 2.39+, or macOS 15+. Windows builds are unsigned; Mac builds are not notarized. SHA256SUMS.txt is included.

History schema remains version 2. Upgrading from versions before 0.8.0 creates a migration backup; downgrading across that migration requires restoring the old database backup.
