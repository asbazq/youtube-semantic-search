"""임베딩 JSON을 읽어 ChromaDB에 저장하는 스크립트."""

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
VIDEO_TITLE_OVERRIDES = {
    "CsoReWY0zPo": "데드리프트 가벼워지는 시작 자세(구독자 자세 체크)",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def extract_video_info_from_filename(filename: str):
    """파일명 ``processed_제목_영상ID.json``에서 제목과 ID를 분리한다."""
    name_part = filename.replace("processed_", "").replace(".json", "")
    # YouTube ID는 항상 11자이며 ID 자체에도 밑줄이 들어갈 수 있다. 따라서
    # 단순 rsplit("_", 1)을 사용하면 5Z9d_BdnjF0 같은 ID가 잘릴 수 있다.
    if len(name_part) >= 12 and name_part[-12] == "_":
        title = name_part[:-12]
        video_id = name_part[-11:]
        return title.replace("_", " "), video_id

    # YouTube ID가 아닌 이전 데이터와의 호환을 위한 fallback이다.
    parts = name_part.rsplit("_", 1)
    if len(parts) == 2:
        title, video_id = parts
        return title.replace("_", " "), video_id
    return name_part.replace("_", " "), "unknown"


def prepare_chunks_for_chroma(
    chunks: List[Dict], video_title: str, video_id: str, filename: str
):
    """청크 리스트를 ChromaDB 저장용 레코드 리스트로 변환한다.

    한 레코드는 세 부분으로 구성된다:
    ``id``는 레코드 고유 이름, ``embedding``은 검색에 쓰는 숫자 리스트,
    ``metadata``는 검색 결과 화면에 보여 줄 자막·영상·시간 정보다.
    """
    records = []
    video_title = VIDEO_TITLE_OVERRIDES.get(video_id, video_title)
    # enumerate는 (0, 첫 항목), (1, 둘째 항목)처럼 번호와 값을 함께 준다.
    for index, chunk in enumerate(chunks):
        try:
            display_text = chunk["text"].rstrip().rstrip(".")
            display_start = chunk["start"]
            display_end = chunk["end"]

            # 현재 청크가 "겁니다" 같은 앞 문장의 끝부분에서 시작하면 이전
            # 청크의 고유한 자막 두 줄을 앞에 덧붙여 시작 문맥도 보존한다.
            if index > 0:
                preceding_blocks = [
                    block
                    for block in chunks[index - 1].get("blocks", [])
                    if block.get("end", 0) <= chunk["start"]
                ][-2:]
                if preceding_blocks:
                    display_text = " ".join(
                        [*(block["text"] for block in preceding_blocks), display_text]
                    ).strip()
                    display_start = preceding_blocks[0]["start"]

            # 임베딩은 현재 청크만 사용하되 화면에는 다음 자막 두 줄을 더 보여
            # 문장 중간에서 결과 미리보기가 끊기는 현상을 줄인다. 다음 청크의
            # 첫 block은 overlap으로 현재 청크와 같을 수 있어 종료 시각 이후의
            # block만 고른다.
            if index + 1 < len(chunks):
                following_blocks = [
                    block
                    for block in chunks[index + 1].get("blocks", [])
                    if block.get("start", 0) >= chunk["end"]
                ][:2]
                if following_blocks:
                    display_text = " ".join(
                        [display_text, *(block["text"] for block in following_blocks)]
                    ).strip()
                    display_end = following_blocks[-1]["end"]
            if display_text and display_text[-1] not in ".!?。！？":
                display_text += "."

            metadata = {
                "video_id": video_id,
                "video_title": video_title,
                "chunk_index": index,
                "text": display_text,
                "start_time": display_start,
                "end_time": display_end,
                "duration": display_end - display_start,
                "source_file": filename,
            }
            # append는 리스트 끝에 새 dict 하나를 추가한다.
            records.append(
                {
                    # :04d는 숫자 3을 "0003"처럼 네 자리 문자열로 만든다.
                    "id": f"{video_id}_{index:04d}",
                    "embedding": chunk["embedding"],
                    "metadata": metadata,
                }
            )
        except KeyError as error:
            logger.error("Missing key in chunk %s: %s", index, error)
    return records


def upload_file_to_chroma(collection, filepath: Path):
    """임베딩 파일 하나를 읽고 최대 BATCH_SIZE개씩 DB에 저장한다.

    ``collection``은 ChromaDB 컬렉션 객체이고 ``filepath``는 읽을 JSON 경로다.
    반환값은 저장을 시도한 레코드 개수이며, 오류가 발생하면 0이다.
    """
    try:
        logger.info("Processing %s", filepath.name)
        with filepath.open("r", encoding="utf-8") as file:
            chunks = json.load(file)
        if not chunks:
            logger.warning("No chunks found in %s", filepath.name)
            return 0

        video_title, video_id = extract_video_info_from_filename(filepath.name)
        records = prepare_chunks_for_chroma(chunks, video_title, video_id, filepath.name)

        # 같은 영상의 기존 벡터를 먼저 제거한다. 단순 upsert만 하면 새 청크 수가
        # 줄었을 때 예전 청크가 DB에 남아 잘못된 검색 결과를 낼 수 있다.
        # source_file로 찾으면 과거의 잘못된 video_id로 저장된 레코드도 교체된다.
        existing = collection.get(where={"source_file": {"$eq": filepath.name}})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
            logger.info(
                "Replaced %s existing vectors for video %s",
                len(existing["ids"]),
                video_id,
            )

        # range(시작, 끝, 간격): 0, 100, 200 ... 순서로 반복한다.
        for offset in range(0, len(records), BATCH_SIZE):
            # offset=100이면 records[100:200], 즉 두 번째 100개를 선택한다.
            batch = records[offset : offset + BATCH_SIZE]
            # upsert = 같은 id가 있으면 갱신(update), 없으면 삽입(insert).
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
    """data/embeddings 폴더에 있는 모든 JSON 파일을 업로드한다."""
    collection = get_chroma_collection()
    embedding_files = sorted(EMBEDDINGS_DIR.glob("*.json"))
    if not embedding_files:
        logger.error("No embedding files found in %s", EMBEDDINGS_DIR)
        return

    initial_count = collection.count()
    # generator expression으로 각 반환값(업로드 개수)을 더한다.
    uploaded = sum(upload_file_to_chroma(collection, file) for file in embedding_files)
    final_count = collection.count()
    logger.info("Vectors processed this session: %s", uploaded)
    logger.info("Total vectors in collection: %s (net change: %s)", final_count, final_count - initial_count)


def check_collection_status():
    """현재 저장 개수와 샘플 레코드 하나를 로그로 보여 준다."""
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
    # argparse는 ``--check``, ``--file`` 같은 터미널 옵션을 해석한다.
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
