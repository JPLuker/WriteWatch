- Added a release gate that requires all nine expected packages, rejects empty or unexpected files, checks tag/version consistency for tag builds, and generates a complete checksum manifest.
- Added grouped weekly dependency update checks for Python packages and GitHub Actions, plus private vulnerability-reporting guidance.
- Includes 0.11.0 storage migration and updater retention. Existing default-location history/settings are copied automatically, preserving original files for recovery. Custom profiles stay in place.

No changes to session tracking, history schema or backup format in this maintenance patch. Repository-level security settings still need administrator verification; the new configuration does not establish that they are enabled.

Testing release. Automated tests and packaging checks do not replace hands-on upgrade/migration validation before 1.0. Choose Settings → Updates → Testing to receive development builds.

Requires Windows x64, Linux glibc 2.39+, or macOS 15+. Windows builds are unsigned; Mac builds are not notarized. DEB installation remains managed by the system package installer. SHA256SUMS.txt is included.
