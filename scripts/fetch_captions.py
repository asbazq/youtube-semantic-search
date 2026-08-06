"""yt-dlp로 YouTube 자막을 받아 프로젝트용 JSON으로 변환한다.

입력: 영상 ID와 사용자가 정한 제목
출력: data/captions/제목_영상ID.json
"""

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

# 이 프로젝트는 한국어 자막만 사용한다. 영어 자막으로 대체하지 않는다.
load_dotenv()
DATA_DIR = Path("data/captions")
VIDEO_LIST_FILE = Path("video_ids.json")
CAPTION_LANGUAGES = "ko"
YTDLP_COOKIES_FROM_BROWSER = os.getenv("YTDLP_COOKIES_FROM_BROWSER")

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def select_subtitle_file(subtitle_files):
    """여러 VTT 경로 중 한국어 파일 하나를 반환한다.

    ``subtitle_files``는 Path 객체의 리스트다. 예를 들어 파일명이
    ``영상.ko.vtt``이면 우선순위 0이 되어 선택된다. ``min(..., key=함수)``는
    파일 자체가 아니라 각 파일에 함수를 적용한 결과를 서로 비교한다.
    """
    # "ko" 문자열을 ["ko"] 리스트로 바꾸는 list comprehension이다.
    language_order = [
        language.strip() for language in CAPTION_LANGUAGES.split(",") if language.strip()
    ]

    def priority(subtitle_file):
        """정렬에 쓸 (언어 우선순위, 파일명) 튜플을 만든다."""
        name = subtitle_file.name.lower()
        for index, language in enumerate(language_order):
            language = language.lower()
            if name.endswith(f".{language}.vtt") or f".{language}-" in name:
                return index, name
        return len(language_order), name

    # min의 key에 함수를 넘기면 각 항목의 priority 결과가 가장 작은 것을 고른다.
    return min(subtitle_files, key=priority)


def fetch_caption_with_ytdlp(video_id: str, title: str, output_dir: Path):
    """영상 하나의 한국어 자막을 내려받아 JSON으로 저장한다.

    이 함수가 직접 YouTube 통신을 구현하지는 않는다. ``cmd`` 리스트를 만든 뒤
    별도 프로그램인 yt-dlp를 실행한다. 성공 흐름은 다음과 같다:
    yt-dlp 실행 → 임시 VTT 찾기 → VTT 파싱 → captions JSON 저장 → True 반환.
    어느 단계든 실패하면 False를 반환해 ``main.py``가 다음 단계를 중단하게 한다.
    """
    try:
        logger.info(f"🔄 Fetching transcript for {title} ({video_id}) using yt-dlp...")

        # with 블록이 끝나면 임시 폴더와 원본 VTT는 자동 삭제된다.
        with tempfile.TemporaryDirectory() as temp_dir:
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            # 쉘 문자열 대신 인자 리스트를 쓰면 공백이 있는 제목도 안전하게 전달된다.
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

            # 위 리스트는 터미널에서 다음과 비슷한 명령이 된다.
            # python -m yt_dlp --write-subs --sub-langs ko ... 영상URL

            if YTDLP_COOKIES_FROM_BROWSER:
                cmd[3:3] = ["--cookies-from-browser", YTDLP_COOKIES_FROM_BROWSER]

            # 출력은 result.stdout/stderr에 문자열로 담고 최대 60초만 기다린다.
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            # 운영체제 관례상 종료 코드 0은 성공, 0 이외의 값은 실패다.
            if result.returncode == 0:
                subtitle_files = list(Path(temp_dir).glob("*.vtt"))

                if subtitle_files:
                    subtitle_file = select_subtitle_file(subtitle_files)
                    logger.info("🗣️ Selected subtitle: %s", subtitle_file.name)
                    # transcript 자료형: [{"text": str, "start": float,
                    #                       "duration": float}, ...]
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
    """다른 모듈이 자막 다운로드 기능만 호출할 때 사용하는 편의 함수."""
    output_dir = Path("data/captions")
    ensure_dir_exists(output_dir)
    return fetch_caption_with_ytdlp(video_id, title, output_dir)


def prompt_user_for_input():
    """터미널에서 영상 ID와 제목을 입력받아 튜플로 반환한다."""
    print()
    video_id = input("🎥 Enter the YouTube video ID: ").strip()
    title = input("📝 Enter a title/label for the video: ").strip()
    return video_id, title


def main():
    """명령행 인자 유무에 따라 단일 영상/대화형/일괄 모드를 실행한다."""
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
    # sys.argv[0]은 파일명, [1]과 [2]는 사용자가 전달한 영상 ID와 제목이다.
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
