# Video Tools

Tools for downloading and clipping videos from the internet.

## Prerequisites

If any dependencies are missing when you use the plugin, Claude will offer to install them
for you. You can also install them manually ahead of time:

### macOS

[Homebrew](https://brew.sh/) is the recommended way to install the dependencies. If you don't
have it on your machine, you can find the installation instructions [here](https://brew.sh/).

In Terminal (or any terminal app):

```bash
brew install yt-dlp ffmpeg
# Python 3 is also required (included with Xcode Command Line Tools, installed by Homebrew)
```

### Windows

In PowerShell or Command Prompt:

```powershell
winget install yt-dlp ffmpeg Python.Python.3
```

## Skills

### YouTube Live Segment Downloader

Download a clip from a YouTube live stream — just give Claude the stream URL and the approximate
time window you want. It downloads a rough cut, asks you to review it and pick exact trim
points, then produces the final clip. A 20-minute segment downloads in under a minute.

Works with any YouTube live stream that has DVR enabled (CBS News 24/7, ABC News Live, CNN, etc.).

**Examples:**

> "Download about 20 minutes from the CBS News 24/7 stream starting around 3:00 PM ET today: https://youtube.com/watch?v=..."

> "Grab the last 30 minutes from this live stream: https://youtube.com/watch?v=..."

Under the hood, this works by extracting individual segments from the stream's HLS manifest
and stitching them together with ffmpeg, bypassing the normal limitation where YouTube live
streams can't be partially downloaded.
