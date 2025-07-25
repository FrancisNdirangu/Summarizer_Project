import sys, os
import youtube_transcript_api as yta
from youtube_transcript_api import YouTubeTranscriptApi as Y

print("📦 Module path:", yta.__file__)
print("✅ Has get_transcript:", hasattr(Y, "get_transcript"))
print("📋 Transcript-related methods:", [m for m in dir(Y) if "transcript" in m.lower()])
