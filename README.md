# WriteWatch

A local Windows/Linux companion for Fade In. Start a writing session, finish it, and copy your progress into your writers group. Your script stays on your computer.

## Download

Download the latest **prerelease** from [Releases](https://github.com/JPLuker/WriteWatch/releases).

- **Windows x64:** run `WriteWatch-…-Windows-Setup.exe` (per-user installer), or extract the portable ZIP and run `WriteWatch.exe` inside its folder. Keep `_internal` alongside the executable. The initial builds are unsigned; Windows may show its unknown-publisher prompt.
- **Linux x86_64:** make the AppImage executable in its Properties → Permissions and run it. If FUSE is unavailable, launch with `--appimage-extract-and-run`. Alternatively, extract the `.tar.gz` and run `WriteWatch/WriteWatch`. Targets Ubuntu 24.04 and similarly recent distributions (glibc 2.39+); Wayland and X11 use Qt. No keyboard hooks or compositor extensions.
- Each main-branch build also provides downloads under [Actions](https://github.com/JPLuker/WriteWatch/actions). A successful main-branch build publishes a versioned prerelease automatically; bump the app version for each release.

## Your first session

1. Save your screenplay in Fade In.
2. Open WriteWatch and **Choose Fade In script** (`.fadein` or `.osf`). Selection stays in memory and is not saved to history.
3. Pick **Writing** with a net-word goal, or **Revision** with a minute goal.
4. Click **Start session**, then write normally. WriteWatch checks your saved file every two seconds.
5. Save before **Pause** or **Done**. Resume excludes changes saved during the pause.
6. Click **Done — share progress**, then **Copy for writers group**. Paste it wherever you want. No automatic posting.

Example copied summary (no squares, script title or text):

```text
WriteWatch · Oct 15, 2026
Writing · Session complete
Goal progress: 100%
Time: 58m 00s · +624 net words
Goal: 500 net words
#WriteWatch
```

History lets you copy older sessions again and shows weekly totals and a writing streak. A PNG share card is optional. **Delete history** removes local completed/interrupted statistics; it never touches your script.

## What the numbers mean

- **Time** is the manual session timer minus pauses, not measured keyboard activity. It keeps running if you switch apps. A long suspension/event-loop stall pauses it.
- **Net words** compares saved screenplay-body word counts. It includes character cues and scene headings, but excludes title pages, notes and synopses. Counts may differ from Fade In's report. Equal-length rewrites yield zero; deleted words can make the total negative.
- **Revision** goals use elapsed session minutes so editing needn't increase the word count.
- Unsaved changes cannot be measured. Save before finishing. Changes made and undone between checks cannot be reconstructed.
- Interrupted sessions keep their most recent numeric checkpoint (normally within two seconds), appear as interrupted in history, and do not extend the completed-session streak. They are not automatically resumed.
- Week totals group sessions by their local start date; a session spanning midnight remains on its start day.

## Privacy

No network requests, accounts, telemetry, global typing hooks, script snapshots or script uploads. Only aggregate session statistics are persisted. See [PRIVACY.md](PRIVACY.md).

## Development

Requires Python 3.12+.

```sh
python -m venv .venv
# Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m writewatch
python -m unittest discover -v
```

Build **on each target OS**:

```sh
python -m pip install -r requirements-build.txt
python packaging/build.py
# Linux AppImage: bash packaging/appimage.sh
# Windows installer: ISCC packaging/windows.iss (Inno Setup 6)
```

CI runs parser, session, privacy, clipboard and UI tests on Windows and Linux before packaging. Source verification does not replace testing with your actual Fade In files and desktop. The initial release needs that hands-on check.

## Project status

0.1.1 is an initial testing release. No official relationship with Fade In. This repository currently grants no license to WriteWatch source; Joseph retains rights. Dependency notices are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
