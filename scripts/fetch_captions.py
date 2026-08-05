import json
import sys
import os
import logging
import subprocess
import tempfile
from pathlib import Path

from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.utils import save_json, parse_vtt_file, ensure_dir_exists

# --- Configurations ---
load_dotenv()
DATA_DIR = Path("data/captions")
VIDEO_LIST_FILE = Path("video_ids.json")
CAPTION_LANGUAGES = os.getenv("CAPTION_LANGUAGES", "ko,en")
YTDLP_COOKIES_FROM_BROWSER = os.getenv("YTDLP_COOKIES_FROM_BROWSER")

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def fetch_caption_with_ytdlp(video_id: str, title: str, output_dir: Path):
    """Fetch captions using yt-dlp and parse."""
    try:
        logger.info(f"🔄 Fetching transcript for {title} ({video_id}) using yt-dlp...")

        with tempfile.TemporaryDirectory() as temp_dir:
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            cmd = [
                sys.executable,
                "-m",
                "yt_dlp",
                "--write-subs",
                "--write-auto-subs",
                "--sub-langs", CAPTION_LANGUAGES,
                "--sub-format", "vtt",
                "--skip-download",
                "--output", f"{temp_dir}/%(title)s.%(ext)s",
                video_url
            ]

            if YTDLP_COOKIES_FROM_BROWSER:
                cmd[3:3] = ["--cookies-from-browser", YTDLP_COOKIES_FROM_BROWSER]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                subtitle_files = list(Path(temp_dir).glob("*.vtt"))

                if subtitle_files:
                    subtitle_file = subtitle_files[0]
                    transcript = parse_vtt_file(subtitle_file)

                    if transcript:
                        output_file = output_dir / f"{title}_{video_id}.json"
                        save_json(transcript, output_file)
                        logger.info(f"✅ Saved captions for {title} ({video_id}) - {len(transcript)} segments")
                        return True
                    else:
                        logger.warning(f"⚠️ Could not parse subtitle file for {video_id}")
                        return False
                else:
                    logger.warning(f"⚠️ No subtitle files found for {video_id}")
                    return False
            else:
                error_message = result.stderr.strip() or result.stdout.strip()
                logger.error("❌ yt-dlp failed for %s:\n%s", video_id, error_message)
                return False

    except subprocess.TimeoutExpired:
        logger.error(f"⏰ Timeout while fetching {video_id}")
        return False
    except Exception as e:
        logger.error(f"🔥 Error fetching {video_id}: {type(e).__name__}: {e}")
        return False


def fetch_captions_for_video(video_id: str, title: str) -> bool:
    output_dir = Path("data/captions")
    ensure_dir_exists(output_dir)
    return fetch_caption_with_ytdlp(video_id, title, output_dir)


def prompt_user_for_input():
    """Interactive mode: prompt for video ID and title"""
    print()
    video_id = input("🎥 Enter the YouTube video ID: ").strip()
    title = input("📝 Enter a title/label for the video: ").strip()
    return video_id, title


def main():
    ensure_dir_exists(DATA_DIR)

    try:
        subprocess.run(
            [sys.executable, "-m", "yt_dlp", "--version"],
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("❌ yt-dlp is not installed. Install it with: pip install yt-dlp")
        raise SystemExit(1)

    # --- Interactive input if no args and video_ids.json doesn't exist ---
    if len(sys.argv) == 1 and not VIDEO_LIST_FILE.exists():
        video_id, title = prompt_user_for_input()
        success = fetch_caption_with_ytdlp(video_id, title, DATA_DIR)
        if not success:
            raise SystemExit(1)
        return

    # --- Run with command-line arguments ---
    if len(sys.argv) == 3:
        video_id = sys.argv[1]
        title = sys.argv[2]
        logger.info(f"🎬 Processing 1 video: {title} ({video_id})")
        success = fetch_caption_with_ytdlp(video_id, title, DATA_DIR)
        if success:
            logger.info("🎯 Completed! Successfully processed 1/1 videos")
        else:
            logger.warning("⚠️ Failed to process the video.")
            raise SystemExit(1)
        return

    # --- Fallback to batch mode using video_ids.json ---
    if not VIDEO_LIST_FILE.exists():
        logger.error(f"❌ File not found: {VIDEO_LIST_FILE}")
        return

    with open(VIDEO_LIST_FILE, "r", encoding="utf-8") as f:
        videos = json.load(f)

    logger.info(f"🎬 Processing {len(videos)} videos...")
    success_count = 0

    for video in videos:
        success = fetch_caption_with_ytdlp(video["video_id"], video["title"], DATA_DIR)
        if success:
            success_count += 1

    logger.info(f"🎯 Completed! Successfully processed {success_count}/{len(videos)} videos")
    if success_count != len(videos):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
