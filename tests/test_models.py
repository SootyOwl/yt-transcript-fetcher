import pytest

from yt_transcript_fetcher.exceptions import NoSegmentsError
from yt_transcript_fetcher.models import Language, LanguageList, Segment, SegmentList, Transcript


@pytest.fixture
def sample_language(continuation_token):
    """Fixture to create a sample Language object."""
    return Language(
        code="en",
        display_name="English",
        _continuation_token=continuation_token,
    )


@pytest.fixture
def sample_language_list(sample_language):
    """Fixture to create a sample LanguageList object."""
    return LanguageList(languages=[sample_language])


@pytest.fixture
def sample_segment():
    """Fixture to create a sample Segment object."""
    return Segment(
        start_ms=120,
        end_ms=10000,
        text="Sample segment text",
        start_time_text="0:00",
        accessibility_label="0 seconds Sample segment text",
    )


@pytest.fixture
def sample_transcript(sample_language, sample_segment):
    """Fixture to create a sample Transcript object."""
    return Transcript(
        video_id="sample_video_id",
        language=sample_language,
        segments=[sample_segment],
    )


def test_language_creation(sample_language, continuation_token):
    """Test creating a Language object."""
    assert sample_language.code == "en"
    assert sample_language.display_name == "English"
    assert sample_language._continuation_token == continuation_token
    assert not sample_language.is_auto_generated


def test_language_list_creation(sample_language_list):
    """Test creating a LanguageList object."""
    assert len(sample_language_list.languages) == 1
    assert sample_language_list.languages[0].code == "en"
    assert sample_language_list.get_language_by_code("en") is not None
    assert sample_language_list.get_language_by_code("fr") is None


def test_segment_creation(sample_segment):
    """Test creating a Segment object."""
    assert sample_segment.start_ms == 120
    assert sample_segment.end_ms == 10000
    assert sample_segment.text == "Sample segment text"
    assert sample_segment.start_time_text == "0:00"
    assert sample_segment.accessibility_label == "0 seconds Sample segment text"


# test from_resposne
@pytest.fixture
def sample_response():
    """Fixture to create a sample response dictionary."""
    import json

    # tests/sampleresponse.json
    with open("tests/sampleresponse.json", "r") as f:
        return json.load(f)


def test_transcript_from_response(sample_response, sample_language):
    """Test creating a Transcript object from a response."""
    transcript = Transcript.from_response(sample_language, sample_response)

    assert transcript.video_id == "dQw4w9WgXcQ"
    assert transcript.language.code == "en"
    assert len(transcript.segments) > 0
    assert transcript.segments[0].start_ms == 1360
    assert transcript.segments[0].end_ms == 3040
    assert transcript.segments[0].text == "[♪♪♪]"


def test_language_list_from_response(sample_response):
    """Test creating a LanguageList object from a response."""
    language_list = LanguageList.from_response(sample_response)

    assert len(language_list.languages) > 0
    assert any(lang.code == "en" for lang in language_list.languages)
    assert any(lang.display_name == "English" for lang in language_list.languages)
    assert language_list.get_language_by_code("en") is not None
    assert language_list.get_language_by_code("fr") is None


@pytest.fixture
def sample_player_response():
    """Fixture with a minimal /player API response containing caption tracks."""
    return {
        "playabilityStatus": {"status": "OK"},
        "captions": {
            "playerCaptionsTracklistRenderer": {
                "captionTracks": [
                    {
                        "baseUrl": "https://www.youtube.com/api/timedtext?v=dQw4w9WgXcQ&lang=en",
                        "name": {"simpleText": "English"},
                        "languageCode": "en",
                        "kind": "asr",
                    }
                ]
            }
        },
    }


def test_language_list_from_player_response(sample_player_response):
    """Test creating a LanguageList from a /player API response."""
    language_list = LanguageList.from_player_response(sample_player_response, "dQw4w9WgXcQ")

    assert len(language_list.languages) == 1
    lang = language_list.languages[0]
    assert lang.code == "en"
    assert lang.display_name == "English"
    assert lang.is_auto_generated is True
    assert lang._base_url == "https://www.youtube.com/api/timedtext?v=dQw4w9WgXcQ&lang=en"
    assert lang._continuation_token is not None


@pytest.fixture
def sample_timedtext_response():
    """Fixture with a sample timedtext JSON3 response."""
    return {
        "wireMagic": "pb3",
        "events": [
            {"tStartMs": 0, "dDurationMs": 500, "id": 1, "wpWinPts": 1},
            {"tStartMs": 1360, "dDurationMs": 1680, "segs": [{"utf8": "[♪♪♪]"}]},
            {"tStartMs": 3040, "dDurationMs": 2000, "segs": [{"utf8": "Never gonna give you up"}]},
            {"tStartMs": 5040, "dDurationMs": 500, "segs": [{"utf8": "\n"}]},
        ],
    }


def test_segment_list_from_timedtext(sample_timedtext_response):
    """Test creating a SegmentList from a timedtext JSON3 response."""
    segment_list = SegmentList.from_timedtext(sample_timedtext_response)

    # Fixture has 4 events: 1 without segs, 2 with text, 1 with only \n
    # Only the 2 events with non-empty text should produce segments
    assert len(segment_list) == 2
    assert segment_list[0].start_ms == 1360
    assert segment_list[0].end_ms == 3040
    assert segment_list[0].text == "[♪♪♪]"
    assert segment_list[0].start_time_text == "0:01"
    assert segment_list[1].start_ms == 3040
    assert segment_list[1].text == "Never gonna give you up"


def test_segment_list_from_timedtext_no_segments():
    """Test that from_timedtext raises NoSegmentsError when there are no valid events."""
    from yt_transcript_fetcher.exceptions import NoSegmentsError

    with pytest.raises(NoSegmentsError):
        SegmentList.from_timedtext({"events": []})

    with pytest.raises(NoSegmentsError):
        SegmentList.from_timedtext({"events": [{"tStartMs": 0, "dDurationMs": 500}]})


@pytest.fixture
def segment_dict():
    """Fixture to create a sample segment dictionary."""
    return {
        "startMs": "27040",
        "endMs": "31040",
        "snippet": {
            "runs": [
                {"text": "\u266a A full commitment's\nwhat I'm thinking of \u266a"}
            ]
        },
        "startTimeText": {"simpleText": "0:27"},
        "accessibility": {
            "accessibilityData": {
                "label": "27 seconds \u266a A full commitment's\nwhat I'm thinking of \u266a"
            }
        },
        "targetId": "dQw4w9WgXcQ.CgASAmVuGgA%3D.27040.31040",
    }


def test_segment_from_dict(segment_dict):
    """Test creating a Segment object from a dictionary."""
    segment = Segment.from_dict(segment_dict)

    assert segment.start_ms == 27040
    assert segment.end_ms == 31040
    assert segment.text == "\u266a A full commitment's\nwhat I'm thinking of \u266a"
    assert segment.start_time_text == "0:27"


def test_transcript_text():
    """Test getting the full text of a transcript."""
    sample_language = Language(
        code="en",
        display_name="English",
        _continuation_token="sample_token",
    )
    sample_segment1 = Segment(
        start_ms=0,
        end_ms=1000,
        text="Hello",
        start_time_text="0:00",
        accessibility_label="0 seconds Hello",
    )
    sample_segment2 = Segment(
        start_ms=1000,
        end_ms=2000,
        text="World",
        start_time_text="0:01",
        accessibility_label="1 second World",
    )
    sample_transcript = Transcript(
        video_id="sample_video_id",
        language=sample_language,
        segments=[sample_segment1, sample_segment2],
    )
    full_text = sample_transcript.text
    assert (
        full_text == "Hello\nWorld"
    ), "Transcript text should match the concatenated segment texts."


def test_transcript_creation(sample_transcript):
    """Test creating a Transcript object."""
    assert sample_transcript.video_id == "sample_video_id"
    assert sample_transcript.language.code == "en"
    assert len(sample_transcript.segments) == 1
    assert sample_transcript.segments[0].text == "Sample segment text"


def test_transcript_invalid_creation():
    """Test creating a Transcript object with invalid data."""
    sample_language = Language(
        code="en",
        display_name="English",
        _continuation_token="sample_token",
    )

    # Test with empty segments
    with pytest.raises(
        NoSegmentsError, match="Transcript must contain at least one segment"
    ):
        Transcript(
            video_id="sample_video_id",
            language=sample_language,
            segments=[],
        )

    # Test with invalid segment type
    with pytest.raises(ValueError, match="Each segment must be an instance of Segment"):
        Transcript(
            video_id="sample_video_id",
            language=sample_language,
            segments=["invalid_segment"],
        )


def test_transcript_start_time():
    """Test getting the start time of a transcript."""
    sample_language = Language(
        code="en",
        display_name="English",
        _continuation_token="sample_token",
    )
    segment1 = Segment(
        start_ms=1000,
        end_ms=2000,
        text="First segment",
        start_time_text="0:01",
        accessibility_label="1 second First segment",
    )
    segment2 = Segment(
        start_ms=3000,
        end_ms=4000,
        text="Second segment",
        start_time_text="0:03",
        accessibility_label="3 seconds Second segment",
    )
    transcript = Transcript(
        video_id="sample_video_id",
        language=sample_language,
        segments=[segment1, segment2],
    )

    assert transcript.start_time == 1000


def test_transcript_end_time():
    """Test getting the end time of a transcript."""
    sample_language = Language(
        code="en",
        display_name="English",
        _continuation_token="sample_token",
    )
    segment1 = Segment(
        start_ms=1000,
        end_ms=2000,
        text="First segment",
        start_time_text="0:01",
        accessibility_label="1 second First segment",
    )
    segment2 = Segment(
        start_ms=3000,
        end_ms=4000,
        text="Second segment",
        start_time_text="0:03",
        accessibility_label="3 seconds Second segment",
    )
    transcript = Transcript(
        video_id="sample_video_id",
        language=sample_language,
        segments=[segment1, segment2],
    )

    assert transcript.end_time == 4000


def test_transcript_duration():
    """Test getting the duration of a transcript."""
    sample_language = Language(
        code="en",
        display_name="English",
        _continuation_token="sample_token",
    )
    segment1 = Segment(
        start_ms=1000,
        end_ms=2000,
        text="First segment",
        start_time_text="0:01",
        accessibility_label="1 second First segment",
    )
    segment2 = Segment(
        start_ms=3000,
        end_ms=5000,
        text="Second segment",
        start_time_text="0:03",
        accessibility_label="3 seconds Second segment",
    )
    transcript = Transcript(
        video_id="sample_video_id",
        language=sample_language,
        segments=[segment1, segment2],
    )

    assert transcript.duration == 4000  # 5000 - 1000


def test_transcript_language_code():
    """Test getting the language code of a transcript."""
    sample_language = Language(
        code="fr",
        display_name="French",
        _continuation_token="sample_token",
    )
    segment = Segment(
        start_ms=1000,
        end_ms=2000,
        text="Bonjour",
        start_time_text="0:01",
        accessibility_label="1 second Bonjour",
    )
    transcript = Transcript(
        video_id="sample_video_id",
        language=sample_language,
        segments=[segment],
    )

    assert transcript.language_code == "fr"


def test_transcript_get_segment_by_time():
    """Test getting a segment by time."""
    sample_language = Language(
        code="en",
        display_name="English",
        _continuation_token="sample_token",
    )
    segment1 = Segment(
        start_ms=1000,
        end_ms=2000,
        text="First segment",
        start_time_text="0:01",
        accessibility_label="1 second First segment",
    )
    segment2 = Segment(
        start_ms=2000,
        end_ms=3000,
        text="Second segment",
        start_time_text="0:02",
        accessibility_label="2 seconds Second segment",
    )
    transcript = Transcript(
        video_id="sample_video_id",
        language=sample_language,
        segments=SegmentList([segment1, segment2]),
    )

    # Test finding segment
    found_segment = transcript.get_segment_by_time(1500)
    assert found_segment == segment1

    # Test finding second segment
    found_segment = transcript.get_segment_by_time(2500)
    assert found_segment == segment2

    # Test time not in any segment
    found_segment = transcript.get_segment_by_time(5000)
    assert found_segment is None


def test_transcript_get_segments_by_text():
    """Test getting segments by text content."""
    sample_language = Language(
        code="en",
        display_name="English",
        _continuation_token="sample_token",
    )
    segment1 = Segment(
        start_ms=1000,
        end_ms=2000,
        text="Hello world",
        start_time_text="0:01",
        accessibility_label="1 second Hello world",
    )
    segment2 = Segment(
        start_ms=2000,
        end_ms=3000,
        text="Goodbye world",
        start_time_text="0:02",
        accessibility_label="2 seconds Goodbye world",
    )
    segment3 = Segment(
        start_ms=3000,
        end_ms=4000,
        text="Hello again",
        start_time_text="0:03",
        accessibility_label="3 seconds Hello again",
    )
    transcript = Transcript(
        video_id="sample_video_id",
        language=sample_language,
        segments=SegmentList([segment1, segment2, segment3]),
    )

    # Test finding segments with "world"
    segments_with_world = transcript.get_segments_by_text("world")
    assert len(segments_with_world) == 2
    assert segment1 in segments_with_world
    assert segment2 in segments_with_world

    # Test finding segments with "hello" (case insensitive)
    segments_with_hello = transcript.get_segments_by_text("hello")
    assert len(segments_with_hello) == 2
    assert segment1 in segments_with_hello
    assert segment3 in segments_with_hello

    # Test finding segments with non-existent text
    segments_with_xyz = transcript.get_segments_by_text("xyz")
    assert len(segments_with_xyz) == 0


def test_transcript_get_segments_by_time_range():
    """Test getting segments by time range."""
    sample_language = Language(
        code="en",
        display_name="English",
        _continuation_token="sample_token",
    )
    segment1 = Segment(
        start_ms=1000,
        end_ms=2000,
        text="First segment",
        start_time_text="0:01",
        accessibility_label="1 second First segment",
    )
    segment2 = Segment(
        start_ms=2000,
        end_ms=3000,
        text="Second segment",
        start_time_text="0:02",
        accessibility_label="2 seconds Second segment",
    )
    segment3 = Segment(
        start_ms=4000,
        end_ms=5000,
        text="Third segment",
        start_time_text="0:04",
        accessibility_label="4 seconds Third segment",
    )
    transcript = Transcript(
        video_id="sample_video_id",
        language=sample_language,
        segments=SegmentList([segment1, segment2, segment3]),
    )

    # Test overlapping range
    segments_in_range = transcript.get_segments_by_time_range(1500, 2500)
    assert len(segments_in_range) == 2
    assert segment1 in segments_in_range
    assert segment2 in segments_in_range

    # Test exact match
    segments_in_range = transcript.get_segments_by_time_range(2000, 3000)
    assert len(segments_in_range) == 1
    assert segment2 in segments_in_range

    # Test no overlap
    segments_in_range = transcript.get_segments_by_time_range(3500, 3800)
    assert len(segments_in_range) == 0

    # Test range that includes all segments
    segments_in_range = transcript.get_segments_by_time_range(0, 6000)
    assert len(segments_in_range) == 3


def test_transcript_empty_segments_properties():
    """Test transcript properties with empty segments."""
    sample_language = Language(
        code="en",
        display_name="English",
        _continuation_token="sample_token",
    )

    # Create a transcript that would pass validation but test edge cases
    segment = Segment(
        start_ms=1000,
        end_ms=2000,
        text="Test",
        start_time_text="0:01",
        accessibility_label="1 second Test",
    )
    transcript = Transcript(
        video_id="sample_video_id",
        language=sample_language,
        segments=[segment],
    )

    # Clear segments to test edge case behavior
    transcript.segments = []

    assert transcript.start_time == 0
    assert transcript.end_time == 0
    assert transcript.duration == 0
