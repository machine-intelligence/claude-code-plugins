---
name: YouTube Live Segment Downloader
description: >-
  This skill should be used when the user asks to "download a clip from a live stream",
  "extract a segment from a YouTube live video", "download part of a live stream",
  "grab a clip from YouTube live", "save a segment from a streaming video", or needs
  to download a specific time range from a YouTube live stream (including 24/7 news
  streams like CBS News, ABC News, CNN). Also applies when yt-dlp's --download-sections
  fails with "This format cannot be partially downloaded" on a live stream.
version: 0.1.0
allowed-tools:
  - Bash(yt-dlp *)
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/skills/youtube-live-segment/scripts/extract_live_segment.py" *)
  - Bash(ffmpeg *)
  - Bash(open *)
  - Bash(start *)
---

# YouTube Live Segment Downloader

Extract specific time segments from YouTube live streams at 20-30x real-time speed using
custom HLS playlist construction. This technique bypasses yt-dlp's limitation where DASH
formats on live streams cannot be partially downloaded.

Do not attempt `yt-dlp --download-sections` on live streams — DASH formats do not support
partial downloads and it will fail.

## Core Technique

The approach has two steps:

1. **Identify the best HLS format** — Claude picks the highest quality HLS format from `yt-dlp -F`
2. **Run the bundled script** — it handles everything else: gets the manifest URL, calculates
   segments from UTC times, builds a playlist, and downloads with ffmpeg

This achieves 20-30x real-time speed (a 20-minute segment downloads in under a minute).

## Step-by-Step Workflow

The user should give you the YouTube live stream URL directly, not just tell you which stream they want. If they haven't provided a URL, ask for it before proceeding.

### Step 1: Identify Available HLS Formats

List all formats and find HLS (m3u8) ones. HLS formats have protocol `m3u8_native` or
contain `m3u8` in the format note.

```bash
yt-dlp -F <youtube_url>
```

Look for formats numbered in the 90s or 300 range (e.g., 91, 92, 93, 94, 95, 96, 300, 301).
Format 300 is typically 720p60. Choose the highest quality HLS format available.

If no HLS formats appear, the stream may not have DVR enabled (required for this technique).
Try adding `--live-from-start` to the command. If there are still no HLS formats, let the
user know this stream doesn't support segment extraction.

### Step 2: Download the Segment

Convert the user's target time to UTC, then run the bundled script with the YouTube URL,
chosen format ID, and UTC start/end times. The script gets the manifest URL from yt-dlp,
finds a reference point, calculates segment numbers, builds a playlist, and downloads with
ffmpeg. A 60-second buffer is added on each side by default.

Name the rough cut `[Channel/Show] - rough cut - YYYY-MM-DD.mp4`
(e.g., `ABC News Live - rough cut - 2026-02-12.mp4`). Save it in the current working
directory.

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/youtube-live-segment/scripts/extract_live_segment.py" "<youtube_url>" <format_id> "<start_utc>" "<end_utc>" "<descriptive name>.mp4"
```

The script also accepts raw segment numbers instead of timestamps (e.g. `7500 7740`).

Let the user know the download is running and roughly how long to expect (a 20-minute
segment typically takes under a minute).

### Step 3: Review and Precise Trim

Users typically give an approximate time window ("it happened around 5:30 PM, grab half an
hour around that") because pinpointing an exact moment in a 10+ hour live stream is hard.
The initial download is intentionally a rough cut — a wider net around the target. After
downloading, **always** prompt the user to review the video and identify the exact portion
they want to keep.

**Workflow:**
1. Tell the user the rough cut is ready and offer to open it for review
   (use `open "output.mp4"` on macOS or `start output.mp4` on Windows).
2. Use AskUserQuestion to ask the user for the exact start and end timestamps for the
   final clip (e.g., "start at 2:15, end at 18:30"). If you don't already know from the
   conversation what the clip is of, also ask what to name it. Name the final clip
   `[Channel/Show] - [Description] - YYYY-MM-DD.mp4`
   (e.g., `ABC News Live - Malo segment - 2026-02-12.mp4`).
3. Once the user provides timestamps, trim with ffmpeg:
   ```bash
   ffmpeg -i output.mp4 -ss HH:MM:SS -to HH:MM:SS -c copy "final clip.mp4"
   ```
4. Clean up the rough cut if the user doesn't need it.

**If the user already knows exact trim points** or says the rough cut is fine, skip the review.

### Step 4: Clean Up

After the final clip is ready, use AskUserQuestion to ask if the user wants to keep or
delete the rough cut. Tell the user the full path to the final clip so they can find it
easily.

## Bundled Script

**`${CLAUDE_PLUGIN_ROOT}/skills/youtube-live-segment/scripts/extract_live_segment.py`** handles
the full download pipeline:

1. Gets the m3u8 manifest URL from yt-dlp
2. Fetches the manifest and finds a reference point (segment number to UTC timestamp)
3. Calculates the target segment range from UTC times (with configurable buffer)
4. Builds a custom m3u8 playlist with only the requested segments
5. Downloads with ffmpeg (`-c copy`, no re-encoding)

**Time mode** (preferred):
```
python <script> <youtube_url> <format_id> <start_utc> <end_utc> <output.mp4> [--buffer SECONDS]
```

**Segment mode** (fallback — if the third and fourth args are plain integers):
```
python <script> <youtube_url> <format_id> <start_sq> <end_sq> <output.mp4>
```

Requires yt-dlp and ffmpeg. No Python dependencies beyond standard library.

## Time Zone Offsets

Always convert the user's local time to UTC before passing it to the script.

| Time zone | UTC offset |
| --------- | ---------- |
| EST       | +5 hours   |
| EDT       | +4 hours   |
| PST       | +8 hours   |
| PDT       | +7 hours   |

For other time zones, ask the user or look up the offset.

## Common Pitfalls

- **DASH formats cannot be partially downloaded.** Always use HLS (m3u8) formats for this technique.
- **yt-dlp `--download-sections` does not work** on live streams with DASH formats. Do not retry it.
- **Segment numbers shift** as the DVR buffer rolls forward on 24/7 streams. Run the script close to when the user requests the clip, not hours later.
- **Buffer generously.** The script adds 60 seconds of padding by default. Use `--buffer` to increase if needed. Trimming after download is cheap.

## If Something Goes Wrong

If the standard workflow fails for a reason you don't understand, don't just give up — offer
to get creative and try to figure out an alternative approach. yt-dlp and ffmpeg are powerful
tools with many options, and there may be a workaround.

When troubleshooting, explain what you're trying and why at each step. Users who aren't
familiar with these tools will be more comfortable letting you experiment if they understand
what's happening.

If you do find a workaround, offer to write up what went wrong and how you solved it so the
skill can be updated to handle that case in the future.

## Tool Requirements

- `yt-dlp`
- `ffmpeg`
- Python 3 (for the bundled script, no external dependencies)

If any of these are missing, use AskUserQuestion to offer to install them. On macOS, check
if `brew` is available first — if not, direct the user to https://brew.sh/ to install
Homebrew (it requires interactive setup). Once Homebrew is available:
`brew install yt-dlp ffmpeg`. On Windows: `winget install yt-dlp.yt-dlp` (this automatically
installs ffmpeg as a dependency). Verify Python 3 is available separately — it is often
already installed.
