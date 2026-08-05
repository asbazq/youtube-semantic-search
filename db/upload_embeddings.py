import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.chroma_setup import get_chroma_collection

EMBEDDINGS_DIR = Path("data/embeddings")
BATCH_SIZE = 100

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def extract_video_info_from_filename(filename: str):
    name_part = filename.replace("processed_", "").replace(".json", "")
    parts = name_part.rsplit("_", 1)
    if len(parts) == 2:
        title, video_id = parts
        return title.replace("_", " "), video_id
    return name_part.replace("_", " "), "unknown"


def prepare_chunks_for_chroma(
    chunks: List[Dict], video_title: str, video_id: str, filename: str
):
    records = []
    for index, chunk in enumerate(chunks):
        try:
            metadata = {
                "video_id": video_id,
                "video_title": video_title,
                "chunk_index": index,
                "text": chunk["text"],
                "start_time": chunk["start"],
                "end_time": chunk["end"],
                "duration": chunk["duration"],
                "source_file": filename,
            }
            records.append(
                {
                    "id": f"{video_id}_{index:04d}",
                    "embedding": chunk["embedding"],
                    "metadata": metadata,
                }
            )
        except KeyError as error:
            logger.error("Missing key in chunk %s: %s", index, error)
    return records


def upload_file_to_chroma(collection, filepath: Path):
    try:
        logger.info("Processing %s", filepath.name)
        with filepath.open("r", encoding="utf-8") as file:
            chunks = json.load(file)
        if not chunks:
            logger.warning("No chunks found in %s", filepath.name)
            return 0

        video_title, video_id = extract_video_info_from_filename(filepath.name)
        records = prepare_chunks_for_chroma(chunks, video_title, video_id, filepath.name)
        for offset in range(0, len(records), BATCH_SIZE):
            batch = records[offset : offset + BATCH_SIZE]
            collection.upsert(
                ids=[record["id"] for record in batch],
                embeddings=[record["embedding"] for record in batch],
                metadatas=[record["metadata"] for record in batch],
                documents=[record["metadata"]["text"] for record in batch],
            )
            logger.info("Uploaded batch %s: %s vectors", offset // BATCH_SIZE + 1, len(batch))
        return len(records)
    except Exception as error:
        logger.error("Error processing %s: %s", filepath, error)
        return 0


def upload_all_embeddings():
    collection = get_chroma_collection()
    embedding_files = sorted(EMBEDDINGS_DIR.glob("*.json"))
    if not embedding_files:
        logger.error("No embedding files found in %s", EMBEDDINGS_DIR)
        return

    initial_count = collection.count()
    uploaded = sum(upload_file_to_chroma(collection, file) for file in embedding_files)
    final_count = collection.count()
    logger.info("Vectors processed this session: %s", uploaded)
    logger.info("Total vectors in collection: %s (net change: %s)", final_count, final_count - initial_count)


def check_collection_status():
    collection = get_chroma_collection()
    total_count = collection.count()
    logger.info("Total vectors: %s", total_count)
    if total_count:
        sample = collection.get(limit=1, include=["metadatas", "documents"])
        metadata = sample["metadatas"][0]
        logger.info("Sample ID: %s", sample["ids"][0])
        logger.info("Video: %s", metadata.get("video_title", "Unknown"))
        logger.info("Text preview: %s...", metadata.get("text", "")[:100])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload embeddings to ChromaDB")
    parser.add_argument("--check", action="store_true", help="Check collection status only")
    parser.add_argument("--file", type=str, help="Upload one embeddings file")
    parser.add_argument("--all", action="store_true", help="Upload every embeddings file")
    args = parser.parse_args()

    if args.check:
        check_collection_status()
    elif args.file:
        upload_file_to_chroma(get_chroma_collection(), Path(args.file))
    else:
        upload_all_embeddings()
