"""Tests for Plex API client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from unrealitytv.plex.client import PlexAPIError, PlexClient
from unrealitytv.plex.markers import MarkerType


class TestPlexClientInit:
    """Tests for PlexClient initialization."""

    def test_client_initialization(self) -> None:
        """Test initializing PlexClient."""
        client = PlexClient(
            base_url="http://localhost:32400", token="test_token_123"
        )

        assert client.base_url == "http://localhost:32400"
        assert client.token == "test_token_123"

    def test_client_strips_trailing_slash(self) -> None:
        """Test that trailing slash is removed from base URL."""
        client = PlexClient(
            base_url="http://localhost:32400/", token="test_token_123"
        )

        assert client.base_url == "http://localhost:32400"

    def test_client_initialization_without_requests(self) -> None:
        """Test error when requests library is not installed."""
        with patch("unrealitytv.plex.client.requests", None):
            with pytest.raises(PlexAPIError, match="requests library is not installed"):
                PlexClient(
                    base_url="http://localhost:32400", token="test_token_123"
                )


class TestPlexClientHeaders:
    """Tests for header management."""

    def test_get_headers_includes_token(self) -> None:
        """Test that headers include authentication token."""
        client = PlexClient(
            base_url="http://localhost:32400", token="test_token_123"
        )

        headers = client._get_headers()

        assert headers["X-Plex-Token"] == "test_token_123"
        assert headers["Accept"] == "application/json"

    def test_get_headers_returns_copy(self) -> None:
        """Test that get_headers returns a copy."""
        client = PlexClient(
            base_url="http://localhost:32400", token="test_token_123"
        )

        headers1 = client._get_headers()
        headers1["Custom"] = "value"
        headers2 = client._get_headers()

        assert "Custom" not in headers2


class TestPlexClientLibraries:
    """Tests for library retrieval."""

    def test_get_libraries_success(self) -> None:
        """Test successfully retrieving libraries."""
        client = PlexClient(
            base_url="http://localhost:32400", token="test_token"
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "MediaContainer": {
                "Directory": [
                    {
                        "key": "1",
                        "title": "Movies",
                        "type": "movie",
                    },
                    {
                        "key": "2",
                        "title": "Shows",
                        "type": "show",
                    },
                ]
            }
        }

        with patch.object(client.session, "get", return_value=mock_response):
            libraries = client.get_libraries()

            assert len(libraries) == 2
            assert libraries[0]["key"] == "1"
            assert libraries[0]["title"] == "Movies"
            assert libraries[1]["key"] == "2"
            assert libraries[1]["title"] == "Shows"

    def test_get_libraries_empty(self) -> None:
        """Test retrieving when no libraries exist."""
        client = PlexClient(
            base_url="http://localhost:32400", token="test_token"
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {"MediaContainer": {}}

        with patch.object(client.session, "get", return_value=mock_response):
            libraries = client.get_libraries()

            assert len(libraries) == 0

    def test_get_libraries_api_error(self) -> None:
        """Test handling of API errors when getting libraries."""
        client = PlexClient(
            base_url="http://localhost:32400", token="test_token"
        )

        with patch.object(
            client.session, "get", side_effect=Exception("Connection error")
        ):
            with pytest.raises(PlexAPIError, match="Failed to get Plex libraries"):
                client.get_libraries()


class TestPlexClientSections:
    """Tests for section retrieval."""

    def test_get_sections_success(self) -> None:
        """Test successfully retrieving sections."""
        client = PlexClient(
            base_url="http://localhost:32400", token="test_token"
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "MediaContainer": {
                "Metadata": [
                    {
                        "key": "/library/metadata/1",
                        "title": "Show 1",
                        "type": "show",
                        "ratingKey": "1",
                    },
                    {
                        "key": "/library/metadata/2",
                        "title": "Show 2",
                        "type": "show",
                        "ratingKey": "2",
                    },
                ]
            }
        }

        with patch.object(client.session, "get", return_value=mock_response):
            items = client.get_sections("1")

            assert len(items) == 2
            assert items[0]["title"] == "Show 1"
            assert items[1]["title"] == "Show 2"

    def test_get_sections_empty(self) -> None:
        """Test retrieving empty sections."""
        client = PlexClient(
            base_url="http://localhost:32400", token="test_token"
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {"MediaContainer": {}}

        with patch.object(client.session, "get", return_value=mock_response):
            items = client.get_sections("1")

            assert len(items) == 0

    def test_get_sections_api_error(self) -> None:
        """Test handling of API errors when getting sections."""
        client = PlexClient(
            base_url="http://localhost:32400", token="test_token"
        )

        with patch.object(
            client.session, "get", side_effect=Exception("Connection error")
        ):
            with pytest.raises(PlexAPIError, match="Failed to get Plex sections"):
                client.get_sections("1")


class TestPlexClientFindEpisode:
    """Tests for episode finding."""

    def test_find_episode_with_season_episode(self) -> None:
        """Test finding specific episode with season and episode number."""
        client = PlexClient(
            base_url="http://localhost:32400", token="test_token"
        )

        mock_response_search = MagicMock()
        mock_response_search.json.return_value = {
            "MediaContainer": {
                "Metadata": [
                    {
                        "key": "/library/metadata/10",
                        "title": "Breaking Bad",
                        "ratingKey": "10",
                    }
                ]
            }
        }

        mock_response_episodes = MagicMock()
        mock_response_episodes.json.return_value = {
            "MediaContainer": {
                "Metadata": [
                    {
                        "key": "/library/metadata/100",
                        "title": "Pilot",
                        "ratingKey": "100",
                        "parentIndex": 1,
                        "index": 1,
                    }
                ]
            }
        }

        with patch.object(
            client.session, "get", side_effect=[mock_response_search, mock_response_episodes]
        ):
            episode = client.find_episode("Breaking Bad", 1, 1)

            assert episode is not None
            assert episode["title"] == "Pilot"
            assert episode["seasonNumber"] == 1
            assert episode["episodeNumber"] == 1

    def test_find_episode_show_not_found(self) -> None:
        """Test handling when show is not found."""
        client = PlexClient(
            base_url="http://localhost:32400", token="test_token"
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {"MediaContainer": {}}

        with patch.object(client.session, "get", return_value=mock_response):
            episode = client.find_episode("Nonexistent Show", 1, 1)

            assert episode is None

    def test_find_episode_episode_not_found(self) -> None:
        """Test handling when episode is not found."""
        client = PlexClient(
            base_url="http://localhost:32400", token="test_token"
        )

        mock_response_search = MagicMock()
        mock_response_search.json.return_value = {
            "MediaContainer": {
                "Metadata": [
                    {
                        "key": "/library/metadata/10",
                        "title": "Breaking Bad",
                        "ratingKey": "10",
                    }
                ]
            }
        }

        mock_response_episodes = MagicMock()
        mock_response_episodes.json.return_value = {
            "MediaContainer": {
                "Metadata": [
                    {
                        "key": "/library/metadata/100",
                        "title": "Pilot",
                        "ratingKey": "100",
                        "parentIndex": 1,
                        "index": 1,
                    }
                ]
            }
        }

        with patch.object(
            client.session, "get", side_effect=[mock_response_search, mock_response_episodes]
        ):
            episode = client.find_episode("Breaking Bad", 1, 5)

            assert episode is None

    def test_find_episode_api_error(self) -> None:
        """Test handling of API errors during episode search."""
        client = PlexClient(
            base_url="http://localhost:32400", token="test_token"
        )

        with patch.object(
            client.session, "get", side_effect=Exception("Connection error")
        ):
            with pytest.raises(PlexAPIError, match="Failed to find episode"):
                client.find_episode("Breaking Bad", 1, 1)


class TestPlexClientApplyMarker:
    """Tests for marker application."""

    def test_apply_marker_success(self) -> None:
        """Test successfully applying a marker."""
        client = PlexClient(
            base_url="http://localhost:32400", token="test_token"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client.session, "post", return_value=mock_response):
            result = client.apply_marker(
                item_id="123", start_ms=1000, end_ms=5000, marker_type=MarkerType.INTRO
            )

            assert result is True

    def test_apply_marker_converts_ms_to_seconds(self) -> None:
        """Test that milliseconds are converted to seconds."""
        client = PlexClient(
            base_url="http://localhost:32400", token="test_token"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client.session, "post", return_value=mock_response) as mock_post:
            client.apply_marker(
                item_id="123", start_ms=1000, end_ms=5000, marker_type=MarkerType.INTRO
            )

            call_args = mock_post.call_args
            assert "startOffset=1" in call_args[0][0]
            assert "endOffset=5" in call_args[0][0]

    def test_apply_marker_api_error(self) -> None:
        """Test handling of API errors during marker application."""
        client = PlexClient(
            base_url="http://localhost:32400", token="test_token"
        )

        with patch.object(
            client.session, "post", side_effect=Exception("Connection error")
        ):
            with pytest.raises(PlexAPIError, match="Failed to apply marker"):
                client.apply_marker(
                    item_id="123",
                    start_ms=1000,
                    end_ms=5000,
                    marker_type=MarkerType.INTRO,
                )

    def test_apply_marker_different_types(self) -> None:
        """Test applying different marker types."""
        client = PlexClient(
            base_url="http://localhost:32400", token="test_token"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200

        for marker_type in MarkerType:
            with patch.object(client.session, "post", return_value=mock_response):
                result = client.apply_marker(
                    item_id="123",
                    start_ms=1000,
                    end_ms=5000,
                    marker_type=marker_type,
                )

                assert result is True
