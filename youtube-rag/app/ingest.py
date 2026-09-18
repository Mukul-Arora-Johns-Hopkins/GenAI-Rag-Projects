"""Ingestion for YouTube Research Assistant — fetch transcript and chunk it."""
import re
from typing import List
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled

from youtube_rag.config import settings
from shared.rag_core import chunk_text, Chunk


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r"(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([^&?\/\s]+)",
        r"^([a-zA-Z0-9_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from: {url}")


def fetch_transcript(video_id: str) -> str:
    """Fetch transcript for a YouTube video. Tries multiple languages."""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Try English first, then any available
        for lang in ["en", "en-US", "en-GB"]:
            try:
                transcript = transcript_list.find_transcript([lang])
                data = transcript.fetch()
                text = " ".join(entry["text"] for entry in data)
                return text
            except (NoTranscriptFound, TranscriptsDisabled):
                continue

        # Fall back to any available language
        transcript = transcript_list.find_transcript(transcript_list.languages)
        data = transcript.fetch()
        text = " ".join(entry["text"] for entry in data)
        return text

    except NoTranscriptFound:
        raise ValueError("No transcript available for this video.")
    except TranscriptsDisabled:
        raise ValueError("Transcripts are disabled for this video.")
    except Exception as e:
        if "video_id" in str(e).lower() or "not found" in str(e).lower():
            raise ValueError(f"Video not found or unavailable: {e}")
        raise


def parse_transcript_with_timestamps(video_id: str):
    """Fetch transcript with timestamps for citation support.

    Returns list of (timestamp, text) tuples.
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = None

        for lang in ["en", "en-US", "en-GB"]:
            try:
                transcript = transcript_list.find_transcript([lang])
                break
            except (NoTranscriptFound, TranscriptsDisabled):
                continue

        if transcript is None:
            transcript = transcript_list.find_transcript(transcript_list.languages)

        data = transcript.fetch()
        return [(entry["start"], entry["text"]) for entry in data]

    except Exception:
        return []


def transcript_to_text(transcript_data) -> str:
    """Convert transcript data (list of dicts or tuples) to plain text."""
    if not transcript_data:
        return ""

    if isinstance(transcript_data[0], dict):
        return " ".join(entry["text"] for entry in transcript_data)
    else:
        return " ".join(text for _, text in transcript_data)


def chunk_transcript(transcript_text: str, video_id: str) -> List[Chunk]:
    """Chunk transcript text with timestamp-based source labels."""
    # First get timestamps for citation
    timestamp_data = parse_transcript_with_timestamps(video_id)

    # Build a timestamp lookup by approximate position
    timestamp_lookup = {}
    if timestamp_data:
        total_duration = timestamp_data[-1][0] if timestamp_data else 0
        for start_time, text in timestamp_data:
            # Estimate position in the full text
            text_len = len(text)
            pos_estimate = int((start_time / total_duration) * len(transcript_text)) if total_duration > 0 else 0
            timestamp_lookup[pos_estimate] = start_time

    chunks = chunk_text(
        transcript_text,
        source_label=f"video {video_id[:8]}",
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    # Add timestamps to chunk metadata
    for chunk in chunks:
        chunk.metadata = {"video_id": video_id}

    # Try to assign timestamps based on text position
    for chunk in chunks:
        chunk_start = transcript_text.find(chunk.text[:50])
        if chunk_start >= 0 and timestamp_lookup:
            # Find closest timestamp
            closest_time = min(timestamp_lookup.keys(),
                             key=lambda k: abs(k - chunk_start))
            chunk.metadata["timestamp"] = format_timestamp(timestamp_lookup[closest_time])
            chunk.source = f"{format_timestamp(chunk.metadata['timestamp'])}"

    return chunks


def format_timestamp(seconds: float) -> str:
    """Format seconds as MM:SS."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def ingest_video(url: str) -> List[Chunk]:
    """Full ingestion pipeline: fetch transcript → chunk → return chunks."""
    video_id = extract_video_id(url)
    transcript_data = parse_transcript_with_timestamps(video_id)

    if not transcript_data:
        raise ValueError("No transcript available for this video.")

    transcript_text = transcript_to_text(transcript_data)

    # Truncate if needed
    if len(transcript_text) > settings.max_transcript_length:
        transcript_text = transcript_text[:settings.max_transcript_length]

    chunks = chunk_transcript(transcript_text, video_id)
    return chunks
