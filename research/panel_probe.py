"""Experimental modern transcript panel; independent of the production backend."""

import argparse
import base64
import hashlib
import json
import re
import sys
from urllib.parse import quote, unquote

import requests

CLIENT_VERSION = "2.20261020.01.00"  # Observed 2026-10-21; configurable in CLI.
PANEL_ID = "PAmodern_transcript_view"


class PanelProtocolError(ValueError):
    pass


def encode_params(video_id, track_id=None):
    """Encode observed fields 149 -> {1: video, 3: 2, 6: optional vssId}."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("Expected an 11-character video ID")

    def varint(value):
        result = bytearray()
        while value > 127:
            result.append((value & 127) | 128)
            value >>= 7
        result.append(value)
        return bytes(result)

    def field(number, data):
        return varint((number << 3) | 2) + varint(len(data)) + data

    nested = field(1, video_id.encode("ascii")) + b"\x18\x02"
    if track_id is not None:
        nested += field(6, track_id.encode("utf-8"))
    return quote(base64.b64encode(field(149, nested)).decode("ascii"))


def _wire_fields(data):
    """Decode the observed varint/length-delimited continuation fields only."""
    offset = 0

    def varint():
        nonlocal offset
        value = 0
        for shift in range(0, 70, 7):
            if offset >= len(data):
                break
            byte = data[offset]
            offset += 1
            value |= (byte & 127) << shift
            if byte < 128:
                return value
        raise PanelProtocolError("Truncated or oversized continuation varint")

    fields = {}
    while offset < len(data):
        tag = varint()
        number, wire_type = tag >> 3, tag & 7
        if not number or number in fields:
            raise PanelProtocolError("Invalid or repeated continuation field")
        if wire_type == 0:
            value = varint()
        elif wire_type == 2:
            length = varint()
            if length > len(data) - offset:
                raise PanelProtocolError("Truncated continuation field")
            value = data[offset:offset + length]
            offset += length
        else:
            raise PanelProtocolError("Unsupported continuation wire type")
        fields[number] = value
    return fields


def _selected_track(section_list):
    def decode(value):
        value = unquote(value)
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

    command = section_list["header"]["searchInputViewModel"]["onInputAction"]["command"]["innertubeCommand"]["continuationCommand"]
    if command["request"] != "CONTINUATION_REQUEST_TYPE_GET_PANEL":
        raise PanelProtocolError("Unexpected transcript continuation route")
    continuation = _wire_fields(_wire_fields(decode(command["token"]))[377091426])
    if continuation[2].decode("utf-8") != PANEL_ID:
        raise PanelProtocolError("Unexpected transcript continuation panel")
    params = _wire_fields(decode(continuation[3].decode("ascii")))
    return _wire_fields(params[149])[6].decode("utf-8")


def parse_panel(response, expected_track=None):
    """Join transcript views to their referenced timing entity by global index.

    Chapter headers occupy timing slots too. Never zip only transcript views
    with all timings or infer an end timestamp from the following segment.
    """
    try:
        panel = response["content"]["engagementPanelSectionListRenderer"]
        section_list = panel["content"]["sectionListRenderer"]
        if expected_track is not None and _selected_track(section_list) != expected_track:
            raise PanelProtocolError("Server selected a different caption track")
        keys = {
            command["updateTimedMarkersSyncObserverCommand"]["timedSyncEntityKey"]
            for command in panel["onShowCommands"]
            if "updateTimedMarkersSyncObserverCommand" in command
        }
        if len(keys) != 1:
            raise PanelProtocolError("Expected one transcript timing entity reference")
        entities = [
            mutation["payload"]["timedMarkersListSyncEntity"]
            for mutation in response["frameworkUpdates"]["entityBatchUpdate"]["mutations"]
            if mutation.get("payload", {}).get("timedMarkersListSyncEntity", {}).get("key") in keys
        ]
        if len(entities) != 1:
            raise PanelProtocolError("Missing or ambiguous transcript timing entity")
        timings = [
            timing
            for section in entities[0]["timedListData"]["sections"]
            for timing in section["timedSyncDataList"]
        ]
        segments = []
        for section in section_list["contents"]:
            for wrapper in section.get("itemSectionRenderer", {}).get("contents", []):
                item = wrapper.get("macroMarkersPanelItemViewModel")
                if item is None:
                    continue
                views = item["item"]["timelineItemViewModel"]["contentItems"]
                transcript_views = [view["transcriptSegmentViewModel"] for view in views if "transcriptSegmentViewModel" in view]
                if not transcript_views:
                    continue
                index = item["index"]
                if type(index) is not int or not 0 <= index < len(timings):
                    raise PanelProtocolError("Invalid transcript timing index")
                timing = timings[index]
                start, end = int(timing["videoTimeMs"]), int(timing["endTimeMs"])
                seek = item["onTap"]["innertubeCommand"]["watchEndpoint"]["startTimeSeconds"]
                if start < 0 or end < start or start // 1000 != int(seek):
                    raise PanelProtocolError("Transcript timing disagrees with seek command")
                text = "\n".join(view["simpleText"] for view in transcript_views)
                if not text.strip():
                    raise PanelProtocolError("Empty transcript text")
                segments.append({"start_ms": start, "end_ms": end, "text": text})
        if not segments:
            raise PanelProtocolError("Response has no transcript segments")
        return segments
    except (KeyError, TypeError, ValueError, IndexError) as error:
        if isinstance(error, PanelProtocolError):
            raise
        raise PanelProtocolError("Unexpected modern transcript response structure") from error


def fetch_panel(video_id, track_id=None, client_version=CLIENT_VERSION):
    """One anonymous request, without retry, browser bootstrap or caption URLs."""
    body = {
        "context": {"client": {
            "clientName": "WEB", "clientVersion": client_version,
            "hl": "en", "gl": "GB",
        }},
        "panelId": PANEL_ID,
        "params": encode_params(video_id, track_id),
    }
    response = requests.post(
        "https://www.youtube.com/youtubei/v1/get_panel?prettyPrint=false",
        json=body, timeout=20,
    )
    response.raise_for_status()
    return parse_panel(response.json(), expected_track=track_id)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video_id")
    parser.add_argument("--track", help="Observed caption vssId, for example .en, a.en or .ja")
    parser.add_argument("--client-version", default=CLIENT_VERSION)
    args = parser.parse_args()
    try:
        segments = fetch_panel(args.video_id, args.track, args.client_version)
        text = "\n".join(segment["text"] for segment in segments)
        print(json.dumps({
            "video_id": args.video_id, "requested_track": args.track,
            "endpoint": "get_panel", "status": 200, "segments": len(segments),
            "first_start_ms": segments[0]["start_ms"],
            "last_end_ms": segments[-1]["end_ms"],
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "cookies": False, "attestation": False,
        }, indent=2))
    except (requests.RequestException, ValueError) as error:
        # Do not print response bodies, session values or transcript text.
        print(json.dumps({
            "error": type(error).__name__,
            "reason": str(error) if isinstance(error, PanelProtocolError) else None,
            "status": getattr(getattr(error, "response", None), "status_code", None),
        }), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
