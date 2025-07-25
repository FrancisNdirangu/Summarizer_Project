import time
import csv
import re
import sys
from typing import List
import pandas as pd
from statistics import mean

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

# Define fallback for old versions
class TooManyRequests(Exception):
    pass

INPUT_CSV = "youtube_video_list.csv"
OUTPUT_CSV = "youtube_transcripts.csv"
MAX_WORDS = 1200
LANGS = ["en"]

SLEEP_BETWEEN_CALLS = 0.3
RETRIES = 3
BACKOFF = 2.0

FILLER_WORDS = set([
    "um", "uh", "you know", "like", "i mean", "sort of", "kind of",
    "actually", "basically", "literally", "right", "okay", "so", "well"
])

STOP_WORDS = set([
    'the', 'and', 'is', 'in', 'it', 'you', 'that', 'he', 'was', 'for', 'on', 'are',
    'with', 'as', 'i', 'his', 'they', 'be', 'at', 'one', 'have', 'this', 'from', 'or'
])


def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[\n\r]+", " ", text)
    text = re.sub(r"[^a-z0-9.,!?;:'\"\\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    for filler in FILLER_WORDS:
        text = re.sub(rf"\b{re.escape(filler)}\b", "", text)
    return text.strip()


def quality_metrics(text: str, duration_sec: float) -> dict:
    words = text.split()
    sentences = re.split(r'[.!?]', text)
    words_per_min = len(words) / (duration_sec / 60.0) if duration_sec else 0
    avg_sent_len = mean([len(s.split()) for s in sentences if s.strip()]) if sentences else 0
    stopword_ratio = len([w for w in words if w in STOP_WORDS]) / len(words) if words else 0
    return {
        "word_count": len(words),
        "wpm": round(words_per_min, 2),
        "avg_sentence_len": round(avg_sent_len, 2),
        "stopword_ratio": round(stopword_ratio, 2)
    }


def fetch_transcript_compat(video_id: str, langs: List[str]) -> List[dict]:
    transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
    try:
        return transcripts.find_transcript(langs).fetch()
    except Exception:
        for t in transcripts:
            try:
                return t.translate(langs[0]).fetch()
            except Exception:
                continue
        raise NoTranscriptFound(video_id=video_id, requested_language_codes=langs, transcript_data=[])




def get_transcript_with_retry(video_id: str, langs: List[str]):
    delay = SLEEP_BETWEEN_CALLS
    for attempt in range(1, RETRIES + 1):
        try:
            return fetch_transcript_compat(video_id, langs)
        except TooManyRequests:
            if attempt == RETRIES:
                raise
            time.sleep(delay)
            delay *= BACKOFF
        except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
            raise
        except Exception:
            if attempt == RETRIES:
                raise
            time.sleep(delay)
            delay *= BACKOFF


def main():
    try:
        df = pd.read_csv(INPUT_CSV)
    except FileNotFoundError:
        print(f"Missing {INPUT_CSV}. Run video list generator first.", file=sys.stderr)
        sys.exit(1)

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["author", "title", "transcript"])

        for i, row in df.iterrows():
            vid = str(row["video_id"])
            title = str(row["title"])
            author = str(row["channel_name"])

            try:
                tx = get_transcript_with_retry(vid, LANGS)
                full_text = " ".join(chunk["text"] for chunk in tx if chunk["text"].strip())
                clean = clean_text(full_text)
                duration = tx[-1]['start'] + tx[-1].get('duration', 0)
                metrics = quality_metrics(clean, duration)

                if metrics["word_count"] <= MAX_WORDS:
                    writer.writerow([author, title, clean])
                    print(f"✅ {i+1}/{len(df)} saved {vid} {metrics}")
                else:
                    print(f"⏭️ {i+1}/{len(df)} too long ({metrics['word_count']} words)")

            except (TranscriptsDisabled, NoTranscriptFound) as e:
                print(f"❌ {i+1}/{len(df)} no transcript {vid}: {e.__class__.__name__}")
            except Exception as e:
                print(f"⚠️ {i+1}/{len(df)} error {vid}: {e}")

            time.sleep(SLEEP_BETWEEN_CALLS)

    print(f"\nDone. Transcripts saved to {OUTPUT_CSV}.")
    # print(f"\n✅ Done. {success_count} saved. {error_count} skipped.")



if __name__ == "__main__":
    main()
