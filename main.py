"""프로젝트의 시작점(entry point).

사용자의 메뉴 입력을 받고 아래 파이프라인을 순서대로 실행한다.
YouTube 자막 다운로드 -> 자막 전처리 -> 임베딩 생성 -> ChromaDB 저장 -> 검색
"""

import json
import os
import re
import sys
import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse
from search.semantic_search import YouTubeSemanticSearch, format_time


def normalize_video_id(value: str) -> str:
    """영상 ID 또는 YouTube URL에서 순수 영상 ID만 꺼낸다.

    ``value: str``은 매개변수가 문자열이라는 타입 힌트이고,
    ``-> str``은 이 함수가 문자열을 반환한다는 뜻이다.
    """
    # strip()은 양 끝 공백을, 이어지는 strip('"') 등은 따옴표를 제거한다.
    value = value.strip().strip('"').strip("'")
    if not value:
        return ""

    # 한 줄 if 문: URL이 아니면 파싱하기 쉬운 임시 URL 형태로 만든다.
    candidate = value if "://" in value else f"https://youtube.com/watch?v={value}"
    parsed = urlparse(candidate)

    if parsed.hostname in {"youtu.be", "www.youtu.be"}:
        return parsed.path.strip("/").split("/")[0]

    query_id = parse_qs(parsed.query).get("v", [""])[0]
    if query_id:
        return query_id

    return value.split("&", 1)[0].split("?", 1)[0]

def run_script(command: list):
    """명령 리스트로 자식 프로세스를 실행하고 성공 여부를 반환한다.

    예: ``[python경로, "scripts/fetch_captions.py", 영상ID, 제목]``.
    현재 ``main.py``가 부모 프로세스이고 새로 실행되는 스크립트가 자식
    프로세스다. 자식에서 ``SystemExit(1)``이 발생하면 여기서는
    ``CalledProcessError``가 되어 False를 반환한다.
    """
    try:
        # 현재 프로세스의 환경 변수를 복사한다. 원본 os.environ은 수정하지 않는다.
        env = os.environ.copy()
        env['PYTHONPATH'] = os.getcwd()
        print(f"\n🚀 Running: {' '.join(command)}")
        # check=True이면 자식 프로세스 종료 코드가 0이 아닐 때 예외가 발생한다.
        subprocess.run(command, check=True, env=env)
        print(f"✅ {' '.join(command)} completed successfully\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {command} failed with exit code {e.returncode}")
        return False

def find_processed_file(video_id: str, video_title: str) -> Optional[str]:
    """영상 ID/제목에 해당하는 임베딩 JSON 경로를 찾는다.

    찾으면 경로 문자열을, 찾지 못하면 None을 반환한다. 여러 파일명 형태를
    허용하는 이유는 제목의 공백이 저장 과정에서 밑줄로 바뀔 수 있기 때문이다.
    """
    embeddings_dir = Path("data/embeddings")

    # Try different possible filename patterns
    possible_patterns = [
        f"processed_{video_title.replace(' ', '_')}_{video_id}.json",
        f"processed_{video_title.replace(' ', '')}_{video_id}.json",
        f"processed_{'_'.join(video_title.split())}_{video_id}.json",
        f"{video_title.replace(' ', '_')}_{video_id}.json",
        f"{video_id}.json"
    ]

    for pattern in possible_patterns:
        file_path = embeddings_dir / pattern
        if file_path.exists():
            return str(file_path)

    # If exact match not found, search for files containing the video_id
    for file_path in embeddings_dir.glob("*.json"):
        if video_id in file_path.name:
            return str(file_path)

    return None

def full_pipeline(video_id: str, video_title: str) -> bool:
    """영상 하나를 검색 가능하게 만드는 전체 파이프라인을 실행한다.

    각 단계의 출력 파일이 다음 단계의 입력이 된다:
    captions JSON → chunks JSON → embeddings JSON → ChromaDB.
    반환값 True는 모든 단계 성공, False는 중간 단계 실패를 뜻한다.
    """
    python_exec = sys.executable

    # First 3 steps remain the same
    # 중첩 리스트: 바깥 리스트는 단계 목록, 안쪽 리스트는 한 명령의 인자 목록이다.
    initial_steps = [
        [python_exec, "scripts/fetch_captions.py", video_id, video_title],
        [python_exec, "scripts/preprocess_captions.py"],
        [python_exec, "scripts/embed_chunks.py"]
    ]

    # Run initial steps
    # 리스트 안의 각 명령 리스트를 순서대로 실행한다.
    for step in initial_steps:
        if not run_script(step):
            return False

    # Find the specific processed file
    processed_file = find_processed_file(video_id, video_title)
    if not processed_file:
        print(f"❌ Could not find processed embedding file for video {video_id}")
        print("🔍 Available files in data/embeddings/:")
        embeddings_dir = Path("data/embeddings")
        if embeddings_dir.exists():
            for file in embeddings_dir.glob("*.json"):
                print(f"   - {file.name}")
        return False

    print(f"📁 Found processed file: {processed_file}")

    # Upload only the specific file
    upload_command = [python_exec, "db/upload_embeddings.py", "--file", processed_file]
    if not run_script(upload_command):
        return False

    return True

def full_pipeline_all_files(video_id: str, video_title: str) -> bool:
    """대안 파이프라인: 마지막에 모든 임베딩 파일을 DB에 업로드한다."""
    python_exec = sys.executable
    steps = [
        [python_exec, "scripts/fetch_captions.py", video_id, video_title],
        [python_exec, "scripts/preprocess_captions.py"],
        [python_exec, "scripts/embed_chunks.py"],
        [python_exec, "db/upload_embeddings.py", "--all"]
    ]

    for step in steps:
        if not run_script(step):
            return False
    return True


def batch_pipeline(videos: list[tuple[str, str]]) -> tuple[int, int]:
    """여러 영상의 자막을 받은 뒤 전처리와 임베딩은 한 번씩 실행한다."""
    python_exec = sys.executable
    fetched_videos = []

    for video_id, video_title in videos:
        command = [python_exec, "scripts/fetch_captions.py", video_id, video_title]
        if run_script(command):
            fetched_videos.append((video_id, video_title))
        else:
            print(f"⚠️ Skipping failed video: {video_title} ({video_id})")

    if not fetched_videos:
        return 0, len(videos)

    for command in (
        [python_exec, "scripts/preprocess_captions.py"],
        [python_exec, "scripts/embed_chunks.py"],
    ):
        if not run_script(command):
            return 0, len(videos)

    uploaded = 0
    for video_id, video_title in fetched_videos:
        processed_file = find_processed_file(video_id, video_title)
        if processed_file and run_script(
            [python_exec, "db/upload_embeddings.py", "--file", processed_file]
        ):
            uploaded += 1
        else:
            print(f"⚠️ Could not upload: {video_title} ({video_id})")

    return uploaded, len(videos)


def safe_video_title(title: str, fallback: str) -> str:
    """영상 제목을 자막 JSON 파일명으로 안전하게 사용할 수 있게 정리한다."""
    cleaned = re.sub(r'[\\/:*?"<>|]', "_", title).strip().strip(".")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:120] or fallback


def get_playlist_videos(playlist_url: str) -> list[tuple[str, str]]:
    """yt-dlp로 재생목록의 공개 영상 ID와 제목을 가져온다."""
    command = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--flat-playlist",
        "--extractor-args",
        "youtube:lang=ko",
        "--dump-single-json",
        "--ignore-errors",
        "--no-warnings",
        playlist_url,
    ]
    cookies_from_browser = os.getenv("YTDLP_COOKIES_FROM_BROWSER")
    if cookies_from_browser:
        command[3:3] = ["--cookies-from-browser", cookies_from_browser]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        )
        playlist = json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        print("❌ Timed out while reading the playlist.")
        return []
    except subprocess.CalledProcessError as error:
        message = error.stderr.strip() if error.stderr else str(error)
        print(f"❌ Could not read playlist: {message}")
        return []
    except json.JSONDecodeError:
        print("❌ yt-dlp returned an invalid playlist response.")
        return []

    videos = []
    seen_video_ids = set()
    for entry in playlist.get("entries") or []:
        if not entry or not entry.get("id"):
            continue
        video_id = normalize_video_id(str(entry["id"]))
        if not video_id or video_id in seen_video_ids:
            continue
        title = safe_video_title(str(entry.get("title") or video_id), video_id)
        videos.append((video_id, title))
        seen_video_ids.add(video_id)
    return videos


def prompt_for_videos() -> list[tuple[str, str]]:
    """빈 URL이 입력될 때까지 영상 URL/ID와 표시 제목을 받는다."""
    videos = []
    print("\n여러 영상을 입력하세요. URL 입력 없이 Enter를 누르면 시작합니다.")
    while True:
        value = input(f"🎥 Video {len(videos) + 1} URL or ID: ").strip()
        if not value:
            break
        video_id = normalize_video_id(value)
        video_title = input("📝 Title/label: ").strip()
        if not video_id or not video_title:
            print("❌ URL/ID and title are both required.")
            continue
        videos.append((video_id, video_title))
    return videos


def print_search_results(results: dict) -> None:
    """검색 결과와 해당 위치로 바로 이동하는 YouTube 링크를 출력한다."""
    if "error" in results:
        print(f"❌ {results['error']}")
        return

    print(f"\n📊 Found {results['total_found']} result(s):")
    for index, result in enumerate(results["results"], 1):
        print(f"\n{index}. 🎬 Video: {result['video_title']}")
        print(
            f"   ⏰ Time: {format_time(result['start_time'])}"
            f" - {format_time(result['end_time'])}"
        )
        print(f"   ⭐ Score: {result['score']:.4f}")
        print(f"   🔗 URL: {result['youtube_url']}")
        print(f"   📝 Text: {result['text']}")

def main():
    """CLI 메뉴를 반복해서 보여 주는 메인 함수."""
    # 객체를 한 번 생성해 모델과 DB 연결을 반복해서 로드하지 않게 한다.
    engine = YouTubeSemanticSearch()
    print("\n🎥 Welcome to YouTube Semantic Search Engine")

    # break를 만날 때까지 계속 실행되는 무한 반복문이다.
    while True:
        print("\nOptions:")
        print("1. Process one YouTube video")
        print("2. Process multiple YouTube videos")
        print("3. Process a YouTube playlist")
        print("4. Search all videos")
        print("5. Show available videos")
        print("6. Exit")

        choice = input("Choose an option (1-6): ").strip()

        # if/elif는 사용자가 고른 메뉴 하나의 코드만 실행한다.
        if choice == "1":
            video_id = normalize_video_id(input("🎥 Enter YouTube Video ID or URL: "))
            video_title = input("📝 Enter a title/label for the video: ").strip()

            if not video_id or not video_title:
                print("❌ Video ID and title are required.")
                continue

            print("🔁 Processing video and uploading to search engine...")
            if not full_pipeline(video_id, video_title):
                print("❌ Processing failed.")
                continue

            query = input("🔍 Enter search query for this video: ").strip()
            print_search_results(engine.search_by_video(query, video_id))

        elif choice == "2":
            videos = prompt_for_videos()
            if not videos:
                print("⚠️ No videos entered.")
                continue
            uploaded, total = batch_pipeline(videos)
            print(f"\n✅ Uploaded {uploaded}/{total} video(s) to ChromaDB.")

        elif choice == "3":
            playlist_url = input("🎞️ YouTube playlist URL: ").strip()
            if not playlist_url:
                print("❌ Playlist URL is required.")
                continue
            videos = get_playlist_videos(playlist_url)
            if not videos:
                print("⚠️ No available videos found in the playlist.")
                continue
            print(f"\n🎬 Found {len(videos)} video(s):")
            for index, (video_id, title) in enumerate(videos, 1):
                print(f" {index}. {title} ({video_id})")
            print("\n🔁 Downloading captions and building the search index...")
            uploaded, total = batch_pipeline(videos)
            print(f"\n✅ Uploaded {uploaded}/{total} playlist video(s) to ChromaDB.")

        elif choice == "4":
            query = input("🔍 Search all videos: ").strip()
            if not query:
                print("❌ Search query is required.")
                continue
            print_search_results(engine.search(query))

        elif choice == "5":
            videos = engine.get_video_list()
            print("\n🎬 Available Videos in ChromaDB:")
            for v in videos:
                print(f" - {v['video_id']} | {v['title']}")
        elif choice == "6":
            print("👋 Exiting. Goodbye!")
            break
        else:
            print("❌ Invalid choice. Try again.")

# 이 파일을 직접 실행할 때만 main()을 호출한다. 다른 파일에서 import할 때는
# 자동 실행되지 않는다.
if __name__ == "__main__":
    main()
