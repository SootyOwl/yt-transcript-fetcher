from .api import YouTubeTranscriptFetcher
from .exceptions import (
    InvalidLanguageCodeError,
    NoLanguageError,
    NoSegmentsError,
    NoTranscriptError,
    VideoNotFoundError,
)
from .models import Language, LanguageList, Segment, SegmentList, Transcript

_default_fetcher = YouTubeTranscriptFetcher()


def get_transcript(video_id, language="en"):
    """Fetch the transcript for a YouTube video in the specified language."""
    return _default_fetcher.get_transcript(video_id, language)


def list_languages(video_id):
    """Fetch all available languages for a given YouTube video."""
    return _default_fetcher.list_languages(video_id)


__all__ = [
    "YouTubeTranscriptFetcher",
    "get_transcript",
    "list_languages",
    "Language",
    "LanguageList",
    "Segment",
    "SegmentList",
    "Transcript",
    "InvalidLanguageCodeError",
    "NoLanguageError",
    "NoSegmentsError",
    "NoTranscriptError",
    "VideoNotFoundError",
]
