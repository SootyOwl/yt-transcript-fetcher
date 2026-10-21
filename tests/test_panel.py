"""Modern wire fixtures and compatibility with the existing public models."""

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from yt_transcript_fetcher import Language, LanguageList, Segment, SegmentList, Transcript
from yt_transcript_fetcher import _panel
from yt_transcript_fetcher.exceptions import NoSegmentsError, NoTranscriptError, YouTubeAPIError
from yt_transcript_fetcher.protobuf import generate_params


@pytest.fixture
def panel():
    return json.loads(Path(__file__).with_name("fixtures").joinpath("modern_panel.json").read_text())


@pytest.mark.parametrize("track,expected", [
    (None, "qgkPCgtkUXc0dzlXZ1hjURgC"),
    (".en", "qgkUCgtkUXc0dzlXZ1hjURgCMgMuZW4%3D"),
])
def test_captured_wire_encoding(track, expected):
    assert _panel.encode_params("dQw4w9WgXcQ", track) == expected


def test_selection_comes_from_server_continuation(panel):
    assert _panel.selection(panel) == ("jNQXAC9IVRw", ".en")


def test_new_response_keeps_public_model_contract(panel):
    language = Language("en", "English", False, generate_params("jNQXAC9IVRw", "en", False))
    transcript = Transcript.from_response(language, panel)
    assert transcript.video_id == "jNQXAC9IVRw"
    assert transcript.language is language
    assert isinstance(transcript.segments, SegmentList)
    assert all(isinstance(segment, Segment) for segment in transcript.segments)
    assert [(s.start_ms, s.end_ms, s.text) for s in transcript.segments] == [
        (1000, 7974, "Sample text 1"),
        (7000, 15733, "Sample text 2"),
        (16000, 18881, "Sample text 3"),
    ]
    assert transcript.text == "Sample text 1\nSample text 2\nSample text 3"
    assert transcript.start_time == 1000
    assert transcript.end_time == 18881
    assert transcript.duration == 17881
    assert transcript.get_segment_by_time(8000) is transcript.segments[1]
    assert len(transcript.get_segments_by_text("SAMPLE")) == 3
    assert len(transcript.get_segments_by_time_range(9000, 10000)) == 1
    assert transcript.segments[0].start_time_text == "0:01"
    assert transcript.segments[0].accessibility_label == "Seek to sample 1"


@pytest.mark.parametrize("fault", ["missing_end", "reversed", "negative_index", "wrong_seek", "missing_entity", "duplicate_index"])
def test_bad_timing_never_returns_fabricated_or_partial_transcript(panel, fault):
    entity = panel["frameworkUpdates"]["entityBatchUpdate"]["mutations"][1]["payload"]["timedMarkersListSyncEntity"]
    view = panel["content"]["engagementPanelSectionListRenderer"]["content"]["sectionListRenderer"]["contents"][1]["itemSectionRenderer"]["contents"][0]["macroMarkersPanelItemViewModel"]
    if fault == "missing_end":
        del entity["timedListData"]["sections"][1]["timedSyncDataList"][1]["endTimeMs"]
    elif fault == "reversed":
        entity["timedListData"]["sections"][1]["timedSyncDataList"][1]["endTimeMs"] = "0"
    elif fault == "negative_index":
        view["index"] = -1
    elif fault == "wrong_seek":
        view["onTap"]["innertubeCommand"]["watchEndpoint"]["startTimeSeconds"] = 999
    elif fault == "missing_entity":
        entity["key"] = "wrong"
    else:
        view["index"] = 1
    with pytest.raises(YouTubeAPIError):
        SegmentList.from_response(panel)


def test_empty_panel_keeps_no_segments_error(panel):
    panel["content"]["engagementPanelSectionListRenderer"]["content"]["sectionListRenderer"]["contents"] = []
    with pytest.raises(NoSegmentsError):
        SegmentList.from_response(panel)


def test_wrong_selected_track_is_not_returned_as_requested(panel):
    lang = Language("ja", "Japanese", False, generate_params("jNQXAC9IVRw", "ja", False))
    with pytest.raises(NoTranscriptError):
        Transcript.from_response(lang, panel)


def test_wrong_selected_video_is_rejected(panel):
    lang = Language("en", "English", False, generate_params("dQw4w9WgXcQ", "en", False))
    with pytest.raises(YouTubeAPIError):
        Transcript.from_response(lang, panel)


def test_player_track_identity_does_not_change_dataclass_schema():
    data = {"captions": {"playerCaptionsTracklistRenderer": {"captionTracks": [
        {"languageCode": "en", "name": {"simpleText": "English"}, "vssId": ".en.named-track"},
    ]}}}
    lang = LanguageList.from_player_response(data, "jNQXAC9IVRw")[0]
    assert getattr(lang, "_vss_id", None) == ".en.named-track"
    assert getattr(lang, "_default_vss_id", None) == ".en.named-track"
    assert set(asdict(lang)) == {"code", "display_name", "is_auto_generated", "_continuation_token"}


@pytest.mark.parametrize("default,requested,error", [
    ("a.fil", "fil", None),
    (None, "fil", YouTubeAPIError),
    (".en", "fil", NoTranscriptError),
])
def test_missing_selected_track_is_resolved_only_from_known_default(panel, default, requested, error):
    header = panel["content"]["engagementPanelSectionListRenderer"]["content"]["sectionListRenderer"]["header"]
    # Captured ASR-only continuation omits panel params field 6.
    header["searchInputViewModel"]["onInputAction"]["command"]["innertubeCommand"]["continuationCommand"]["token"] = "kta-ngs0EhhQQW1vZGVybl90cmFuc2NyaXB0X3ZpZXcaGHFna1BDZ3RTZERab1IzWjZTRkl0YnhnQw%3D%3D"
    tracks = [{"languageCode": "fil", "kind": "asr", "vssId": "a.fil"}]
    metadata = {"captionTracks": tracks}
    if default != "a.fil":
        tracks.append({"languageCode": "en", "vssId": ".en"})
    if default == ".en":
        metadata["audioTracks"] = [{"defaultCaptionTrackIndex": 1}]
        metadata["defaultAudioTrackIndex"] = 0
    lang = LanguageList.from_player_response({"captions": {"playerCaptionsTracklistRenderer": metadata}}, "Rt6hGvzHR-o").get_language_by_code(requested)
    if error:
        with pytest.raises(error):
            Transcript.from_response(lang, panel)
    else:
        assert Transcript.from_response(lang, panel).language is lang


@pytest.mark.parametrize("token", ["not!base64", "qgkPCgtk", "AA==", "gICAgICAgICAgIA="])
def test_malformed_continuation_is_a_protocol_error(panel, token):
    header = panel["content"]["engagementPanelSectionListRenderer"]["content"]["sectionListRenderer"]["header"]
    header["searchInputViewModel"]["onInputAction"]["command"]["innertubeCommand"]["continuationCommand"]["token"] = token
    with pytest.raises(YouTubeAPIError):
        _panel.selection(panel)


def test_missing_view_does_not_return_a_partial_transcript(panel):
    sections = panel["content"]["engagementPanelSectionListRenderer"]["content"]["sectionListRenderer"]["contents"]
    sections[1]["itemSectionRenderer"]["contents"].pop()
    with pytest.raises(YouTubeAPIError):
        SegmentList.from_response(panel)


def test_reordered_views_cannot_corrupt_timing_helpers(panel):
    sections = panel["content"]["engagementPanelSectionListRenderer"]["content"]["sectionListRenderer"]["contents"]
    sections.reverse()
    for section in sections:
        section["itemSectionRenderer"].get("contents", []).reverse()
    with pytest.raises(YouTubeAPIError):
        SegmentList.from_response(panel)


def test_unknown_content_mixed_with_transcript_is_not_silently_dropped(panel):
    sections = panel["content"]["engagementPanelSectionListRenderer"]["content"]["sectionListRenderer"]["contents"]
    views = sections[0]["itemSectionRenderer"]["contents"][0]["macroMarkersPanelItemViewModel"]["item"]["timelineItemViewModel"]["contentItems"]
    views.append({"unknownTextViewModel": {"simpleText": "Additional transcript text"}})
    with pytest.raises(YouTubeAPIError):
        SegmentList.from_response(panel)


@pytest.mark.parametrize("audio_tracks", [None, [None], {"0": {}}, "invalid"])
def test_invalid_optional_audio_metadata_preserves_language_discovery(audio_tracks):
    tracks = [{"languageCode": "en", "vssId": ".en"}, {"languageCode": "ja", "vssId": ".ja"}]
    languages = LanguageList.from_player_response({"captions": {"playerCaptionsTracklistRenderer": {
        "captionTracks": tracks, "audioTracks": audio_tracks,
    }}}, "jNQXAC9IVRw")
    assert [lang.code for lang in languages] == ["en", "ja"]
    assert all(lang._default_vss_id is None for lang in languages)


def test_legacy_android_factory_is_preserved():
    legacy = {"actions": [{"elementsCommand": {"transformEntityCommand": {"arguments": {
        "transformTranscriptSegmentListArguments": {"overwrite": {"initialSegments": [{
            "transcriptSegmentRenderer": {"startMs": "120", "endMs": "2520", "snippet": {
                "elementsAttributedString": {"content": "Legacy Android text"}
            }},
        }]}}
    }}}}]}
    lang = Language("en", "English", False, generate_params("jNQXAC9IVRw", "en", False))
    transcript = Transcript.from_response(lang, legacy)
    assert transcript.video_id == "jNQXAC9IVRw"
    assert transcript.text == "Legacy Android text"
    assert (transcript.start_time, transcript.end_time) == (120, 2520)
