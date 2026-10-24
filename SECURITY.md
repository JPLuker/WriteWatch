# Security

WriteWatch is pre-1.0 software. Security fixes target the newest published version; older testing releases are not maintained separately.

## Report a vulnerability privately

If the repository's Security tab offers **Report a vulnerability**, use it. Otherwise email the package maintainer at **JPLuker@pm.me** with the subject **WriteWatch security report**. Do not open a public issue containing exploit details, credentials or private writing.

Include the affected version and operating system, expected versus observed behavior, and minimal reproduction steps. Use a synthetic document if a sample is needed. Never send a real screenplay or writing folder. There is no guaranteed response deadline; this is a small maintained project.

## Relevant boundaries

- Selected documents are parsed locally. History stores aggregate statistics; recent-file paths are stored separately. JSON backups can contain those paths.
- Document parsers must not follow external URLs, extract archive entries to arbitrary paths, or resolve external XML entities.
- Updates contact GitHub and verify asset sizes and SHA-256 digests. Checksums are integrity checks against GitHub metadata, not an independent publisher signature. Current Windows binaries are unsigned and Mac bundles are not notarized.
- Imported backups must be validated before database writes. Migration must preserve source data; deletion and retention must remain limited to app-owned files.

See PRIVACY.md for data handling and README.md for storage locations and update policies.

## Maintenance and release checks

Dependabot checks Python requirements and GitHub Actions weekly, grouping routine updates for review. Updates are not automatically merged. Actions are pinned by commit SHA. Tests and package startup checks run on Windows, Linux and both Mac architectures before publishing testing releases. The release gate requires every expected package, rejects unexpected/empty packages, verifies tag/version consistency for tag builds, and generates SHA256SUMS.txt from the validated files.

Repository-level private reporting, secret scanning, push protection and dependency alert settings must be checked separately by a repository administrator. Committing this document or Dependabot configuration does not prove those settings are enabled. Automated checks do not replace hands-on installer, update and migration testing before 1.0.
