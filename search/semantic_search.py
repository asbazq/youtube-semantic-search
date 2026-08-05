import argparse
import logging
import os
import subprocess
import sys
from datetime import timedelta
from typing import Any, Dict, List, Optional

from sentence_transformers import SentenceTransformer

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.chroma_setup import get_chroma_collection

MODEL_NAME = "all-mpnet-base-v2"
MIN_SCORE = 0.3

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def format_time(seconds: int) -> str:
    try:
        return str(timedelta(seconds=int(seconds)))
    except (TypeError, ValueError):
        return "00:00:00"


class YouTubeSemanticSearch:
    def __init__(self):
        logger.info("Loading embedding model: %s", MODEL_NAME)
        self.model = SentenceTransformer(MODEL_NAME)
        self.collection = get_chroma_collection()

    def embed_query(self, query: str) -> Optional[List[float]]:
        if not query or not query.strip():
            logger.warning("Empty query provided")
            return None
        try:
            return self.model.encode([query.strip()], convert_to_numpy=True)[0].tolist()
        except Exception as error:
            logger.error("Embedding error for query '%s': %s", query, error)
            return None

    def _query(self, embedding: List[float], top_k: int, where=None):
        count = self.collection.count()
        if count == 0:
            return []
        response = self.collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, count),
            where=where,
            include=["metadatas", "distances"],
        )
        metadatas = response.get("metadatas", [[]])[0]
        distances = response.get("distances", [[]])[0]
        return [
            (metadata, 1.0 - distance)
            for metadata, distance in zip(metadatas, distances)
            if 1.0 - distance > MIN_SCORE
        ]

    def search(self, query: str, top_k: int = 10, include_metadata: bool = True) -> Dict[str, Any]:
        del include_metadata  # Metadata is required to build the public result objects.
        embedding = self.embed_query(query)
        if embedding is None:
            return {"error": "Failed to embed query"}
        try:
            matches = self._query(embedding, top_k)
            results = {"query": query, "total_found": len(matches), "results": []}
            for metadata, score in matches:
                video_id = metadata.get("video_id", "").split("&")[0]
                results["results"].append(self._result(metadata, score, video_id, include_duration=True))
            return results
        except Exception as error:
            logger.error("Search failed: %s", error)
            return {"error": str(error)}

    def search_by_video(self, query: str, video_id: str, top_k: int = 10) -> Dict[str, Any]:
        embedding = self.embed_query(query)
        if embedding is None:
            return {"error": "Failed to embed query"}
        try:
            matches = self._query(embedding, top_k, where={"video_id": {"$eq": video_id}})
            results = {"query": query, "video_id": video_id, "total_found": len(matches), "results": []}
            for metadata, score in matches:
                results["results"].append(self._result(metadata, score, video_id))
            return results
        except Exception as error:
            logger.error("Video-specific search failed: %s", error)
            return {"error": str(error)}

    @staticmethod
    def _result(metadata, score, video_id, include_duration=False):
        result = {
            "text": metadata.get("text", ""),
            "video_id": video_id,
            "video_title": metadata.get("video_title", "Unknown"),
            "start_time": metadata.get("start_time", 0),
            "end_time": metadata.get("end_time", 0),
            "score": round(score, 4),
            "youtube_url": f"https://www.youtube.com/watch?v={video_id}&t={int(metadata.get('start_time', 0))}s",
        }
        if include_duration:
            result["duration"] = metadata.get("duration", 0)
        return result

    def get_video_list(self) -> List[Dict[str, str]]:
        try:
            stored = self.collection.get(include=["metadatas"])
            videos = {}
            for metadata in stored.get("metadatas", []):
                video_id = metadata.get("video_id", "")
                if video_id:
                    videos.setdefault(video_id, metadata.get("video_title", "Unknown"))
            return [{"video_id": video_id, "title": title} for video_id, title in videos.items()]
        except Exception as error:
            logger.error("Failed to get video list: %s", error)
            return []


def interactive_search():
    engine = YouTubeSemanticSearch()
    while True:
        print("\n1. General search\n2. Search by specific video\n3. Show available videos\n4. Exit")
        choice = input("Choose an option (1-4): ").strip()
        if choice == "1":
            results = engine.search(input("Enter search query: ").strip())
        elif choice == "2":
            video_id = input("Enter video ID: ").strip()
            results = engine.search_by_video(input("Enter search query: ").strip(), video_id)
        elif choice == "3":
            for video in engine.get_video_list():
                print(f" - {video['video_id']} | {video['title']}")
            continue
        elif choice == "4":
            break
        else:
            continue
        if "error" in results:
            print(results["error"])
        else:
            for index, result in enumerate(results["results"], 1):
                print(f"\n{index}. {result['video_title']}")
                print(f"   Time: {format_time(result['start_time'])} - {format_time(result['end_time'])}")
                print(f"   URL: {result['youtube_url']}")
                print(f"   Text: {result['text'][:200]}...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_pipeline", action="store_true")
    args = parser.parse_args()
    if args.run_pipeline:
        subprocess.run([sys.executable, "run_pipeline.py"], check=True)
    interactive_search()
