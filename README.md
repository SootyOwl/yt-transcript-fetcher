[![Run Tests](https://github.com/SootyOwl/yt-transcript-fetcher/actions/workflows/run-tests.yml/badge.svg)](https://github.com/SootyOwl/yt-transcript-fetcher/actions/workflows/run-tests.yml)


# yt-transcript-fetcher

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
yt-transcript-fetcher <video_id> --list-languages
```

This will list all available languages for the specified video ID.

```bash
yt-transcript-fetcher <video_id> --download <language_code>
```

This will download the transcript for the specified video ID in the given language code and output it to standard output.

### Python API

You can also use the package as a Python module. Here is a basic example:

```python
from yt_transcript_fetcher import list_languages, get_transcript
video_id = "dQw4w9WgXcQ"  # Replace with your video ID
languages = list_languages(video_id)
print("Available languages:", languages)
transcript = get_transcript(video_id, language_code="en")
print("Transcript:", transcript)
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)
