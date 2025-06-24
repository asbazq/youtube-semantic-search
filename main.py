import os
import sys
import subprocess
from pathlib import Path
from search.semantic_search import YouTubeSemanticSearch, format_time
from db.pinecone_setup import get_pinecone_client, get_pinecone_index

def run_script(command: list):
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = os.getcwd()
        print(f"\n🚀 Running: {' '.join(command)}")
        subprocess.run(command, check=True, env=env)
        print(f"✅ {' '.join(command)} completed successfully\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {command} failed with exit code {e.returncode}")
        return False

def find_processed_file(video_id: str, video_title: str) -> str:
    """Find the processed embedding file for the specific video"""
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
    python_exec = sys.executable
    
    # First 3 steps remain the same
    initial_steps = [
        [python_exec, "scripts/fetch_captions.py", video_id, video_title],
        [python_exec, "scripts/preprocess_captions.py"],
        [python_exec, "scripts/embed_chunks.py"]
    ]
    
    # Run initial steps
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
    """Alternative: Run pipeline and upload all files (original behavior)"""
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
    engine = YouTubeSemanticSearch()
    print("\n🎥 Welcome to YouTube Semantic Search Engine")

    while True:
        print("\nOptions:")
        print("1. Process new YouTube video")
        print("2. Show available videos")
        print("3. Exit")

        choice = input("Choose an option (1-3): ").strip()

        if choice == "1":
            video_id = input("🎥 Enter YouTube Video ID: ").strip().strip('"').strip("'")
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
            print("\n🎬 Available Videos in Pinecone:")
            for v in videos:
                print(f" - {v['video_id']} | {v['title']}")
        elif choice == "3":
            print("👋 Exiting. Goodbye!")
            break
        else:
            print("❌ Invalid choice. Try again.")

if __name__ == "__main__":
    main()