- Standardized download filenames to include platform and architecture, with grouped download links above.
- Kept identical legacy filename aliases so older updaters continue to work. New clients prefer canonical names and retain legacy fallback.
- Release validation rejects mismatched aliases and checksums cover every attached package.

No changes to session tracking, history schema or backup format. Includes the storage migration, cleanup, update policies and security maintenance work from previous releases.

Testing release: automated tests and package checks are complete when this release is published. Hands-on sessions, upgrades and migration testing remain for the 1.0 validation pass. Repository security settings remain unverified through the available connector.

Select Settings → Updates → Testing for development builds. Requires Windows x64, Linux glibc 2.39+, or macOS 15+. Windows binaries are unsigned; Mac bundles are not notarized. DEB installation uses the system package installer.
