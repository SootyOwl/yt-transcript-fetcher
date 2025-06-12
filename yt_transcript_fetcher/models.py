"""This module defines the data models for YouTube transcript processing."""

from dataclasses import dataclass

from yt_transcript_fetcher.exceptions import NoLanguageError, NoSegmentsError
from yt_transcript_fetcher.protobuf import get_video_id, is_asr_captions, retrieve_language_code


def safe_get(data, path, default=None):
    """Get nested dict value using 'key.0.subkey' notation"""
    try:
        for key in path.split("."):
            if key.isdigit():
                data = data[int(key)]
            else:
                data = data[key]
        return data
    except (KeyError, IndexError, TypeError):
        return default


@dataclass
class Language:
    """Represents a language available for YouTube transcripts."""

    code: str
    """The ISO 639-1 code of the language."""
    display_name: str
    """The name of the language."""
    is_auto_generated: bool = False
    """Indicates if the transcript is auto-generated (ASR)."""
    _continuation_token: str = None
    """Can be used to fetch the transcript in this language."""

    def __str__(self):
        return f"{self.display_name} ({self.code})"

    def __post_init__(self):
        if not self.code or not self.display_name:
            raise ValueError("Language code and display name cannot be empty.")
        if not isinstance(self.is_auto_generated, bool):
            raise ValueError("is_auto_generated must be a boolean value.")
        if self._continuation_token is None:
            raise ValueError("continuation_token cannot be None.")


@dataclass
class LanguageList:
    """Represents a list of languages available for YouTube transcripts."""

    languages: list[Language]

    def __post_init__(self):
        if not self.languages:
            raise NoLanguageError

    def __str__(self):
        return ", ".join(str(lang) for lang in self.languages)

    def __iter__(self):
        """Iterate over the languages in the list."""
        return iter(self.languages)

    def __len__(self):
        """Get the number of languages in the list."""
        return len(self.languages)

    def __getitem__(self, index):
        """Get a language by index."""
        return self.languages[index]

    def __contains__(self, lang: Language | str):
        """Check if a language is in the list."""
        if isinstance(lang, str):
            return any(language.code == lang for language in self.languages)
        if isinstance(lang, Language):
            return lang in self.languages

    def __eq__(self, other):
        """Check if two LanguageList objects are equal."""
        if not isinstance(other, LanguageList):
            return False
        return sorted(self.languages, key=lambda x: x.code) == sorted(
            other.languages, key=lambda x: x.code
        )

    def get_language_by_code(self, code: str) -> Language:
        """Retrieve a language by its code."""
        for lang in self.languages:
            if lang.code == code:
                return lang
        return None

    @classmethod
    def from_response(cls, response_data):
        """Create a LanguageList from a response dictionary."""
        # languages are at the following path in the response:
        # response_data['actions.0.updateEngagementPanelAction.content.transcriptRenderer.footer.transcriptFooterRenderer.languageMenu.sortFilterSubMenuRenderer.subMenuItems']
        languages = []
        for item in response_data.get("actions", []):
            if "updateEngagementPanelAction" in item:
                sub_menu = safe_get(
                    item,
                    "updateEngagementPanelAction.content.transcriptRenderer.content.transcriptSearchPanelRenderer.footer.transcriptFooterRenderer.languageMenu.sortFilterSubMenuRenderer.subMenuItems",
                    [],
                )
                if not sub_menu:
                    continue
                for lang_item in sub_menu:
                    name = lang_item.get("title", "")
                    continuation_token = (
                        lang_item.get("continuation", {})
                        .get("reloadContinuationData", {})
                        .get("continuation", "")
                    )
                    language_code = retrieve_language_code(continuation_token)
                    is_auto_generated = is_asr_captions(continuation_token)
                    if language_code:
                        languages.append(
                            Language(
                                code=language_code,
                                display_name=name,
                                is_auto_generated=is_auto_generated,
                                _continuation_token=continuation_token,
                            )
                        )
        return cls(languages=languages)


@dataclass
class Segment:
    """Represents a segment of a YouTube video transcript.

    Dict version from response:
    {
        "transcriptSegmentRenderer": {
            "startMs": "120",
            "endMs": "2520",
            "snippet": {
                "runs": [
                    {
                        "text": "hallo da bin ich wieder was haben Helene"
                    }
                ]
            },
            "startTimeText": {
                "simpleText": "0: 00"
            },
            "trackingParams": "CKYDENP2BxgAIhMIrNSdwOPmjQMVwTp7BB3VbxIH",
            "accessibility": {
                "accessibilityData": {
                    "label": "0 seconds hallo da bin ich wieder was haben Helene"
                }
            },
            "targetId": "rnCVlVSE5pI.CgNhc3ISAmRlGgA%3D.120.2520"
        }
    }"""

    start_ms: int
    """Start time of the segment in milliseconds."""
    end_ms: int
    """End time of the segment in milliseconds."""
    text: str
    """Text content of the segment."""
    start_time_text: str = None
    """Formatted start time as a string (e.g., '0:00')."""
    accessibility_label: str = None
    """Accessibility label for screen readers."""

    def __post_init__(self):
        if self.start_ms < 0 or self.end_ms <= self.start_ms:
            raise ValueError("Invalid segment time range.")
        if not self.text:
            raise ValueError("Segment text cannot be empty.")

    def __str__(self):
        return f"[{self.start_time_text}] {self.text}"
    
    @property
    def start(self):
        """The start time of the segment in seconds."""
        return self.start_ms / 1000.0
    
    @property
    def end(self):
        """The end time of the segment in seconds."""
        return self.end_ms / 1000.0

    @classmethod
    def from_dict(cls, segment_dict):
        """Create a Segment from a dictionary."""
        start_ms = segment_dict.get("startMs", "0")
        end_ms = segment_dict.get("endMs", "0")
        snippet = segment_dict.get("snippet", {})
        runs = snippet.get("runs", [])
        text = " ".join(run.get("text", "") for run in runs if "text" in run)
        start_time_text = segment_dict.get("startTimeText", {}).get("simpleText", "")
        accessibility = segment_dict.get("accessibility", {})
        accessibility_label = accessibility.get("accessibilityData", {}).get(
            "label", ""
        )
        try:
            start_ms = int(start_ms)
            end_ms = int(end_ms)
        except ValueError:
            raise ValueError("Start and end times must be integers.")
        return cls(
            start_ms=start_ms,
            end_ms=end_ms,
            text=text,
            start_time_text=start_time_text,
            accessibility_label=accessibility_label,
        )


@dataclass
class SegmentList:
    """Represents a list of segments in a YouTube video transcript."""

    segments: list[Segment]

    def __post_init__(self):
        for segment in self.segments:
            if not isinstance(segment, Segment):
                raise ValueError("Each segment must be an instance of Segment.")

    def __str__(self):
        return f"SegmentList with {len(self.segments)} segments."

    def __iter__(self):
        """Iterate over the segments in the list."""
        return iter(self.segments)

    def __len__(self):
        """Get the number of segments in the list."""
        return len(self.segments)

    def __getitem__(self, index):
        """Get a segment by index."""
        return self.segments[index]

    def __contains__(self, segment: Segment):
        """Check if a segment is in the list."""
        return segment in self.segments

    def __eq__(self, other):
        """Check if two SegmentList objects are equal."""
        if not isinstance(other, SegmentList):
            return False
        return sorted(self.segments, key=lambda x: x.start_ms) == sorted(
            other.segments, key=lambda x: x.start_ms
        )

    def __bool__(self):
        """Check if the SegmentList is not empty."""
        return bool(self.segments)

    @property
    def start_time(self):
        """Get the start time of the transcript in milliseconds."""
        return self.segments[0].start_ms if self.segments else 0

    @property
    def end_time(self):
        """Get the end time of the transcript in milliseconds."""
        return self.segments[-1].end_ms if self.segments else 0

    @classmethod
    def from_response(cls, response_data):
        initial_transcript_parts = safe_get(
            response_data,
            "actions.0.updateEngagementPanelAction.content.transcriptRenderer.content.transcriptSearchPanelRenderer.body.transcriptSegmentListRenderer.initialSegments",
            [],
        )
        if not initial_transcript_parts:
            raise NoSegmentsError("No transcript segments found in the response data.")
        segments = []
        for segment_dict in initial_transcript_parts:
            segment = Segment.from_dict(
                segment_dict.get("transcriptSegmentRenderer", {})
            )
            segments.append(segment)
        return cls(segments=segments)

    def get_segment_by_time(self, time_ms):
        """Get the segment that contains the specified time in milliseconds."""
        return next(
            (
                segment
                for segment in self.segments
                if segment.start_ms <= time_ms < segment.end_ms
            ),
            None,
        )

    def get_segments_by_text(self, text) -> "SegmentList":
        """Get all segments that contain the specified text.

        Args:
            text (str): The text to search for in the segments.
        Returns:
            SegmentList: A list of segments that contain the specified text.
        """
        return SegmentList(
            [
                segment
                for segment in self.segments
                if text.lower() in segment.text.lower()
            ]
        )

    def get_segments_by_time_range(self, start_ms: int, end_ms: int) -> "SegmentList":
        """Get all segments that overlap with the specified time range.

        Inclusive of start_ms and exclusive of end_ms.
        Args:
            start_ms (int): Start time in milliseconds.
            end_ms (int): End time in milliseconds.
        Returns:
            SegmentList: A list of segments that overlap with the specified time range.
        Raises:
            ValueError: If start_ms is not less than end_ms, or if times are negative.
        """
        if start_ms >= end_ms:
            raise ValueError("Start time must be less than end time.")
        if not self.segments:
            return []
        if start_ms < 0 or end_ms < 0:
            raise ValueError("Start and end times must be non-negative.")
        if start_ms >= self.end_time or end_ms <= self.start_time:
            return []

        return SegmentList(
            segments=[
                segment
                for segment in self.segments
                if not (segment.end_ms <= start_ms or segment.start_ms >= end_ms)
            ]
        )


@dataclass
class Transcript:
    """Represents a YouTube video transcript."""

    video_id: str
    """The ID of the YouTube video."""
    language: Language
    """The language of the transcript, represented by a Language object."""
    segments: SegmentList
    """A list of timed entries in the transcript."""

    def __post_init__(self):
        if not self.segments:
            raise NoSegmentsError("Transcript must contain at least one segment.")
        for segment in self.segments:
            if not isinstance(segment, Segment):
                raise ValueError("Each segment must be an instance of Segment.")

    def __str__(self):
        return (
            f"Transcript for video {self.video_id} with {len(self.segments)} segments."
        )

    @property
    def text(self):
        """Get the full text of the transcript as a single string."""
        return "\n".join(segment.text for segment in self.segments)

    @property
    def start_time(self):
        """Get the start time of the transcript in milliseconds."""
        return self.segments[0].start_ms if self.segments else 0

    @property
    def end_time(self):
        """Get the end time of the transcript in milliseconds."""
        return self.segments[-1].end_ms if self.segments else 0

    @property
    def duration(self):
        """Get the duration of the transcript in milliseconds."""
        return self.end_time - self.start_time

    @property
    def language_code(self):
        """Get the ISO 639-1 code of the transcript language."""
        return self.language.code

    def get_segment_by_time(self, time_ms):
        """Get the segment that contains the specified time in milliseconds."""
        return self.segments.get_segment_by_time(time_ms)

    def get_segments_by_text(self, text):
        """Get all segments that contain the specified text."""
        return self.segments.get_segments_by_text(text)

    def get_segments_by_time_range(self, start_ms, end_ms):
        """Get all segments that overlap with the specified time range.

        Inclusive of start_ms and exclusive of end_ms.
        Raises:
            ValueError: If start_ms is not less than end_ms, or if times are negative.
        """
        return self.segments.get_segments_by_time_range(start_ms, end_ms)

    @classmethod
    def from_response(cls, language: Language, response_data: dict):
        """Create a Transcript from a response dictionary."""
        return cls(
            video_id=get_video_id(language._continuation_token),
            language=language,
            segments=SegmentList.from_response(response_data),
        )
