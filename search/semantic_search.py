"""사용자의 검색어와 저장된 자막 벡터를 비교하는 검색 모듈."""

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

# 자막 벡터를 만들 때 사용한 모델과 반드시 같아야 한다.
MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"
MIN_SCORE = 0.3

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def format_time(seconds: int) -> str:
    """초 단위 숫자를 ``시:분:초`` 문자열로 바꾼다."""
    try:
        return str(timedelta(seconds=int(seconds)))
    except (TypeError, ValueError):
        return "00:00:00"


class YouTubeSemanticSearch:
    """임베딩 모델과 ChromaDB 컬렉션을 묶어 검색 기능을 제공하는 클래스.

    클래스는 데이터(self.model, self.collection)와 관련 함수(method)를 하나의
    객체에 묶는 문법이다. ``self``는 현재 만들어진 객체 자신을 뜻한다.
    """

    def __init__(self):
        """``YouTubeSemanticSearch()`` 객체 생성 직후 자동 실행되는 초기화 함수."""
        logger.info("Loading embedding model: %s", MODEL_NAME)
        self.model = SentenceTransformer(MODEL_NAME)
        self.collection = get_chroma_collection()

    def embed_query(self, query: str) -> Optional[List[float]]:
        """질문 문자열을 숫자 리스트로 변환한다. 실패하면 None을 반환한다."""
        if not query or not query.strip():
            logger.warning("Empty query provided")
            return None
        try:
            return self.model.encode([query.strip()], convert_to_numpy=True)[0].tolist()
        except Exception as error:
            logger.error("Embedding error for query '%s': %s", query, error)
            return None

    def _query(self, embedding: List[float], top_k: int, where=None):
        """ChromaDB에서 가까운 벡터를 찾아 (메타데이터, 점수) 목록으로 반환한다.

        이름 앞의 밑줄은 클래스 내부에서 주로 쓰는 메서드라는 관례다.
        """
        count = self.collection.count()
        if count == 0:
            return []
        response = self.collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, count),
            where=where,
            include=["metadatas", "distances"],
        )
        # dict.get(key, 기본값)은 키가 없을 때 KeyError 대신 기본값을 돌려준다.
        metadatas_list = response.get("metadatas") or [[]]
        distances_list = response.get("distances") or [[]]
        metadatas = metadatas_list[0] if metadatas_list else []
        distances = distances_list[0] if distances_list else []
        # zip은 같은 위치의 metadata와 distance를 한 쌍으로 묶는다.
        return [
            (metadata, 1.0 - distance)
            for metadata, distance in zip(metadatas, distances)
            if 1.0 - distance > MIN_SCORE
        ]

    def search(self, query: str, top_k: int = 10, include_metadata: bool = True) -> Dict[str, Any]:
        """모든 영상에서 검색하고 화면에 사용하기 쉬운 dict로 반환한다."""
        del include_metadata  # Metadata is required to build the public result objects.
        embedding = self.embed_query(query)
        if embedding is None:
            return {"error": "Failed to embed query"}
        try:
            matches = self._query(embedding, top_k)
            results = {"query": query, "total_found": len(matches), "results": []}
            for metadata, score in matches:
                raw_video_id = metadata.get("video_id", "")
                video_id = str(raw_video_id or "").split("&")[0]
                results["results"].append(self._result(metadata, score, video_id, include_duration=True))
            return results
        except Exception as error:
            logger.error("Search failed: %s", error)
            return {"error": str(error)}

    def search_by_video(self, query: str, video_id: str, top_k: int = 10) -> Dict[str, Any]:
        """where 조건으로 특정 영상의 자막만 검색한다."""
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
        """DB 검색 결과를 프로그램 공통 결과 형식으로 정리한다.

        staticmethod는 self가 필요 없는, 클래스와 관련된 보조 함수에 사용한다.
        """
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
        """DB 메타데이터에서 중복되지 않은 영상 ID와 제목 목록을 만든다."""
        try:
            stored = self.collection.get(include=["metadatas"])
            videos = {}
            for metadata in stored.get("metadatas", []):
                video_id = metadata.get("video_id", "")
                if video_id:
                    # setdefault는 키가 처음 나타났을 때만 값을 저장해 중복을 제거한다.
                    videos.setdefault(video_id, metadata.get("video_title", "Unknown"))
            return [{"video_id": video_id, "title": title} for video_id, title in videos.items()]
        except Exception as error:
            logger.error("Failed to get video list: %s", error)
            return []


def interactive_search():
    """search 모듈을 직접 실행했을 때 사용할 별도의 검색 메뉴."""
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
