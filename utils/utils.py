import os
import json
import re
import logging
from pathlib import Path
from difflib import SequenceMatcher  # ✅ For fuzzy text similarity

logger = logging.getLogger(__name__)

__all__ = [
    "load_json", "save_json", "ensure_dir_exists",
    "vtt_time_to_seconds", "is_similar", "parse_vtt_file",
    "split_into_chunks"
]

def ensure_dir_exists(path):
    """Ensure that a directory exists."""
    path = str(path) if isinstance(path, Path) else path
    os.makedirs(path, exist_ok=True)

def load_json(filepath):
    """Load JSON file and return Python object."""
    filepath = str(filepath) if isinstance(filepath, Path) else filepath
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, filepath):
    """Save Python object as JSON."""
    filepath = str(filepath) if isinstance(filepath, Path) else filepath
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def vtt_time_to_seconds(time_str):
    """Convert VTT timestamp to seconds."""
    try:
        time_str = time_str.strip().split()[0]
        parts = time_str.split(':')
        if len(parts) != 3:
            raise ValueError("Invalid time format")
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds_parts = parts[2].split('.')
        seconds = int(seconds_parts[0])
        milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
        return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000
    except Exception as e:
        logger.warning(f"⚠️ Failed to parse time: '{time_str}' ({e})")
        return 0.0

def is_similar(a, b, threshold=0.9):
    """Check if two strings are similar above a threshold."""
    if a is None or b is None:
        return False
    return SequenceMatcher(None, a, b).ratio() > threshold

def parse_vtt_file(vtt_file: Path):
    """Parse VTT file and convert it to a cleaned transcript format."""
    transcript = []
    last_text = None
    last_start_time = -1.0

    try:
        with vtt_file.open("r", encoding="utf-8") as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if '-->' in line:
                timestamp_parts = line.split(' --> ')
                if len(timestamp_parts) != 2:
                    i += 1
                    continue

                start_time = vtt_time_to_seconds(timestamp_parts[0])
                end_time = vtt_time_to_seconds(timestamp_parts[1])

                if end_time <= start_time:
                    logger.warning(f"⚠️ Invalid duration in VTT: start={start_time}, end={end_time}")
                    duration = 3.0
                else:
                    duration = round(end_time - start_time, 3)
                    duration = max(duration, 0.5)

                # Collect subtitle text
                i += 1
                text_lines = []
                while i < len(lines) and lines[i].strip():
                    clean_line = re.sub(r'<.*?>', '', lines[i].strip())  # Remove HTML tags
                    clean_line = re.sub(r'\[.*?\]', '', clean_line)     # Remove square bracket content
                    clean_line = clean_line.replace('♪', '')
                    clean_line = re.sub(r'\s+', ' ', clean_line).strip()
                    if clean_line:
                        text_lines.append(clean_line)
                    i += 1

                text = ' '.join(text_lines).strip()

                if not text or is_similar(text, last_text):
                    continue
                if last_start_time >= 0 and abs(start_time - last_start_time) < 0.3:
                    logger.debug(f"⏩ Skipping overlapping segment at {start_time}")
                    continue

                transcript.append({
                    'text': text,
                    'start': start_time,
                    'duration': duration
                })
                last_text = text
                last_start_time = start_time
            else:
                i += 1

    except Exception as e:
        logger.error(f"🔥 Error parsing VTT file: {type(e).__name__}: {e}")
        return None

    return transcript

def split_into_chunks(segments, chunk_size=30):
    """
    Split transcript segments into larger text chunks for embedding.
    Each chunk merges ~`chunk_size` segments.
    """
    chunks = []
    for i in range(0, len(segments), chunk_size):
        chunk = segments[i:i + chunk_size]
        combined_text = " ".join([seg["text"] for seg in chunk])
        chunks.append({
            "text": combined_text,
            "start": chunk[0]["start"],
            "end": chunk[-1]["start"] + chunk[-1]["duration"]
        })
    return chunks
