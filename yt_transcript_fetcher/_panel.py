"""Private codec and parser for YouTube's modern transcript panel."""

import base64
import re
from urllib.parse import quote, unquote

from .exceptions import NoSegmentsError, YouTubeAPIError

PANEL_ID = "PAmodern_transcript_view"


def _varint(value):
    result = bytearray()
    while value > 127:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return bytes(result)


def _field(number, value):
    return _varint((number << 3) | 2) + _varint(len(value)) + value


def encode_params(video_id, track_id=None):
    """Encode the observed panel message, including an optional exact vssId."""
    if not isinstance(video_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("Expected an 11-character YouTube video ID.")
    message = _field(1, video_id.encode("ascii")) + b"\x18\x02"
    if track_id is not None:
        message += _field(6, track_id.encode("utf-8"))
    return quote(base64.b64encode(_field(149, message)).decode("ascii"))


def _message(data):
    if not isinstance(data, bytes):
        raise ValueError("Expected a protobuf message")
    offset = 0

    def read_varint():
        nonlocal offset
        value = 0
        for shift in range(0, 70, 7):
            if offset >= len(data):
                break
            byte = data[offset]
            offset += 1
            if shift == 63 and byte > 1:
                break
            value |= (byte & 127) << shift
            if byte < 128:
                return value
        raise ValueError("Invalid protobuf varint")

    fields = {}
    while offset < len(data):
        tag = read_varint()
        number, wire = tag >> 3, tag & 7
        if not 0 < number < (1 << 29) or number in fields:
            raise ValueError("Invalid or repeated protobuf field")
        if wire == 0:
            value = read_varint()
        elif wire in (1, 2, 5):
            length = read_varint() if wire == 2 else (8 if wire == 1 else 4)
            if length > len(data) - offset:
                raise ValueError("Truncated protobuf field")
            value = data[offset:offset + length]
            offset += length
        else:
            raise ValueError("Unsupported protobuf wire type")
        fields[number] = value
    return fields


def _decode(value):
    value = unquote(value)
    return base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)


def selection(response):
    """Read the server-selected video and track; absent track means default."""
    try:
        section_list = response["content"]["engagementPanelSectionListRenderer"]["content"]["sectionListRenderer"]
        command = section_list["header"]["searchInputViewModel"]["onInputAction"]["command"]["innertubeCommand"]["continuationCommand"]
        if command["request"] != "CONTINUATION_REQUEST_TYPE_GET_PANEL":
            raise ValueError("Unexpected continuation route")
        continuation = _message(_message(_decode(command["token"]))[377091426])
        if continuation[2].decode("utf-8") != PANEL_ID:
            raise ValueError("Unexpected panel")
        params = _message(_message(_decode(continuation[3].decode("ascii")))[149])
        video_id = params[1].decode("ascii")
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            raise ValueError("Invalid selected video")
        track = params.get(6, b"").decode("utf-8") or None
        return video_id, track
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise YouTubeAPIError("Unable to verify the modern transcript selection.") from error


def _integer(value):
    # Reject booleans, floats and negative indices instead of coercing them.
    if type(value) is int and value >= 0:
        return value
    if isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
        return int(value)
    raise ValueError("Expected a nonnegative integer")


def segments(response):
    """Normalize views using global timing indices, including chapter slots."""
    try:
        panel = response["content"]["engagementPanelSectionListRenderer"]
        section_list = panel["content"]["sectionListRenderer"]
        if not section_list["contents"]:
            raise NoSegmentsError()
        references = {
            command["updateTimedMarkersSyncObserverCommand"]["timedSyncEntityKey"]
            for command in panel["onShowCommands"]
            if "updateTimedMarkersSyncObserverCommand" in command
        }
        if len(references) != 1:
            raise ValueError("Ambiguous timing reference")
        entities = [
            mutation["payload"]["timedMarkersListSyncEntity"]
            for mutation in response["frameworkUpdates"]["entityBatchUpdate"]["mutations"]
            if mutation.get("payload", {}).get("timedMarkersListSyncEntity", {}).get("key") in references
        ]
        if len(entities) != 1:
            raise ValueError("Missing or ambiguous timing entity")
        timings = [
            timing
            for section in entities[0]["timedListData"]["sections"]
            for timing in section["timedSyncDataList"]
        ]
        result, seen = [], set()
        previous_index = -1
        for section in section_list["contents"]:
            for wrapper in section["itemSectionRenderer"].get("contents", []):
                if "macroMarkersPanelItemViewModel" not in wrapper:
                    raise ValueError("Unknown transcript item")
                item = wrapper["macroMarkersPanelItemViewModel"]
                views = item["item"]["timelineItemViewModel"]["contentItems"]
                parts = [view["transcriptSegmentViewModel"] for view in views if "transcriptSegmentViewModel" in view]
                if not parts or len(parts) != len(views):
                    raise ValueError("Unknown transcript content")
                index = _integer(item["index"])
                if index >= len(timings) or index <= previous_index:
                    raise ValueError("Invalid or unordered timing index")
                previous_index = index
                seen.add(index)
                timing = timings[index]
                start, end = _integer(timing["videoTimeMs"]), _integer(timing["endTimeMs"])
                seek = _integer(item["onTap"]["innertubeCommand"]["watchEndpoint"]["startTimeSeconds"])
                if end < start or start // 1000 != seek:
                    raise ValueError("Invalid transcript timing")
                text = "\n".join(part["simpleText"] for part in parts)
                if not text.strip():
                    raise ValueError("Empty transcript text")
                result.append({
                    "start_ms": start, "end_ms": end, "text": text,
                    "start_time_text": parts[0].get("timestamp", ""),
                    "accessibility_label": parts[0].get("accessibilityHint", ""),
                })
        if not result:
            raise NoSegmentsError()
        # Chapter headings have no endTimeMs; every timed caption must have a view.
        if seen != {index for index, timing in enumerate(timings) if "endTimeMs" in timing}:
            raise ValueError("Incomplete transcript panel")
        return result
    except (KeyError, TypeError, ValueError, AttributeError, IndexError) as error:
        raise YouTubeAPIError("Invalid modern transcript response or timing data.") from error
