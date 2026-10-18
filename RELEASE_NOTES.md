- Fixed disabled update checks on DEB installations. The app now announces newer releases and provides a download link; install the DEB through your system package installer.
- Existing DEB users must install this version manually once to receive future update notices. No APT update repository is configured.
- Successful builds now publish testing releases automatically, with SHA256SUMS.txt. Existing published binaries are never replaced.

Testing build: automated tests and packaging checks run on Windows, Linux and both Mac architectures. Hands-on desktop validation remains outstanding; this is not the final 1.0 release.

Requires Windows x64, Linux glibc 2.39+, or macOS 15+. Windows builds are unsigned; Mac builds are not notarized.

Includes the 0.8.0 revision metrics and 0.7.0 session improvements. History migrations retain backups; downgrading requires restoring the pre-upgrade database backup. The unfinished data export/import controls are not included.
