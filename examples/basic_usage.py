# Example usage of the yt_transcript package to fetch and display YouTube video transcripts.
from re import search
from yt_transcript_fetcher import get_transcript, list_languages


def main():
    video_id = "dQw4w9WgXcQ"  # Replace with your YouTube video ID
    language_code = "en"  # Replace with your desired language code

    try:
        # Fetch the transcript for the specified video and language
        transcript = get_transcript(video_id, language_code)
        print(f"Transcript for video {video_id} in language {language_code}:")

        # get the full text of the transcript
        print(transcript.text)

        # Print each segment of the transcript
        for segment in transcript.segments:
            print(f"[{segment.start:.2f} - {segment.end:.2f}] {segment.text}")

        # find specific languages available for the video
        languages = list_languages(video_id)
        print(f"Available languages for video {video_id}:")
        for lang in languages:
            print(f"{lang.code}: {lang.display_name}")

        # Get a specific language by code
        lang = languages.get_language_by_code(language_code)

        # Find a segment by start time (ms)
        time = 43.1 * 1000  # Convert seconds to milliseconds
        segment = transcript.get_segment_by_time(time)
        if segment:
            print(
                f"Segment at 4310ms: [{segment.start:.2f} - {segment.end:.2f}] {segment.text}"
            )
        else:
            print("No segment found at 4310ms.")

        # Find all segments containing a specific string
        search_text = "Never gonna give"
        segments_with_word = transcript.get_segments_by_text(search_text)
        if segments_with_word:
            print("Segments containing search_text:")
            for seg in segments_with_word:
                print(f"[{seg.start:.2f} - {seg.end:.2f}] {seg.text}")
        else:
            print("No segments found containing 'Never gonna give'.")

        # Find all segments in a time range
        start_time = 10 * 1000  # 10 seconds
        end_time = 20 * 1000  # 20 seconds
        segments_in_range = transcript.get_segments_by_time_range(start_time, end_time)
        if segments_in_range:
            print(f"Segments between {start_time}ms and {end_time}ms:")
            for seg in segments_in_range:
                print(f"[{seg.start:.2f} - {seg.end:.2f}] {seg.text}")
        else:
            print(f"No segments found between {start_time}ms and {end_time}ms.")

        # Find segments within a time range with a specific word
        word = "never"
        segments_with_word_in_range = transcript.get_segments_by_time_range(
            start_time, end_time
        ).get_segments_by_text(word)
        if segments_with_word_in_range:
            print(
                f"Segments containing '{word}' between {start_time}ms and {end_time}ms:"
            )
            for seg in segments_with_word_in_range:
                print(f"[{seg.start_ms:.2f} - {seg.end_ms:.2f}] {seg.text}")
        else:
            print(
                f"No segments found containing '{word}' between {start_time}ms and {end_time}ms."
            )

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
# Example usage of the yt_transcript package to fetch and display YouTube video transcripts.