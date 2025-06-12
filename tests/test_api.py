import pytest
from yt_transcript.api import YouTubeTranscriptFetcher
from yt_transcript.exceptions import NoTranscriptError, VideoNotFoundError
from yt_transcript.models import Language


@pytest.fixture
def fetcher():
    """Fixture to create a YouTubeTranscriptFetcher instance."""
    return YouTubeTranscriptFetcher()


def test_list_languages(fetcher):
    """Test listing transcripts for a YouTube video."""
    video_id = "dQw4w9WgXcQ"  # Example video ID
    language_list = fetcher.list_languages(video_id)

    assert language_list is not None
    assert len(language_list.languages) > 0
    assert all(isinstance(lang, Language) for lang in language_list.languages)
    print("Available languages:", language_list)
    assert any(
        lang.code == "en" for lang in language_list.languages
    ), "English language not found in the list."
    assert "English (en)" in str(language_list)

def test_list_languages_no_video(fetcher):
    """Test listing languages for a non-existent YouTube video."""
    with pytest.raises(VideoNotFoundError) as exc_info:
        fetcher.list_languages("11111111111")
    assert "Couldn't find transcript for video 11111111111. Please check the video ID exists and is accessible." in str(exc_info.value)

def test_get_transcript(fetcher):
    """Test fetching a transcript for a YouTube video."""
    video_id = "dQw4w9WgXcQ"  # Example video ID
    language = "en"  # English language code

    transcript = fetcher.get_transcript(video_id, language)
    assert transcript is not None
    assert transcript.video_id == video_id
    assert transcript.language.code == language

def test_get_transcript_no_video(fetcher):
    """Test fetching a transcript for a non-existent YouTube video."""
    with pytest.raises(VideoNotFoundError) as exc_info:
        fetcher.get_transcript("11111111111", "en")
    assert "Couldn't find transcript for video 11111111111. Please check the video ID exists and is accessible." in str(exc_info.value)

def test_get_transcript_no_language(fetcher):
    """Test fetching a transcript for a video with no available language."""
    video_id = "dQw4w9WgXcQ"  # Example video ID
    language = "xx"  # Non-existent language code

    with pytest.raises(NoTranscriptError) as exc_info:
        fetcher.get_transcript(video_id, language)
    assert f"No transcript available for video {video_id} in language {language}." in str(exc_info.value)
