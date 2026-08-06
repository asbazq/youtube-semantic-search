"""ChromaDB의 저장 위치와 컬렉션 생성을 담당하는 모듈."""

import logging
import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# .env 파일의 값을 os.environ에 불러온다. 값이 없으면 두 번째 인자를 기본값으로 쓴다.
load_dotenv()
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "youtube-semantic-search")
PERSIST_DIRECTORY = Path(os.getenv("CHROMA_PERSIST_DIRECTORY", "data/chroma"))


def get_chroma_client():
    """프로그램 종료 뒤에도 데이터가 남는 ChromaDB 클라이언트를 만든다."""
    # parents=True는 상위 폴더도 만들고, exist_ok=True는 이미 있어도 오류를 내지 않는다.
    PERSIST_DIRECTORY.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(PERSIST_DIRECTORY))


def get_chroma_collection():
    """컬렉션을 가져오고, 아직 없다면 새로 만든다.

    컬렉션은 관계형 DB의 테이블과 비슷하며 여러 벡터 레코드를 보관한다.
    cosine은 두 벡터가 가리키는 방향이 얼마나 비슷한지 비교하는 방식이다.
    """
    collection = get_chroma_client().get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    logger.info("ChromaDB collection ready: %s", COLLECTION_NAME)
    return collection


if __name__ == "__main__":
    get_chroma_collection()
