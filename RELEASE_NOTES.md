- Added Stable and Testing update channels. Stable is the default: select Settings → Updates → Testing to keep receiving development releases.
- Automatic update checks now run at most once per 24 hours, including across restarts. Manual checks remain available.
- Windows installers and AppImages retain restart-to-update. Portable Windows, Linux DEB/tar and current unsigned/not-notarized Mac builds check and notify, with manual installation.
- Switching channels clears a pending update from the previous channel. Neither channel downgrades the installed version.
- Added Windows policy support to disable the updater, alongside WRITEWATCH_DISABLE_UPDATES=1.
- Backups now include the update channel (format 2). Old format 1 backups still import and default to Stable; 0.9.0 cannot import new exports. The history database format is unchanged.

Testing release with automated tests and package/startup checks on Windows, Linux and both Mac architectures. Hands-on update validation remains outstanding.

Requires Windows x64, Linux glibc 2.39+, or macOS 15+. Windows builds are unsigned; Mac builds are not notarized. SHA256SUMS.txt is included. Existing DEB users install this DEB through the system package installer; no APT repository is configured.
