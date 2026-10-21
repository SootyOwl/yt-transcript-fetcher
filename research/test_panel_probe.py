"""Protocol fixtures and timing regressions for the isolated panel prototype."""

import copy

import pytest

from panel_probe import PanelProtocolError, encode_params, parse_panel


def test_params_match_regular_browser_capture():
    assert encode_params("dQw4w9WgXcQ") == "qgkPCgtkUXc0dzlXZ1hjURgC"


def test_track_params_match_server_continuation():
    assert encode_params("dQw4w9WgXcQ", ".en") == "qgkUCgtkUXc0dzlXZ1hjURgCMgMuZW4%3D"


@pytest.fixture
def chapter_panel():
    # Reduced from the captured chapter-bearing response. Chapter headings
    # consume indices 0 and 2; transcript entries use global indices 1 and 3.
    def item(index, text, seconds):
        return {"macroMarkersPanelItemViewModel": {
            "index": index,
            "item": {"timelineItemViewModel": {"contentItems": [
                {"transcriptSegmentViewModel": {"simpleText": text}}
            ]}},
            "onTap": {"innertubeCommand": {"watchEndpoint": {"startTimeSeconds": seconds}}},
        }}

    return {
        "content": {"engagementPanelSectionListRenderer": {
            "onShowCommands": [{"updateTimedMarkersSyncObserverCommand": {"timedSyncEntityKey": "selected"}}],
            "content": {"sectionListRenderer": {"contents": [
                {"itemSectionRenderer": {"contents": [item(1, "First segment", 1)]}},
                {"itemSectionRenderer": {"contents": [item(3, "Second segment", 6)]}},
            ]}},
        }},
        "frameworkUpdates": {"entityBatchUpdate": {"mutations": [
            {"payload": {"timedMarkersListSyncEntity": {"key": "unrelated", "timedListData": {"sections": []}}}},
            {"payload": {"timedMarkersListSyncEntity": {"key": "selected", "timedListData": {"sections": [
                {"timedSyncDataList": [
                    {"videoTimeMs": "0"},
                    {"videoTimeMs": "1000", "endTimeMs": "3040"},
                ]},
                {"timedSyncDataList": [
                    {"videoTimeMs": "5000"},
                    {"videoTimeMs": "6000", "endTimeMs": "9876"},
                ]},
            ]}}}},
        ]}},
    }


def test_chapter_headers_do_not_shift_transcript_timing(chapter_panel):
    assert parse_panel(chapter_panel) == [
        {"start_ms": 1000, "end_ms": 3040, "text": "First segment"},
        {"start_ms": 6000, "end_ms": 9876, "text": "Second segment"},
    ]


def test_missing_end_time_is_rejected_instead_of_invented(chapter_panel):
    data = copy.deepcopy(chapter_panel)
    entity = data["frameworkUpdates"]["entityBatchUpdate"]["mutations"][1]["payload"]["timedMarkersListSyncEntity"]
    del entity["timedListData"]["sections"][1]["timedSyncDataList"][1]["endTimeMs"]
    with pytest.raises(PanelProtocolError):
        parse_panel(data)


def test_http_success_without_a_transcript_is_not_success():
    with pytest.raises(PanelProtocolError):
        parse_panel({"responseContext": {}})


@pytest.mark.parametrize("requested_track", [".en", ".ja"])
def test_server_selected_track_is_checked(chapter_panel, requested_track):
    section_list = chapter_panel["content"]["engagementPanelSectionListRenderer"]["content"]["sectionListRenderer"]
    section_list["header"] = {"searchInputViewModel": {"onInputAction": {"command": {"innertubeCommand": {
        "continuationCommand": {
            "token": "kta-ngs-EhhQQW1vZGVybl90cmFuc2NyaXB0X3ZpZXcaInFna1VDZ3RrVVhjMGR6bFhaMWhqVVJnQ01nTXVaVzQlM0Q%3D",
            "request": "CONTINUATION_REQUEST_TYPE_GET_PANEL",
        }
    }}}}}
    if requested_track == ".en":
        assert len(parse_panel(chapter_panel, expected_track=requested_track)) == 2
    else:
        with pytest.raises(PanelProtocolError):
            parse_panel(chapter_panel, expected_track=requested_track)
