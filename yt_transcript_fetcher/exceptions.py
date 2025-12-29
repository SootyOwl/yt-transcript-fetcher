class NoSegmentsError(Exception):
    """Exception raised when no segments are found in the transcript."""

    def __init__(self, message="No segments found in the transcript."):
        self.message = message
        super().__init__(self.message)


class NoTranscriptError(Exception):
    """Exception raised when no transcript is available for the video."""

    def __init__(self, message="No transcript available for the video."):
        self.message = message
        super().__init__(self.message)


class NoLanguageError(Exception):
    """Exception raised when no language is available for the video."""

    def __init__(self, message="No language available for the video."):
        self.message = message
        super().__init__(self.message)

class YouTubeAPIError(Exception):
    """Exception raised for errors returned by the YouTube API."""

    def __init__(self, message="An error occurred with the YouTube API."):
        self.message = message
        super().__init__(self.message)

class VideoNotFoundError(Exception):
    """Exception raised when a YouTube video is not found."""

    def __init__(self, message="The requested YouTube video was not found."):
        self.message = message
        super().__init__(self.message)

class InvalidLanguageCodeError(Exception):
    """Exception raised when an invalid language code is provided."""

    def __init__(self, message="Invalid language code provided."):
        self.message = message
        super().__init__(self.message)