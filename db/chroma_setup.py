import logging
import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "youtube-semantic-search")
PERSIST_DIRECTORY = Path(os.getenv("CHROMA_PERSIST_DIRECTORY", "data/chroma"))


def get_chroma_client():
    """Create a Chroma client whose data survives process restarts."""
    PERSIST_DIRECTORY.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(PERSIST_DIRECTORY))


def get_chroma_collection():
    """Return the cosine-distance collection, creating it when needed."""
    collection = get_chroma_client().get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    logger.info("ChromaDB collection ready: %s", COLLECTION_NAME)
    return collection


if __name__ == "__main__":
    get_chroma_collection()
