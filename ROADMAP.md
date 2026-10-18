# Remaining work

Desktop priority: finish stabilization and standards work, then release 1.0. Browser/cloud work does not block desktop maintenance mode.

## Implemented for 0.7.0 validation
- #2: Page goals, manually entered or explicitly estimated using configurable words per page. Native editor pagination is not inferred.
- #3: Start on successful file selection; editable goals and mode without resetting progress.
- #4: Ten local recent file paths, Browse, disable and clear controls; never shared.
- #5: Negative-count completion covered in UI tests. Original report not reproduced from negativity alone; final-read failures now offer explicit last-count completion. Keep issue open until the reporter verifies.
- #6: Copy button wording.
- #7: Default Writing label omitted from text summaries; Revision retained.

## Next
- Validate the new flow on a real writing session, including negative-count completion.
- Validate 0.8.0 revision metrics: cumulative word additions/removals between observed saves; no stored content. Movement and punctuation-only changes are intentionally not counted.

## First priority after desktop 1.0
- Build a separate WriteWatch Chrome extension for #1. First prototype: Google Docs stays open with its word counter visible; observe that counter for sessions, goals, history and copied summaries.
- Verify that whole-document counts can be distinguished from selected-text counts, and handle hidden counters, navigation, reloads and multiple tabs without false deltas.
- No Drive API or Google Cloud setup planned for the counter prototype. Do not promise reliable support until tested against the live editor.
- Desktop maintenance and browser development remain separate. Tablet support is not implied by a desktop Chrome extension.


## Before a public release
- Publish only from tagged CI builds; separate untested OS/formats and label them according to release standards.
- Standardize asset names, grouped downloads and SHA256SUMS.txt.
- Align update channels, cadence and installation-type policies with the new standards.
- Finish storage-location migration and automatic cache/log retention. Export/import/deletion, data-folder access, diagnostics and manual cache/log clearing are implemented in 0.9.0.
- Finish dependency/security baseline configuration and documentation.
- Confirm each main-release format and its upgrade path on actual hardware or a real VM.

At Joseph’s request, successful versioned main pushes now publish testing prereleases so testing can continue between development sessions. These are not claims of hands-on platform validation. Stable 1.0 publication still requires the checks above.
