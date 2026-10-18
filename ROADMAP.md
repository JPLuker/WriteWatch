# Remaining work

User priority: #2 → #3 → #4 → #5 → #6 → #7 → #1.

## Implemented for 0.7.0 validation
- #2: Page goals, manually entered or explicitly estimated using configurable words per page. Native editor pagination is not inferred.
- #3: Start on successful file selection; editable goals and mode without resetting progress.
- #4: Ten local recent file paths, Browse, disable and clear controls; never shared.
- #5: Negative-count completion covered in UI tests. Original report not reproduced from negativity alone; final-read failures now offer explicit last-count completion. Keep issue open until the reporter verifies.
- #6: Copy button wording.
- #7: Default Writing label omitted from text summaries; Revision retained.

## Next
- Validate the new flow on a real writing session, including negative-count completion.
- Revision metrics: compare saved text in memory for additions/removals and changed paragraphs; persist only aggregates. Account for moved text, repeated edits and save intervals before claiming reliable totals.
- #1: Google Drive / OneDrive access needs separate provider integrations and OAuth app registrations. Tablet use additionally needs a supported mobile/web client; adding desktop cloud access alone does not solve it. Existing locally synced supported files already work. No cloud-only access is implemented yet.

## Before a public release
- Publish only from tagged CI builds; separate untested OS/formats and label them according to release standards.
- Standardize asset names, grouped downloads and SHA256SUMS.txt.
- Align update channels, cadence and installation-type policies with the new standards.
- Add full export/import/deletion and storage-location migration, plus diagnostics and cache/log management.
- Finish dependency/security baseline configuration and documentation.
- Confirm each main-release format and its upgrade path on actual hardware or a real VM.

Main pushes produce development artifacts; tags prepare drafts. Do not promote an unverified artifact to a tested public release.
