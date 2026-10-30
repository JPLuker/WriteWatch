- Protect writing files inside app cache/log folders: cleanup no longer recursively deletes directories.
- Preserve subfolders, links, hard-linked files and known watched document paths during cleanup.
- Require a new filename for backup exports and share images. Existing files are never overwritten by those exports.
- Refuse linked app-data files and unrelated history databases. Migration backups use unique filenames.
- Prevent update downloads, helper scripts and logs from overwriting existing files. AppImage staging collisions cancel the update.
- Keep document readers read-only; regression checks verify original bytes survive tracking, cleanup and failed exports.

Testing release. Hands-on session, upgrade/migration and backup validation remain before 1.0. Choose Settings → Updates → Testing for development builds.

Requires Windows x64, Linux glibc 2.39+, or macOS 15+. Windows binaries are unsigned; Mac bundles are not notarized. DEB installation uses the system package installer.
