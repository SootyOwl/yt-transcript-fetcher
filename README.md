# yt-transcript-fetcher | YouTube Transcript Fetcher

[![Run Tests](https://github.com/SootyOwl/yt-transcript-fetcher/actions/workflows/run-tests.yml/badge.svg)](https://github.com/SootyOwl/yt-transcript-fetcher/actions/workflows/run-tests.yml)
[![PyPI - Version](https://img.shields.io/pypi/v/yt-transcript-fetcher)](https://pypi.org/project/yt-transcript-fetcher/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/yt-transcript-fetcher)
![PyPI - License](https://img.shields.io/pypi/l/yt-transcript-fetcher)
![PyPI - Downloads](https://img.shields.io/pypi/dm/yt-transcript-fetcher)

A python package to fetch YouTube video transcripts.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install yt-transcript-fetcher.

```bash
pip install yt-transcript-fetcher
```

## Usage

Basic usage examples can be found in the [examples](https://github.com/SootyOwl/yt-transcript-fetcher/tree/main/examples) directory.

### Command Line Interface (CLI)
The package includes a basic command line interface for fetching transcripts. You can run the following command:

```bash
yt-transcript-fetcher list-languages <video_id>
```

This will list all available languages for the specified video ID.

```bash
yt-transcript-fetcher download -l <language_code> <video_id>
```

This will download the transcript for the specified video ID in the given language code and output it to standard output.

### Python API

You can also use the package as a Python module. Here is a basic example:

```python
from yt_transcript_fetcher import list_languages, get_transcript
video_id = "dQw4w9WgXcQ"  # Replace with your video ID
languages = list_languages(video_id)
print("Available languages:", languages)
transcript = get_transcript(video_id, language="en")
print(transcript.text)
for segment in transcript.segments:
    print(segment.start_ms, segment.end_ms, segment.text)
```

### Backend and compatibility

The package discovers caption languages through YouTube's internal `player`
endpoint and fetches transcript text through `get_panel` using protobuf
parameters. It needs only Python and the existing package dependencies: no
browser, JavaScript helper, cookies, API key, or caption-URL download.

The public functions, `YouTubeTranscriptFetcher(session=None)`, model
constructors, timing helpers, and CLI commands remain unchanged. Existing
legacy response parsers and protobuf helpers remain available. A fetcher caches
language discovery per video and respects caller-supplied sessions. If multiple
tracks share a language code, the first matching track retains precedence.

YouTube's modern panel groups text differently, so segment counts, text
grouping, and timing boundaries can differ from older transcripts. Times remain
in milliseconds on `start_ms`/`end_ms`, and seconds on `start`/`end`. The parser
checks the returned video and caption track and rejects incomplete or malformed
timing data instead of returning an incorrectly labelled transcript.

This fix preserves the previous exception and retry behavior. Language discovery
still maps HTTP failures to `VideoNotFoundError`, except JSON
`FAILED_PRECONDITION` errors, which raise `YouTubeAPIError`. Transcript HTTP
failures propagate as `requests.HTTPError`. Default sessions retain retries for
HTTP 400, HTTP 429 and transient server failures, respecting `Retry-After`.
Invalid modern panel selection or timing data raises `YouTubeAPIError` from
`yt_transcript_fetcher.exceptions`. Revised transport exceptions and removal of
HTTP 400 retries are reserved for a separate breaking release.

This uses an undocumented API and may need updates as YouTube changes. Successful
requests do not establish the rate limit on a Discord bot's hosting network;
cache transcripts and bound concurrency in the application. The protocol and
verification evidence are recorded in [research/README.md](research/README.md).

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)
