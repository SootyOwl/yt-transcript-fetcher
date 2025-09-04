import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from yt_transcript_fetcher.exceptions import NoTranscriptError, VideoNotFoundError
from yt_transcript_fetcher.models import LanguageList, Transcript
from yt_transcript_fetcher.protobuf import generate_params

YouTubeVideoID = str
"""Type alias for YouTube video ID, which is a string."""


class YouTubeTranscriptFetcher:
    """A class to fetch YouTube video transcripts and available languages."""

    def __init__(self, session=None):
        """Initialize the YouTubeTranscriptFetcher with an optional session."""
        self.session = session or requests.Session()
        # Set default headers to mimic a browser request
        self.initialise_session()
        self._context = {
            "client": {"clientName": "WEB", "clientVersion": "2.20250903.04.00"}
        }
        self.URL = (
            "https://www.youtube.com/youtubei/v1/get_transcript?prettyPrint=false"
        )
        self.languages: dict[YouTubeVideoID, LanguageList] = {}

    def initialise_session(self):
        """Set up the session with appropriate headers and retry strategy."""
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.3"
                ),
            }
        )
        # Configure retries with exponential backoff for transient errors and rate limiting
        # Sometimes (roughly 1% of requests) we get a 400 Bad Request despite the video ID being valid
        # and the request being well-formed - seems to be a gRPC FAILED_PRECONDITION error from YouTube (#3).
        # Retrying a few times seems to mitigate this issue for now.
        retry = Retry(
            total=5,
            connect=3,
            read=3,
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

        request_data = {
            "context": self._context,
            "params": lang._continuation_token,
        }

        response = self.session.post(self.URL, json=request_data, timeout=10)
        response.raise_for_status()
        response_data = response.json()
        return Transcript.from_response(lang, response_data)

    def list_languages(self, video_id) -> LanguageList:
        """Fetch all available languages for a given YouTube video."""
        request_data = {
            "context": self._context,
            "params": generate_params(video_id=video_id, language="xx"),
        }
        try:
            response = self.session.post(self.URL, json=request_data, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            if hasattr(e, "response") and e.response.status_code == 400:
                raise VideoNotFoundError(
                    f"Couldn't find transcript for video {video_id}. "
                    "Please check the video ID exists and is accessible."
                ) from e
            raise Exception(
                f"Failed to fetch languages for video {video_id}: {e}"
            ) from e
        response_data = response.json()
        self.languages[video_id] = LanguageList.from_response(response_data)
        return self.languages[video_id]
