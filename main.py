"""프로젝트의 시작점(entry point).

사용자의 메뉴 입력을 받고 아래 파이프라인을 순서대로 실행한다.
YouTube 자막 다운로드 -> 자막 전처리 -> 임베딩 생성 -> ChromaDB 저장 -> 검색
"""

import os
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
    """별도 Python 스크립트를 실행하고 성공 여부를 bool로 반환한다."""
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
    """한 영상에 필요한 전체 처리 단계를 실행한다."""
    python_exec = sys.executable

    # First 3 steps remain the same
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

def main():
    """CLI 메뉴를 반복해서 보여 주는 메인 함수."""
    # 객체를 한 번 생성해 모델과 DB 연결을 반복해서 로드하지 않게 한다.
    engine = YouTubeSemanticSearch()
    print("\n🎥 Welcome to YouTube Semantic Search Engine")

    # break를 만날 때까지 계속 실행되는 무한 반복문이다.
    while True:
        print("\nOptions:")
        print("1. Process new YouTube video")
        print("2. Show available videos")
        print("3. Exit")

        choice = input("Choose an option (1-3): ").strip()

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
            results = engine.search_by_video(query, video_id)

            # results는 dict이며, 실패 시에는 "error" 키가 들어 있다.
            if "error" in results:
                print(f"❌ {results['error']}")
            else:
                print(f"\n📊 Found {results['total_found']} result(s):")
                for i, res in enumerate(results["results"], 1):
                    print(f"\n{i}. 🎬 Video: {res['video_title']}")
                    print(f"   ⏰ Time: {format_time(res['start_time'])} - {format_time(res['end_time'])}")
                    print(f"   🔗 URL: {res['youtube_url']}")
                    print(f"   📝 Text: {res['text'][:200]}...")

        elif choice == "2":
            videos = engine.get_video_list()
            print("\n🎬 Available Videos in ChromaDB:")
            for v in videos:
                print(f" - {v['video_id']} | {v['title']}")
        elif choice == "3":
            print("👋 Exiting. Goodbye!")
            break
        else:
            print("❌ Invalid choice. Try again.")

# 이 파일을 직접 실행할 때만 main()을 호출한다. 다른 파일에서 import할 때는
# 자동 실행되지 않는다.
if __name__ == "__main__":
    main()
