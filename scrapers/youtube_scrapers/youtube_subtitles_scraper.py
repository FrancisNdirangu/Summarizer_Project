"""
youtube_subtitles_scraper.py
==============================

This script demonstrates how to collect subtitles (closed captions) from
YouTube videos for use as training data in natural‑language processing tasks.

The scraper uses the open source `youtube_transcript_api` package to fetch
transcripts for individual YouTube videos.  For videos that do not provide
manual captions, YouTube often generates auto‑captions via automatic speech
recognition (ASR).  Auto‑captions can be a convenient way to obtain text for
video content, but they frequently contain errors.  According to a 2023
industry report, even the most accurate ASR solutions reach only about
93 % accuracy on well‑recorded content, and accuracy can drop as low as
57.5 % when audio quality is poor【976534291370789†L116-L146】.  For high‑quality
training data you may want to prefer channels that provide manually edited
subtitles or perform post‑processing on auto‑generated transcripts.

The script accepts a list of YouTube video identifiers (the 11‑character
codes that follow ``v=`` in YouTube URLs) and attempts to download the
English transcript for each.  It concatenates the individual caption
segments into a single string, computes a word count, and writes the
results to a CSV file.  Videos whose transcripts exceed the configured
``MAX_WORDS`` threshold are skipped.  You can adjust this limit to suit
your downstream use case (for example, training an abstractive summarizer
with a maximum input length).

To use this script you must install `youtube_transcript_api` (see
https://github.com/jdepoix/youtube-transcript-api).  The package does not
require a YouTube API key and works for both manual and auto‑generated
captions【675069861163593†L150-L165】.  Installation requires internet access; on
an offline system you should install the package in advance or copy it
into your environment manually.

Example usage:

    python youtube_subtitles_scraper.py \
        --video-ids video_ids.txt \
        --output-file youtube_subtitles.csv \
        --max-words 1200

The `video_ids.txt` file should contain one YouTube video ID per line.

If you do not have a list of video IDs, you can generate one using the
YouTube Data API or other tools such as `yt‑dlp` search, but these
approaches require an API key or additional software that is not included
in this repository.
"""

import argparse
import csv
import os
import sys
from typing import List, Optional

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError as exc:
    print(
        "youtube_transcript_api is required but not installed. "
        "Install it via pip (pip install youtube-transcript-api) before running this script.",
        file=sys.stderr,
    )
    raise


def read_video_ids(path: str) -> List[str]:
    """
    Read a list of YouTube video IDs from a text file.  Blank lines and
    comments (lines starting with '#') are ignored.
    """
    ids: List[str] = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Extract video ID from a full YouTube URL if provided
            if "youtube.com" in line:
                # ID is the value after v=
                parts = line.split('v=')
                if len(parts) > 1:
                    vid = parts[1].split('&')[0]
                    ids.append(vid)
                continue
            ids.append(line)
    return ids


def fetch_transcript(video_id: str, languages: Optional[List[str]] = None) -> Optional[str]:
    """
    Fetch the transcript for a single YouTube video.  If multiple languages are
    provided, the API will attempt them in order until a transcript is found.

    :param video_id: YouTube video identifier (the 11‑character code)
    :param languages: Optional list of language codes (e.g., ['en', 'en-US']).
    :return: Transcript text as a single space‑separated string, or None if
             no transcript is available.
    """
    try:
        if languages:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            # Find the first transcript that matches one of the desired languages
            for trans in transcript_list:
                if trans.language_code in languages:
                    fetched = trans.fetch()
                    break
            else:
                # Fallback: just fetch the first available transcript
                fetched = transcript_list.find_transcript([languages[0]]).fetch()
        else:
            fetched = YouTubeTranscriptApi.get_transcript(video_id)
    except Exception as e:
        # Transcript not available or other error
        return None
    # Combine the text segments into one string
    texts = [snippet['text'].replace('\n', ' ') for snippet in fetched]
    return ' '.join(texts)


def word_count(text: str) -> int:
    """Return the number of words in a string."""
    return len([w for w in text.split() if w])


def main(video_ids_file: str, output_file: str, max_words: int, languages: Optional[List[str]] = None) -> None:
    # Read video IDs
    video_ids = read_video_ids(video_ids_file)
    if not video_ids:
        print(f"No video IDs found in {video_ids_file}.")
        return

    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['video_id', 'word_count', 'transcript'])
        count = 0
        for vid in video_ids:
            # Stop after collecting the desired number of transcripts
            if count >= 200:
                break
            text = fetch_transcript(vid, languages)
            if not text:
                continue
            wc = word_count(text)
            if wc > max_words:
                continue
            writer.writerow([vid, wc, text])
            count += 1
            print(f"Collected transcript for video {vid} ({wc} words)")

    print(f"Finished. Collected {count} transcripts under {max_words} words.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Scrape YouTube subtitles using youtube-transcript-api.")
    parser.add_argument('--video-ids', dest='video_ids', required=True,
                        help='Path to a text file containing YouTube video IDs or URLs (one per line).')
    parser.add_argument('--output-file', dest='output_file', required=True,
                        help='Path to output CSV file.')
    parser.add_argument('--max-words', dest='max_words', type=int, default=1200,
                        help='Maximum number of words allowed in a transcript (default: 1200).')
    parser.add_argument('--languages', dest='languages', nargs='*', default=['en'],
                        help='Desired transcript languages in order of priority (default: en).')
    args = parser.parse_args()
    main(args.video_ids, args.output_file, args.max_words, args.languages)