"""
youtube_video_list_generator.py
--------------------------------

This script generates a CSV file containing a list of YouTube video IDs
and their titles for a set of AI/ML/Data‑Science focused channels.  It
uses YouTube's RSS feeds, which are publicly accessible for each
channel.  Because YouTube only returns the most recent ~15 videos per
feed, the script iterates through a list of channels and collects a
subset of videos from each until it accumulates the desired number of
entries (500 by default).

The resulting CSV has two columns:

    channel_name, video_id

The list of channels is defined in the `CHANNELS` dictionary below.  To
add or remove channels, edit this dictionary accordingly.  Each entry
contains a channel identifier (either a `channel_id` or a `user`
slug) and a human‑readable name.

Requirements:
    - Python 3
    - requests (pip install requests)
    - xmltodict (pip install xmltodict) or use the built‑in xml.etree

Note:
    This script is meant to be executed in an environment with
    unrestricted network access.  The current Jupyter environment
    restricts outbound HTTP requests to youtube.com, so it may not run
    here.  Run it locally or in a network‑enabled environment.
"""

import csv
import time
from typing import Dict, List, Tuple

import requests
import xml.etree.ElementTree as ET

# List of AI/ML/Data‑Science YouTube channels.  Each entry maps a
# channel name to a dictionary specifying either a `channel_id` or a
# `user` slug.  The script will build the correct RSS feed URL from
# these values.  Feel free to add more channels to this list.  Each
# channel contributes up to `MAX_PER_CHANNEL` videos to the final list.
CHANNELS: Dict[str, Dict[str, str]] = {
    # format: 'Human‑Readable Name': {'channel_id': 'UC…'} or {'user': 'username'}
    '3Blue1Brown': {'channel_id': 'UCYO_jab_esuFRV4b17AJtAw'},
    'Data School': {'user': 'dataschool'},
    'freeCodeCamp.org': {'channel_id': 'UC8butISFwT-Wl7EV0hUK0BQ'},
    'sentdex': {'channel_id': 'UCfzlCWGWYyIQ0aLC5w48gBQ'},
    'Two Minute Papers': {'channel_id': 'UCbfYPyITQ-7l4upoX8nvctg'},
    'StatQuest': {'user': 'joshstarmer'},
    'Lex Fridman Podcast': {'channel_id': 'UCSHZKyawb77ixDdsGog4iWA'},
    'Codebasics (Krish Naik)': {'channel_id': 'UCh9nVJoWXmFb7sLApWGcLPQ'},
    'Data Science Dojo': {'user': 'DataScienceDojo'},
    'Ken Jee': {'channel_id': 'UCiT9RITQ9PW6BhXK0y2jaeg'},
    'Krish Naik': {'channel_id': 'UCNU_lfiiWBdtULKOw6X0Dig'},
    'Simplilearn': {'channel_id': 'UCBIMLnI8ijEwHhA0L_sITQQ'},
    'edureka!': {'channel_id': 'UCkw4JCwteGrDHIsyIIKo4tQ'},
    'Data Professor': {'channel_id': 'UCV8e2g4IWQqK71bbzGDEI4Q'},
    'Python Engineer': {'channel_id': 'UCbXgNpp0jedKWcQiULLbDTA'},
    'Tech With Tim': {'channel_id': 'UC4JX40jDee_tINbkjycV4Sg'},
    'Data Science Dojo (Clips)': {'channel_id': 'UCzL_0nIe8B4-7ShhVPfJkgw'},
    'TensorFlow': {'channel_id': 'UC0rqucBdTuFTjJiefW5t-IQ'},
    'PyData': {'channel_id': 'UCQtHyjAolUlJf4rJiKS1iHg'},
    'Deeplearning.ai': {'channel_id': 'UCcIXc5mJsHVYTZR1maL5l9w'},
    'Machine Learning Street Talk': {'channel_id': 'UCv7pXLtY96_b905NM-RuM9Q'},
    'Google Cloud Platform': {'channel_id': 'UCLecVXkx2lY4n-qJrwMfHDg'},
    'Arxiv Insights': {'channel_id': 'UCNIkB2IeJ-6AmZv7bQ1oBYg'},
    'DeepLearning.TV': {'channel_id': 'UC9skD8zwAeOx3XrDyrhH-5g'},
    'Springboard': {'channel_id': 'UCjDNLkWgBF_NQv_2fm9WmOw'},
    'TWIML AI Podcast': {'channel_id': 'UCZFipeZtQM5CKUbxDlKH8tg'},
    'IBM Research': {'channel_id': 'UC2h8a19sjqC5sNHdru-OHCA'},
    'TensorFlow (Dev Summit)': {'channel_id': 'UCnauH8RfULW21R7dJICQ7sg'},
    'MIT OpenCourseWare (ML)': {'channel_id': 'UCN590RH2fdek8-N9qYOWdeg'},
    'DeepMind': {'channel_id': 'UCP7jMXSY2xbc3KCAE0MHQ-A'},
    'Andrew Ng / Deeplearning.ai': {'channel_id': 'UCLOJ3R9Z3v4nNkVgI2kLOAg'},
    # Additional channels can be added here as needed.
}

# Maximum number of videos to extract per channel.  Because RSS feeds are
# limited to ~15 entries, setting this to 15 ensures we don't miss
# entries that aren't present in the feed.  Reduce or increase this
# depending on how many channels you have and the target total.
MAX_PER_CHANNEL = 40

# Desired total number of video entries.  If there are not enough
# channels to meet this number with `MAX_PER_CHANNEL` per channel,
# decrease the total or add more channels to the list.
TARGET_TOTAL = 1000


def build_feed_url(chan_def: Dict[str, str]) -> str:
    """Construct the RSS feed URL for a given channel definition."""
    if 'channel_id' in chan_def:
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={chan_def['channel_id']}"
    elif 'user' in chan_def:
        return f"https://www.youtube.com/feeds/videos.xml?user={chan_def['user']}"
    else:
        raise ValueError("Channel definition must include either 'channel_id' or 'user' key")


def parse_feed_for_videos(xml_content: str) -> List[Tuple[str, str]]:
    """
    Parse the provided RSS XML string and extract video IDs and titles.

    Returns a list of (video_id, title) tuples in the order they appear
    in the feed.
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise RuntimeError(f"Failed to parse XML: {e}") from e
    # The 'entry' elements contain individual videos.  Each entry has a
    # 'yt:videoId' or 'id' element containing the video ID and a 'title'
    # element for the video title.
    ns = {
        'atom': 'http://www.w3.org/2005/Atom',
        'yt': 'http://www.youtube.com/xml/schemas/2015'
    }
    videos: List[Tuple[str, str]] = []
    for entry in root.findall('atom:entry', ns):
        # Video ID can be found either in 'yt:videoId' or in the 'id'
        # element after the last ':' character.
        video_id = None
        vid_elem = entry.find('yt:videoId', ns)
        if vid_elem is not None and vid_elem.text:
            video_id = vid_elem.text.strip()
        else:
            id_elem = entry.find('atom:id', ns)
            if id_elem is not None and id_elem.text:
                # The ID looks like 'yt:video:<VIDEO_ID>'.  Split on ':'
                parts = id_elem.text.split(':')
                video_id = parts[-1] if parts else None
        title_elem = entry.find('atom:title', ns)
        title = title_elem.text.strip() if title_elem is not None and title_elem.text else ''
        if video_id:
            videos.append((video_id, title))
    return videos


def fetch_channel_videos(name: str, chan_def: Dict[str, str]) -> List[Tuple[str, str, str]]:
    """
    Download and parse the RSS feed for a single channel.

    Returns a list of tuples (channel_name, video_id, title).  If
    downloading or parsing fails, returns an empty list.
    """
    feed_url = build_feed_url(chan_def)
    try:
        response = requests.get(feed_url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Warning: Failed to fetch feed for {name}: {e}")
        return []
    try:
        videos = parse_feed_for_videos(response.text)
    except Exception as e:
        print(f"Warning: Failed to parse feed for {name}: {e}")
        return []
    # Take at most MAX_PER_CHANNEL videos
    selected = [(name, vid, title) for vid, title in videos[:MAX_PER_CHANNEL]]
    return selected


def generate_video_list(channels: Dict[str, Dict[str, str]], target: int) -> List[Tuple[str, str, str]]:
    """
    Iterate over channels and collect video entries until `target` is reached.

    Returns a list of (channel_name, video_id, title) tuples.
    """
    all_entries: List[Tuple[str, str, str]] = []
    for name, chan_def in channels.items():
        entries = fetch_channel_videos(name, chan_def)
        all_entries.extend(entries)
        print(f"Fetched {len(entries)} videos from {name}")
        if len(all_entries) >= target:
            break
        # Sleep briefly to be polite to YouTube servers
        time.sleep(1)
    # Truncate list to target size
    if len(all_entries) > target:
        all_entries = all_entries[:target]
    return all_entries


def write_csv(entries: List[Tuple[str, str, str]], csv_path: str) -> None:
    """Write collected video entries to a CSV file."""
    with open(csv_path, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['channel_name', 'video_id', 'title'])
        for entry in entries:
            writer.writerow(entry)
    print(f"Wrote {len(entries)} rows to {csv_path}")


if __name__ == '__main__':
    print("Starting to collect YouTube video IDs...")
    video_entries = generate_video_list(CHANNELS, TARGET_TOTAL)
    if not video_entries:
        print("No videos collected. Please check network connectivity or channel definitions.")
    else:
        write_csv(video_entries, 'youtube_video_list.csv')