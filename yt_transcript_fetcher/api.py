import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from yt_transcript_fetcher import _panel
from yt_transcript_fetcher.exceptions import NoTranscriptError, VideoNotFoundError, YouTubeAPIError
from yt_transcript_fetcher.models import LanguageList, Transcript

YouTubeVideoID = str
"""Type alias for YouTube video ID, which is a string."""


class YouTubeTranscriptFetcher:
    """A class to fetch YouTube video transcripts and available languages."""

    # Player discovery and modern panels use separate client profiles.
    CLIENT = {
        "clientName": "ANDROID",
        "clientVersion": "20.10.38",
        "userAgent": "com.google.android.youtube/20.10.38 (Linux; U; Android 11) gzip",
        "osName": "Android",
        "osVersion": "11",
    }
    PANEL_CLIENT = {
        "clientName": "WEB",
        "clientVersion": "2.20261020.01.00",
        "hl": "en",
        "gl": "GB",
    }

    def __init__(self, session=None):
        """Initialize the YouTubeTranscriptFetcher with an optional session.
        
        Args:
            session: An optional requests.Session object to use for API calls.
        """
        self.session = session if session is not None else requests.Session()
        self._context = {"client": self.CLIENT.copy()}
        self._panel_context = {"client": self.PANEL_CLIENT.copy()}
        # Initialise session if not provided, otherwise assume it's already set up
        if session is None:
            self.initialise_session()
        self.URL = (
            "https://www.youtube.com/youtubei/v1/get_panel?prettyPrint=false"
        )
        self.PLAYER_URL = (
            "https://www.youtube.com/youtubei/v1/player?prettyPrint=false"
        )
        self.languages: dict[YouTubeVideoID, LanguageList] = {}

    def initialise_session(self):
        """Set up the session with appropriate headers and retry strategy."""
        # Get User-Agent from client config, or use default web UA
        client_config = self._context.get("client", {})
        user_agent = client_config.get(
            "userAgent",
            "Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0,gzip(gfe)"
        )
        
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": user_agent,
            }
        )
        # Configure retries with exponential backoff for transient errors and rate limiting
        retry = Retry(
            total=2,
            connect=1,
            read=2,
            backoff_factor=0.3,
            status_forcelist=(
                500,
                502,
                503,
                504,
                429,
            ),
            allowed_methods=frozenset(["POST"]),
            raise_on_status=False,
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _post(self, url, request_data, timeout):
        response = self.session.post(url, json=request_data, timeout=timeout)
        if response.status_code == 400:
            try:
                error_data = response.json()
            except ValueError:
                error_data = None
            if isinstance(error_data, dict) and isinstance(error_data.get("error"), dict):
                if error_data["error"].get("status") == "FAILED_PRECONDITION":
                    raise YouTubeAPIError("YouTube API precondition failed for the current client request.")
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError as error:
            raise YouTubeAPIError("YouTube returned an invalid JSON response.") from error
        if not isinstance(data, dict) or "error" in data:
            raise YouTubeAPIError("YouTube returned an invalid API response.")
        return data

    def get_transcript(self, video_id, language="en"):
        """Fetch the transcript for a given YouTube video in the specified language."""
        # if we have already fetched the languages for this video, use it
        if video_id in self.languages:
            language_list = self.languages[video_id]
        else:
            # Fetch the list of languages first
            language_list = self.list_languages(video_id)

        lang = language_list.get_language_by_code(language)
        if not lang:
            raise NoTranscriptError(
                f"No transcript available for video {video_id} in language {language}."
            )

        track_id = getattr(lang, "_vss_id", None) or (
            ("a." if lang.is_auto_generated else ".") + lang.code
        )

        request_data = {
            "context": self._panel_context,
            "panelId": _panel.PANEL_ID,
            "params": _panel.encode_params(video_id, track_id),
        }

        response_data = self._post(self.URL, request_data, timeout=10)
        if not isinstance(response_data.get("content"), dict) or "engagementPanelSectionListRenderer" not in response_data["content"]:
            raise YouTubeAPIError("YouTube did not return a modern transcript panel.")
        return Transcript.from_response(lang, response_data)

    def list_languages(self, video_id) -> LanguageList:
        """Fetch all available languages for a given YouTube video.
        
        Uses the /player API to get caption tracks, which provides language
        information without requiring attestation (PO Token).
        """
        request_data = {
            "context": self._context,
            "videoId": video_id,
            "playbackContext": {
                "contentPlaybackContext": {
                    "html5Preference": "HTML5_PREF_WANTS",
                }
            },
            "contentCheckOk": True,
            "racyCheckOk": True,
        }
        try:
            response_data = self._post(self.PLAYER_URL, request_data, timeout=15)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                raise VideoNotFoundError(
                    f"Couldn't find video {video_id}. "
                    "Please check the video ID exists and is accessible."
                ) from e
            raise
        
        # Check playability status
        playability = response_data.get("playabilityStatus", {})
        if not isinstance(playability, dict) or not playability.get("status"):
            raise YouTubeAPIError("YouTube did not return a player playability status.")
        status = playability.get("status")
        if status != "OK":
            reason = playability.get("reason", "Unknown reason")
            raise VideoNotFoundError(
                f"Video {video_id} is not playable: {reason}"
            )
        
        self.languages[video_id] = LanguageList.from_player_response(response_data, video_id)
        return self.languages[video_id]
