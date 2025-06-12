# basic CLI for downloading YouTube transcripts
import argparse

from yt_transcript_fetcher import get_transcript, list_languages

def main():
    parser = argparse.ArgumentParser(description="Download YouTube video transcripts.")
    
    # list or download
    parser.add_argument(
        "video_id", type=str, help="YouTube video ID to fetch the transcript for."
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    # List all available languages
    mode.add_argument(
        "--list-languages", "-l",
        dest="list_languages",
        action="store_true",
        help="List all available languages for the specified video.",
    )
    # Download transcript in a specific language
    mode.add_argument(
        "--download", "-d",
        dest="download",
        nargs="?",  # Optional argument, if not provided, defaults to 'en'
        const="en",  # Use const instead of default for nargs="?"
        metavar="LANGUAGE",
        type=str,
        help="Download the transcript in the specified language (e.g., 'en', 'fr').",
    )
    args = parser.parse_args()
    if args.list_languages:
        try:
            languages = list_languages(args.video_id)
            print(f"Available languages for video {args.video_id}:")
            for lang in languages:
                print(f"{lang.code}: {lang.display_name}")
        except Exception as e:
            print(f"Error listing languages: {e}")
    elif args.download:
        try:
            transcript = get_transcript(args.video_id, args.download)
            print(f"Transcript for video {args.video_id} in language {args.download}:")
            print(transcript.text)
            for segment in transcript.segments:
                print(f"[{segment.start:.2f} - {segment.end:.2f}] {segment.text}")
        except Exception as e:
            print(f"Error downloading transcript: {e}")

if __name__ == "__main__":
    main()
# This script provides a command-line interface to download YouTube video transcripts.