import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from yt_transcript_fetcher.exceptions import NoTranscriptError, VideoNotFoundError, YouTubeAPIError
from yt_transcript_fetcher.models import LanguageList, Transcript
from yt_transcript_fetcher.protobuf import encode_visitor_data, generate_params

YouTubeVideoID = str
"""Type alias for YouTube video ID, which is a string."""


class YouTubeTranscriptFetcher:
    """A class to fetch YouTube video transcripts and available languages."""

    # Client configuration for YouTube's internal API
    # As of March 2026, using iOS client which doesn't require attestation (PO Token)
    # Android clients started requiring attestation again, but iOS still works
    # See: https://github.com/yt-dlp/yt-dlp/issues/10085
    CLIENT = {
        "clientName": "IOS",
        "clientVersion": "19.16.3",
        "userAgent": "com.google.ios.youtube/19.16.3 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X;)",
        "deviceMake": "Apple",
        "deviceModel": "iPhone16,2",
        "osName": "iOS",
        "osVersion": "17.5.1.21F90",
    }

    def __init__(self, session=None):
        """Initialize the YouTubeTranscriptFetcher with an optional session.
        
        Args:
            session: An optional requests.Session object to use for API calls.
        """
        self.session = session or requests.Session()
        
        # Generate visitorData using the same approach as YouTube.js
        # This is a protobuf-encoded token that identifies the session
        # and is required by YouTube's API to avoid FAILED_PRECONDITION errors
        self._visitor_data = encode_visitor_data()
        
        # Build context with client config and visitorData
        client_config = self.CLIENT.copy()
        client_config["visitorData"] = self._visitor_data
        self._context = {"client": client_config}
        # Initialise session if not provided, otherwise assume it's already set up
        if not session:
            self.initialise_session()
        self.URL = (
            "https://www.youtube.com/youtubei/v1/get_transcript?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8&prettyPrint=false"
        )
        self.PLAYER_URL = (
            "https://www.youtube.com/youtubei/v1/player?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8&prettyPrint=false"
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
        # Sometimes (roughly 1% of requests) we get a 400 Bad Request despite the video ID being valid
        # and the request being well-formed - seems to be a gRPC FAILED_PRECONDITION error from YouTube (#3).
        # Retrying a few times seems to mitigate this issue for now.
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
                400,
            ),
            allowed_methods=frozenset(["POST"]),
            raise_on_status=False,
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

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

        # Generate params with correct auto_generated flag based on caption type
        params = generate_params(
            video_id=video_id,
            language=lang.code,
            auto_generated=lang.is_auto_generated
        )

        request_data = {
            "context": self._context,
            "params": params,
        }

        response = self.session.post(self.URL, json=request_data, timeout=10)
        response.raise_for_status()
        response_data = response.json()
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
            response = self.session.post(self.PLAYER_URL, json=request_data, timeout=15)
            response.raise_for_status()
        except requests.RequestException as e:
            if hasattr(e, "response") and e.response is not None:
                if e.response.status_code == 400:
                    error_data = e.response.json() if e.response.headers.get('content-type', '').startswith('application/json') else {}
                    if error_data.get('error', {}).get('status') == 'FAILED_PRECONDITION':
                        raise YouTubeAPIError(
                            f"API precondition failed for video {video_id}. "
                            "This may indicate that the video is not available.\n"
                            f"Response: {error_data}"
                        ) from e
                raise VideoNotFoundError(
                    f"Couldn't find video {video_id}. "
                    "Please check the video ID exists and is accessible."
                ) from e
            raise Exception(
                f"Failed to fetch languages for video {video_id}: {e}"
            ) from e
        
        response_data = response.json()
        
        # Check playability status
        playability = response_data.get("playabilityStatus", {})
        status = playability.get("status")
        if status != "OK":
            reason = playability.get("reason", "Unknown reason")
            raise VideoNotFoundError(
                f"Video {video_id} is not playable: {reason}"
            )
        
        self.languages[video_id] = LanguageList.from_player_response(response_data, video_id)
        return self.languages[video_id]
