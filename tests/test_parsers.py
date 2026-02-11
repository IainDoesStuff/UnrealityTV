"""Tests for episode filename parser."""

from pathlib import Path

from unrealitytv.parsers import parse_episode


class TestParseEpisode:
    """Test episode filename parser."""

    def test_format_with_dots_and_season_episode(self):
        """Test Show.Name.S01E05.720p.mkv format."""
        path = Path("Show.Name.S01E05.720p.mkv")
        ep = parse_episode(path)
        assert ep.show_name == "Show Name"
        assert ep.season == 1
        assert ep.episode == 5

    def test_format_with_dashes_and_season_episode(self):
        """Test Show Name - S01E05 - Episode Title.mp4 format."""
        path = Path("Show Name - S01E05 - Episode Title.mp4")
        ep = parse_episode(path)
        assert ep.show_name == "Show Name"
        assert ep.season == 1
        assert ep.episode == 5

    def test_format_with_season_x_episode(self):
        """Test Show Name - 1x05 - Title.mkv format."""
        path = Path("Show Name - 1x05 - Title.mkv")
        ep = parse_episode(path)
        assert ep.show_name == "Show Name"
        assert ep.season == 1
        assert ep.episode == 5

    def test_format_with_year_and_season_episode(self):
        """Test Show.Name.2024.S01E05.mkv format."""
        path = Path("Show.Name.2024.S01E05.mkv")
        ep = parse_episode(path)
        assert ep.show_name == "Show Name"
        assert ep.season == 1
        assert ep.episode == 5

    def test_two_digit_season_and_episode(self):
        """Test parsing two-digit season and episode numbers."""
        path = Path("My.Show.S12E42.720p.mkv")
        ep = parse_episode(path)
        assert ep.show_name == "My Show"
        assert ep.season == 12
        assert ep.episode == 42

    def test_unknown_format_returns_none_season_episode(self):
        """Test that unknown format returns None for season/episode."""
        path = Path("Some.Random.Movie.Name.mkv")
        ep = parse_episode(path)
        assert ep.season is None
        assert ep.episode is None
        # Should still extract something as show_name
        assert ep.show_name is not None

    def test_lowercase_season_episode_indicator(self):
        """Test lowercase s and e indicators."""
        path = Path("Show.Name.s01e05.720p.mkv")
        ep = parse_episode(path)
        assert ep.show_name == "Show Name"
        assert ep.season == 1
        assert ep.episode == 5

    def test_single_digit_season_and_episode(self):
        """Test single digit season and episode."""
        path = Path("Show Name S5E3 Title.mp4")
        ep = parse_episode(path)
        assert ep.show_name == "Show Name"
        assert ep.season == 5
        assert ep.episode == 3

    def test_file_path_preserved(self):
        """Test that file_path is preserved in result."""
        full_path = Path("/media/shows/Show.Name.S01E05.mkv")
        ep = parse_episode(full_path)
        assert ep.file_path == full_path
