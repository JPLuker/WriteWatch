# WriteWatch v0.6.1 — session toggles and Linux installer

- Writing / Revision is now a two-option toggle.
- Goals default to No goal. Choose Set goal to enter a word or minute target.
- Added an amd64 `.deb` installer alongside the AppImage, with an application-menu launcher and package-manager uninstall.
- The Debian package is installed, launched and removed in Linux CI.

Linux packages require glibc 2.39+ (Ubuntu 24.04 baseline). Upgrade `.deb` installations by installing the newer package; in-app self-updates remain available for the AppImage. Windows and Mac downloads remain available. macOS requires 15+ and is ad-hoc signed, not notarized.
