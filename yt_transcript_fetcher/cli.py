# PYTHON_ARGCOMPLETE_OK
import argparse

import argcomplete

from yt_transcript_fetcher import get_transcript, list_languages


def main():
    parser = argparse.ArgumentParser(
        prog="yt-transcript-fetcher", description="Download YouTube video transcripts."
    )

    # Add subcommands for listing languages and downloading transcripts
    command = parser.add_subparsers(
        title="subcommands",
        dest="command",
        help="Available commands",
        required=True,
        metavar="MODE",
    )
    langs = command.add_parser(
        "list-languages", help="List available transcript languages for a video."
    )
    langs.add_argument(
        "video_id",
        type=str,
        help="YouTube video ID to list available transcript languages for.",
    )
    download = command.add_parser(
        "download", help="Download the transcript for a video."
    )
    download.add_argument(
        "-l",
        "--language",
        type=str,
        required=True,
        help="Language code for the transcript to download (e.g., 'en' for English).",
    )
    download.add_argument(
        "video_id",
        type=str,
        help="YouTube video ID to fetch the transcript for.",
    )
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    if args.command == "list-languages":
        try:
            languages = list_languages(args.video_id)
            print(f"Available languages for video {args.video_id}:")
            for lang in languages:
                print(f"{lang.code}: {lang.display_name}")
        except Exception as e:
            print(f"Error listing languages: {e}")
    elif args.command == "download":
        try:
            transcript = get_transcript(args.video_id, args.language)
            print(f"Transcript for video {args.video_id} in language {args.language}:")
            print(transcript.text)
            for segment in transcript.segments:
                print(f"[{segment.start:.2f} - {segment.end:.2f}] {segment.text}")
        except Exception as e:
            print(f"Error downloading transcript: {e}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
# This script provides a command-line interface to download YouTube video transcripts.
