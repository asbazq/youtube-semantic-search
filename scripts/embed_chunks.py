"""자막 청크의 문장을 의미를 표현하는 숫자 벡터로 변환한다.

컴퓨터는 문장을 직접 비교하기 어려우므로 SentenceTransformer 모델로 각 문장을
여러 실수의 리스트(embedding)로 바꾼다.
"""

import json
import logging
import argparse
from pathlib import Path
from sentence_transformers import SentenceTransformer

# --- Configuration ---
CHUNKS_DIR = Path("data/chunks")
EMBEDDINGS_DIR = Path("data/embeddings")
# 한국어를 포함한 여러 언어의 문장을 의미에 따라 비교할 수 있는 모델이다.
MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# --- Ensure output directory exists ---
EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

# 모델 로드는 비용이 크므로 파일 시작 시 한 번만 수행하고 모든 파일에서 재사용한다.
logger.info(f"📦 Loading embedding model: {MODEL_NAME}")
try:
    model = SentenceTransformer(MODEL_NAME)
    logger.info("✅ Model loaded successfully")
except Exception as e:
    logger.error(f"❌ Failed to load model {MODEL_NAME}: {e}")
    raise

# --- Function to embed a single chunk file ---
def embed_chunks_file(input_file: Path, output_file: Path):
    """
    입력 JSON의 청크를 읽고 임베딩을 추가해 출력 JSON으로 저장한다.

    Path는 문자열 경로보다 파일 경로 연산을 편리하게 해 주는 객체다.

    입력 청크 하나::

        {"text": "오늘은 파이썬을 배웁니다.", "start": 10.0, ...}

    출력 청크에는 ``"embedding": [0.012, -0.031, ...]``이 추가된다.
    벡터의 숫자 하나에 사람이 읽을 수 있는 고정 의미가 있는 것은 아니며,
    전체 숫자 배열 사이의 거리로 문장 의미가 가까운지를 비교한다.
    """
    try:
        logger.info(f"🔄 Embedding: {input_file.name}")
        with open(input_file, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        # Ensure chunks are in correct format
        if not isinstance(chunks, list):
            raise ValueError("Expected list of chunks")

        # 모델에는 텍스트만 전달하지만 결과를 원래 청크에 붙이기 위해 인덱스도 기억한다.
        texts = []
        valid_indices = []

        for i, chunk in enumerate(chunks):
            if "text" in chunk and isinstance(chunk["text"], str):
                texts.append(chunk["text"])
                valid_indices.append(i)
            else:
                logger.warning(f"⚠️ Skipping invalid chunk {i} (missing or invalid 'text')")

        if not texts:
            logger.warning(f"⚠️ No valid chunks to embed in: {input_file.name}")
            return

        # encode는 문장 목록을 2차원 숫자 배열로 바꾼다.
        # 입력 shape는 문장 N개의 리스트, 출력 shape는 (N, 벡터 차원)이다.
        # 같은 위치가 서로 대응한다: texts[0]의 결과는 embeddings[0]이다.
        embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

        for i, idx in enumerate(valid_indices):
            # NumPy 배열은 JSON 저장이 안 되므로 일반 Python list로 변환한다.
            chunks[idx]["embedding"] = embeddings[i].tolist()

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Saved embeddings to: {output_file.name}")

    except Exception as e:
        logger.error(f"❌ Failed to process {input_file.name}: {e}")

# --- Main driver function ---
def main(overwrite=False):
    """모든 청크 파일을 임베딩하되 최신 결과는 건너뛴다."""
    chunk_files = sorted(CHUNKS_DIR.glob("*.json"))

    if not chunk_files:
        logger.warning("⚠️ No chunk files found in data/chunks/")
        return

    logger.info(f"🚀 Found {len(chunk_files)} chunk files to process")

    embedded_count = 0
    skipped_count = 0

    for chunk_file in chunk_files:
        output_file = EMBEDDINGS_DIR / chunk_file.name

        # 출력 수정 시간이 입력보다 최신이면 이미 최신 결과라는 뜻이다.
        if output_file.exists() and not overwrite:
            if output_file.stat().st_mtime >= chunk_file.stat().st_mtime:
                logger.info(f"⏩ Skipping (already embedded): {chunk_file.name}")
                skipped_count += 1
                continue
            logger.info(f"🔄 Re-embedding updated chunks: {chunk_file.name}")

        embed_chunks_file(chunk_file, output_file)
        embedded_count += 1

    # --- Summary ---
    logger.info("\n🎯 Embedding Summary:")
    logger.info(f"🆕 Embedded files: {embedded_count}")
    logger.info(f"⏭️ Skipped files : {skipped_count}")
    logger.info("✅ Embedding complete!")

# --- CLI entry ---
if __name__ == "__main__":
    # --overwrite를 주면 기존 결과의 수정 시간과 관계없이 다시 만든다.
    parser = argparse.ArgumentParser(description="Embed caption chunks using SentenceTransformer (SBERT)")
    parser.add_argument("--overwrite", action="store_true", help="Force overwrite existing embedding files")
    args = parser.parse_args()

    main(overwrite=args.overwrite)
