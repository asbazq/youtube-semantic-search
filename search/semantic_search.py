import logging
from typing import List, Dict, Optional, Any
from sentence_transformers import SentenceTransformer
import sys
import os
import numpy as np
import argparse
import subprocess
from datetime import timedelta  # ✅ Added for time formatting

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.pinecone_setup import get_pinecone_client, get_pinecone_index

# --- Configurations ---
MODEL_NAME = "all-mpnet-base-v2"
EMBEDDING_DIMENSION = 768
NAMESPACE = "youtube-semantic-search"

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

def format_time(seconds: int) -> str:
    """Format seconds into hh:mm:ss"""
    try:
        return str(timedelta(seconds=int(seconds)))
    except:
        return "00:00:00"

class YouTubeSemanticSearch:
    def __init__(self):
        logger.info("🔄 Initializing YouTube Semantic Search...")
        try:
            logger.info(f"📦 Loading embedding model: {MODEL_NAME}")
            self.model = SentenceTransformer(MODEL_NAME)
            logger.info("✅ Embedding model loaded")

            logger.info("🔗 Connecting to Pinecone...")
            
            self.pc = get_pinecone_client()
            self.index = get_pinecone_index()

            logger.info("✅ Pinecone connection established")

        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            raise

    def embed_query(self, query: str) -> Optional[List[float]]:
        try:
            if not query or not query.strip():
                logger.warning("⚠️ Empty query provided")
                return None
            return self.model.encode([query.strip()], convert_to_numpy=True)[0].tolist()
        except Exception as e:
            logger.error(f"❌ Embedding error for query '{query}': {e}")
            return None

    def search(self, query: str, top_k: int = 10, include_metadata: bool = True) -> Dict[str, Any]:
        try:
            query_embedding = self.embed_query(query)
            if query_embedding is None:
                return {"error": "Failed to embed query"}

            logger.info(f"🔍 Searching top {top_k} results for: '{query}'")
            search_results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=include_metadata,
                namespace=NAMESPACE
            )

            matches = [m for m in search_results.get("matches", []) if m["score"] > 0.3]

            results = {
                "query": query,
                "total_found": len(matches),
                "results": []
            }

            for match in matches:
                metadata = match.get("metadata", {})
                video_id = metadata.get("video_id", "").split("&")[0]

                results["results"].append({
                    "text": metadata.get("text", ""),
                    "video_id": video_id,
                    "video_title": metadata.get("video_title", "Unknown"),
                    "start_time": metadata.get("start_time", 0),
                    "end_time": metadata.get("end_time", 0),
                    "duration": metadata.get("duration", 0),
                    "score": round(match.get("score", 0.0), 4),
                    "youtube_url": f"https://www.youtube.com/watch?v={video_id}&t={int(metadata.get('start_time', 0))}s"
                })

            return results

        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return {"error": str(e)}

    def search_by_video(self, query: str, video_id: str, top_k: int = 10) -> Dict[str, Any]:
        try:
            query_embedding = self.embed_query(query)
            if query_embedding is None:
                return {"error": "Failed to embed query"}

            search_results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter={"video_id": {"$eq": video_id}},
                namespace=NAMESPACE
            )

            matches = [m for m in search_results.get("matches", []) if m["score"] > 0.3]

            results = {
                "query": query,
                "video_id": video_id,
                "total_found": len(matches),
                "results": []
            }

            for match in matches:
                metadata = match.get("metadata", {})

                results["results"].append({
                    "text": metadata.get("text", ""),
                    "video_title": metadata.get("video_title", "Unknown"),
                    "start_time": metadata.get("start_time", 0),
                    "end_time": metadata.get("end_time", 0),
                    "score": round(match.get("score", 0.0), 4),
                    "youtube_url": f"https://www.youtube.com/watch?v={video_id}&t={int(metadata.get('start_time', 0))}s"
                })

            return results

        except Exception as e:
            logger.error(f"❌ Video-specific search failed: {e}")
            return {"error": str(e)}

    def get_video_list(self) -> List[Dict[str, str]]:
        try:
            sample_results = self.index.query(
                vector=[0.1] * EMBEDDING_DIMENSION,
                top_k=100,
                include_metadata=True,
                namespace=NAMESPACE
            )
            
            video_titles = {}
            for match in sample_results.get("matches", []):
                metadata = match.get("metadata", {})
                vid = metadata.get("video_id", "")
                title = metadata.get("video_title", "Unknown")
                if vid and vid not in video_titles:
                    video_titles[vid] = title
                    
            return [{"video_id": vid, "title": title} for vid, title in video_titles.items()]
        except Exception as e:
            logger.error(f"❌ Failed to get video list: {e}")
            return []


def interactive_search():
    engine = YouTubeSemanticSearch()
    print("\n🎥 Welcome to YouTube Semantic Search Engine")
    while True:
        print("\nOptions:")
        print("1. General search")
        print("2. Search by specific video")
        print("3. Show available videos")
        print("4. Exit")

        choice = input("Choose an option (1-4): ").strip()

        if choice == "1":
            query = input("🔍 Enter search query: ").strip()
            results = engine.search(query)
        elif choice == "2":
            video_id = input("📼 Enter video ID: ").strip()
            query = input("🔍 Enter search query: ").strip()
            results = engine.search_by_video(query, video_id)
        elif choice == "3":
            videos = engine.get_video_list()
            print("\n🎬 Available Videos:")
            for v in videos:
                print(f" - {v['video_id']} | {v['title']}")
            continue
        elif choice == "4":
            print("👋 Exiting. Goodbye!")
            break
        else:
            print("❌ Invalid choice. Try again.")
            continue

        if "error" in results:
            print(f"❌ {results['error']}")
        else:
            print(f"\n📊 Found {results['total_found']} result(s):")
            for i, res in enumerate(results["results"], 1):
                print(f"\n{i}. 🎬 Video: {res['video_title']}")
                print(f"   ⏰ Time: {format_time(res['start_time'])} - {format_time(res['end_time'])}")  # ✅ Updated
                print(f"   🔗 URL: {res['youtube_url']}")
                print(f"   📝 Text: {res['text'][:200]}...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_pipeline", action="store_true", help="Run preprocessing pipeline before search")
    args = parser.parse_args()

    if args.run_pipeline:
        logger.info("🚀 Running pipeline script...")
        subprocess.run(["python", "run_pipeline.py"])

    interactive_search()


