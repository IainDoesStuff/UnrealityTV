"""Plex API client for segment management."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional
from urllib.parse import quote

try:
    import requests
except ImportError:
    requests = None

if TYPE_CHECKING:
    from unrealitytv.plex.markers import MarkerType

logger = logging.getLogger(__name__)


class PlexAPIError(Exception):
    """Exception for Plex API errors."""

    pass


class PlexClient:
    """Client for interacting with Plex API."""

    def __init__(self, base_url: str, token: str):
        """Initialize Plex client.

        Args:
            base_url: Base URL of Plex server (e.g., "http://localhost:32400")
            token: X-Plex-Token authentication token

        Raises:
            PlexAPIError: If requests library is not installed
        """
        if requests is None:
            msg = "requests library is not installed. Install with: pip install requests"
            logger.error(msg)
            raise PlexAPIError(msg)

        self.base_url = base_url.rstrip("/")
        self.token = token
        self.session = requests.Session()
        self._headers = {
            "X-Plex-Token": self.token,
            "Accept": "application/json",
        }

    def _get_headers(self) -> dict:
        """Get request headers with authentication."""
        return self._headers.copy()

    def get_libraries(self) -> list[dict]:
        """Get all libraries from Plex server.

        Returns:
            List of library dictionaries with 'key' and 'title' fields

        Raises:
            PlexAPIError: If API request fails
        """
        try:
            url = f"{self.base_url}/library/sections"
            response = self.session.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()

            data = response.json()
            libraries = []
            for lib in data.get("MediaContainer", {}).get("Directory", []):
                libraries.append(
                    {
                        "key": lib.get("key"),
                        "title": lib.get("title"),
                        "type": lib.get("type"),
                    }
                )

            logger.info(f"Retrieved {len(libraries)} libraries from Plex")
            return libraries
        except Exception as e:
            msg = f"Failed to get Plex libraries: {e}"
            logger.error(msg)
            raise PlexAPIError(msg) from e

    def get_sections(self, library_key: str) -> list[dict]:
        """Get items in a library section.

        Args:
            library_key: Key of the library section

        Returns:
            List of item dictionaries with metadata

        Raises:
            PlexAPIError: If API request fails
        """
        try:
            url = f"{self.base_url}/library/sections/{library_key}/all"
            response = self.session.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()

            data = response.json()
            items = []
            for item in data.get("MediaContainer", {}).get("Metadata", []):
                items.append(
                    {
                        "key": item.get("key"),
                        "title": item.get("title"),
                        "type": item.get("type"),
                        "ratingKey": item.get("ratingKey"),
                    }
                )

            logger.info(f"Retrieved {len(items)} items from library {library_key}")
            return items
        except Exception as e:
            msg = f"Failed to get Plex sections: {e}"
            logger.error(msg)
            raise PlexAPIError(msg) from e

    def find_episode(
        self, show_name: str, season: Optional[int], episode: Optional[int]
    ) -> Optional[dict]:
        """Find an episode by show name, season, and episode number.

        Args:
            show_name: Name of the show
            season: Season number (optional)
            episode: Episode number (optional)

        Returns:
            Dictionary with episode metadata or None if not found

        Raises:
            PlexAPIError: If API request fails
        """
        try:
            # First, search for the show
            search_url = (
                f"{self.base_url}/library/all"
                f"?title={quote(show_name)}&limit=1"
            )
            response = self.session.get(
                search_url, headers=self._get_headers(), timeout=10
            )
            response.raise_for_status()

            data = response.json()
            metadata = data.get("MediaContainer", {}).get("Metadata", [])

            if not metadata:
                logger.warning(f"Show not found: {show_name}")
                return None

            show = metadata[0]
            show_key = show.get("key")

            # If season and episode are provided, find the specific episode
            if season is not None and episode is not None:
                episodes_url = f"{self.base_url}{show_key}/children"
                response = self.session.get(
                    episodes_url, headers=self._get_headers(), timeout=10
                )
                response.raise_for_status()

                data = response.json()
                for ep in data.get("MediaContainer", {}).get("Metadata", []):
                    if (
                        ep.get("parentIndex") == season
                        and ep.get("index") == episode
                    ):
                        logger.info(f"Found episode {show_name} S{season}E{episode}")
                        return {
                            "key": ep.get("key"),
                            "ratingKey": ep.get("ratingKey"),
                            "title": ep.get("title"),
                            "seasonNumber": ep.get("parentIndex"),
                            "episodeNumber": ep.get("index"),
                        }

                logger.warning(
                    f"Episode not found: {show_name} S{season}E{episode}"
                )
                return None

            logger.info(f"Found show: {show_name}")
            return {
                "key": show_key,
                "ratingKey": show.get("ratingKey"),
                "title": show.get("title"),
            }
        except Exception as e:
            msg = f"Failed to find episode: {e}"
            logger.error(msg)
            raise PlexAPIError(msg) from e

    def apply_marker(
        self,
        item_id: str,
        start_ms: int,
        end_ms: int,
        marker_type: MarkerType,
    ) -> bool:
        """Apply a marker to a Plex item.

        Args:
            item_id: Plex item ID (ratingKey)
            start_ms: Start time in milliseconds
            end_ms: End time in milliseconds
            marker_type: Type of marker to apply

        Returns:
            True if marker was successfully applied

        Raises:
            PlexAPIError: If API request fails
        """
        try:
            # Convert milliseconds to seconds (Plex uses seconds)
            start_sec = start_ms // 1000
            end_sec = end_ms // 1000

            # Create marker via Plex API
            url = (
                f"{self.base_url}/library/metadata/{item_id}/markers"
                f"?type={marker_type.value}&startOffset={start_sec}"
                f"&endOffset={end_sec}"
            )

            response = self.session.post(
                url, headers=self._get_headers(), timeout=10
            )
            response.raise_for_status()

            logger.info(
                f"Applied {marker_type.value} marker to item {item_id} "
                f"({start_sec}s - {end_sec}s)"
            )
            return True
        except Exception as e:
            msg = f"Failed to apply marker: {e}"
            logger.error(msg)
            raise PlexAPIError(msg) from e

    def close(self):
        """Close the session."""
        if self.session:
            self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
