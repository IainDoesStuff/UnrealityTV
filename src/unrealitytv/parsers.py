"""Filename parsing for episodes."""

import re
from pathlib import Path

from unrealitytv.models import Episode


def parse_episode(file_path: Path) -> Episode:
    """Parse episode information from a filename.

    Supports these naming formats:
    - Show.Name.S01E05.720p.mkv → show="Show Name", season=1, episode=5
    - Show Name - S01E05 - Episode Title.mp4 → show="Show Name", season=1, episode=5
    - Show Name - 1x05 - Title.mkv → show="Show Name", season=1, episode=5
    - Show.Name.2024.S01E05.mkv → show="Show Name", season=1, episode=5

    Args:
        file_path: Path to the video file.

    Returns:
        Episode object with parsed information. Season and episode are None if pattern doesn't match.
    """
    filename = file_path.stem  # Get filename without extension

    # Pattern 1: Show.Name.2024.S01E05 (year included before season/episode)
    # Must try this FIRST to avoid matching the year as part of show name
    pattern_year = r"^(.+?)\.\d{4}\.S(\d{1,2})E(\d{1,2})"
    match = re.search(pattern_year, filename, re.IGNORECASE)
    if match:
        show = match.group(1).replace(".", " ").strip()
        season = int(match.group(2))
        episode = int(match.group(3))
        return Episode(
            file_path=file_path,
            show_name=show,
            season=season,
            episode=episode,
        )

    # Pattern 2: Show.Name.S01E05 or Show Name - S01E05 or Show Name S01E05
    pattern1 = r"^(.+?)(?:\s*-\s*)?S(\d{1,2})E(\d{1,2})"
    match = re.search(pattern1, filename, re.IGNORECASE)
    if match:
        show = match.group(1).replace(".", " ").strip()
        season = int(match.group(2))
        episode = int(match.group(3))
        return Episode(
            file_path=file_path,
            show_name=show,
            season=season,
            episode=episode,
        )

    # Pattern 3: Show Name - 1x05 (season x episode format)
    pattern2 = r"^(.+?)(?:\s*-\s*)(\d{1,2})x(\d{1,2})"
    match = re.search(pattern2, filename, re.IGNORECASE)
    if match:
        show = match.group(1).replace(".", " ").strip()
        season = int(match.group(2))
        episode = int(match.group(3))
        return Episode(
            file_path=file_path,
            show_name=show,
            season=season,
            episode=episode,
        )

    # No pattern matched - extract show name but return None for season/episode
    # Try to get a reasonable show name
    show_name = filename.replace(".", " ").split("-")[0].strip()
    return Episode(
        file_path=file_path,
        show_name=show_name,
        season=None,
        episode=None,
    )
