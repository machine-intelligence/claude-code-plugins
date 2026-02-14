#!/usr/bin/env python3
"""
Download a segment from a YouTube live stream.

Given a YouTube URL, HLS format ID, time range, and output path, this script:
1. Gets the m3u8 manifest URL from yt-dlp
2. Fetches the manifest and finds a reference point
3. Calculates the target segment range from UTC times
4. Builds a custom m3u8 playlist with only those segments
5. Runs ffmpeg to download and mux them into an MP4

Usage (time mode):
    python extract_live_segment.py <youtube_url> <format_id> <start_utc> <end_utc> <output.mp4> [--buffer SECONDS]

    Times are ISO 8601 UTC (e.g. "2025-02-13T21:00:00Z"). A buffer (default 60s)
    is added on each side.

Usage (segment mode):
    python extract_live_segment.py <youtube_url> <format_id> <start_segment> <end_segment> <output.mp4>

    If the third and fourth arguments are plain integers, they are treated as raw
    segment numbers (no buffer is added).

Examples:
    python extract_live_segment.py "https://youtube.com/watch?v=..." 301 "2025-02-13T21:00:00Z" "2025-02-13T21:20:00Z" output.mp4
    python extract_live_segment.py "https://youtube.com/watch?v=..." 301 7500 7740 output.mp4

Requires: yt-dlp, ffmpeg, Python 3
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone


def run_cmd(args: list[str], description: str) -> str:
    """Run a command and return its stdout. Exits on failure."""
    print(f"{description}...")
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {description} failed", file=sys.stderr)
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def fetch_manifest(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8")


def extract_template_url(manifest: str) -> str:
    """Find a segment URL in the manifest and convert it to a template with {sq} placeholder."""
    for line in manifest.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            template = re.sub(r"/sq/\d+/", "/sq/{sq}/", line)
            return template
    raise ValueError("No segment URLs found in manifest")


def find_manifest_reference_point(manifest: str) -> tuple[int, str] | None:
    """Extract a segment number and its date/time from #EXT-X-PROGRAM-DATE-TIME tags.

    Returns (segment_number, iso_datetime) for the last reference point found,
    or None if no date-time tags exist.
    """
    lines = manifest.splitlines()
    last_datetime = None
    last_segment_num = None

    for i, line in enumerate(lines):
        if line.startswith("#EXT-X-PROGRAM-DATE-TIME:"):
            last_datetime = line.split(":", 1)[1].strip()
            for j in range(i + 1, len(lines)):
                seg_line = lines[j].strip()
                if seg_line and not seg_line.startswith("#"):
                    match = re.search(r"/sq/(\d+)/", seg_line)
                    if match:
                        last_segment_num = int(match.group(1))
                    break

    if last_datetime and last_segment_num is not None:
        return (last_segment_num, last_datetime)
    return None


def parse_utc(s: str) -> datetime:
    """Parse an ISO 8601 UTC timestamp. Handles trailing Z."""
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def segments_from_times(
    ref_segment: int,
    ref_time: str,
    start_utc: datetime,
    end_utc: datetime,
    buffer_seconds: float = 60.0,
    segment_duration: float = 5.0,
) -> tuple[int, int]:
    """Calculate segment numbers from UTC times using a manifest reference point."""
    ref_dt = parse_utc(ref_time)
    start_offset = (start_utc - ref_dt).total_seconds() - buffer_seconds
    end_offset = (end_utc - ref_dt).total_seconds() + buffer_seconds
    start_sq = ref_segment + int(start_offset / segment_duration)
    end_sq = ref_segment + int(end_offset / segment_duration)
    return (start_sq, end_sq)


def build_playlist(template_url: str, start_sq: int, end_sq: int, segment_duration: float = 5.0) -> str:
    """Build a minimal m3u8 playlist for the given segment range."""
    lines = [
        "#EXTM3U",
        "#EXT-X-VERSION:3",
        f"#EXT-X-TARGETDURATION:{int(segment_duration)}",
        f"#EXT-X-MEDIA-SEQUENCE:{start_sq}",
    ]
    for sq in range(start_sq, end_sq + 1):
        lines.append(f"#EXTINF:{segment_duration},")
        lines.append(template_url.format(sq=sq))
    lines.append("#EXT-X-ENDLIST")
    return "\n".join(lines) + "\n"


def is_integer(s: str) -> bool:
    try:
        int(s)
        return True
    except ValueError:
        return False


def main():
    if len(sys.argv) < 6:
        print(__doc__)
        sys.exit(1)

    youtube_url = sys.argv[1]
    format_id = sys.argv[2]
    arg3 = sys.argv[3]
    arg4 = sys.argv[4]
    output_path = sys.argv[5]

    # Parse optional --buffer flag
    buffer_seconds = 60.0
    for i, arg in enumerate(sys.argv[6:], start=6):
        if arg == "--buffer" and i + 1 < len(sys.argv):
            buffer_seconds = float(sys.argv[i + 1])
            break

    segment_mode = is_integer(arg3) and is_integer(arg4)

    # Step 1: Get the m3u8 manifest URL from yt-dlp
    manifest_url = run_cmd(
        ["yt-dlp", "-f", format_id, "--print", "urls", youtube_url],
        "Getting manifest URL from yt-dlp",
    )
    print("Manifest URL obtained")

    # Step 2: Fetch and parse the manifest
    print("Fetching manifest...")
    manifest = fetch_manifest(manifest_url)
    print(f"Manifest: {len(manifest.splitlines())} lines")

    ref = find_manifest_reference_point(manifest)
    if ref:
        print(f"Reference point: segment {ref[0]} = {ref[1]}")

    # Step 3: Determine segment range
    if segment_mode:
        start_sq = int(arg3)
        end_sq = int(arg4)
    else:
        if not ref:
            print("Error: No reference point found in manifest. Cannot convert times to segments.", file=sys.stderr)
            print("Try using raw segment numbers instead.", file=sys.stderr)
            sys.exit(1)
        start_utc = parse_utc(arg3)
        end_utc = parse_utc(arg4)
        start_sq, end_sq = segments_from_times(ref[0], ref[1], start_utc, end_utc, buffer_seconds)
        print(f"Time range: {arg3} to {arg4} (buffer: {buffer_seconds:.0f}s)")
        print(f"Calculated segments: {start_sq}-{end_sq}")

    # Step 4: Build playlist
    template = extract_template_url(manifest)
    print("Template URL extracted")

    segment_count = end_sq - start_sq + 1
    duration_min = (segment_count * 5) / 60
    print(f"Building playlist: segments {start_sq}-{end_sq} ({segment_count} segments, ~{duration_min:.1f} min)")

    playlist = build_playlist(template, start_sq, end_sq)

    # Write playlist to a temp file, then run ffmpeg
    playlist_path = os.path.join(tempfile.gettempdir(), "live_segment.m3u8")
    with open(playlist_path, "w") as f:
        f.write(playlist)
    print(f"Playlist written to: {playlist_path}")

    # Step 5: Download with ffmpeg
    try:
        print("Downloading with ffmpeg...")
        ffmpeg_result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-protocol_whitelist", "file,http,https,tcp,tls",
                "-i", playlist_path,
                "-c", "copy",
                output_path,
            ],
            capture_output=True,
            text=True,
        )
        if ffmpeg_result.returncode != 0:
            print("Error: ffmpeg failed", file=sys.stderr)
            if ffmpeg_result.stderr:
                # ffmpeg writes progress to stderr; only show last few lines on error
                lines = ffmpeg_result.stderr.strip().splitlines()
                for line in lines[-10:]:
                    print(f"  {line}", file=sys.stderr)
            sys.exit(1)
    finally:
        try:
            os.remove(playlist_path)
        except OSError:
            pass

    print(f"Done: {output_path}")


if __name__ == "__main__":
    main()
