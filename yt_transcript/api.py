from encodings.punycode import T
from typing import Optional
import requests
from yt_transcript.exceptions import NoTranscriptError, VideoNotFoundError
from yt_transcript.protobuf import generate_params
from yt_transcript.models import LanguageList, Transcript


YouTubeVideoID = str
"""Type alias for YouTube video ID, which is a string."""


class YouTubeTranscriptFetcher:
    """A class to fetch YouTube video transcripts and available languages."""

    def __init__(self, session=None):
        """Initialize the YouTubeTranscriptFetcher with an optional session."""
        self.session = session or requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self._context = {
            "client": {"clientName": "WEB", "clientVersion": "2.20250609.01.00"}
        }
        self.URL = (
            "https://www.youtube.com/youtubei/v1/get_transcript?prettyPrint=false"
        )
        self.languages: dict[YouTubeVideoID, LanguageList] = {}

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
            if hasattr(e, 'response') and e.response.status_code == 400:
                raise VideoNotFoundError(
                    f"Couldn't find transcript for video {video_id}. "
                    "Please check the video ID exists and is accessible."
                ) from e
            raise Exception(f"Failed to fetch languages for video {video_id}: {e}") from e
        response_data = response.json()
        self.languages[video_id] = LanguageList.from_response(response_data)
        return self.languages[video_id]
