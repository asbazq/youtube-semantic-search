import json
import logging
import argparse
from pathlib import Path
from sentence_transformers import SentenceTransformer

# --- Configuration ---
CHUNKS_DIR = Path("data/chunks")
EMBEDDINGS_DIR = Path("data/embeddings")
MODEL_NAME = "all-mpnet-base-v2"

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# --- Ensure output directory exists ---
EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

# --- Load embedding model ---
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
    Load chunks from input_file, generate embeddings using SBERT,
    and write the output to output_file with embeddings attached.
    """
    try:
        logger.info(f"🔄 Embedding: {input_file.name}")
        with open(input_file, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        # Ensure chunks are in correct format
        if not isinstance(chunks, list):
            raise ValueError("Expected list of chunks")

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

        embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

        for i, idx in enumerate(valid_indices):
            chunks[idx]["embedding"] = embeddings[i].tolist()

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Saved embeddings to: {output_file.name}")

    except Exception as e:
        logger.error(f"❌ Failed to process {input_file.name}: {e}")

# --- Main driver function ---
def main(overwrite=False):
    chunk_files = sorted(CHUNKS_DIR.glob("*.json"))

    if not chunk_files:
        logger.warning("⚠️ No chunk files found in data/chunks/")
        return

    logger.info(f"🚀 Found {len(chunk_files)} chunk files to process")

    embedded_count = 0
    skipped_count = 0

    for chunk_file in chunk_files:
        output_file = EMBEDDINGS_DIR / chunk_file.name

        if output_file.exists() and not overwrite:
            logger.info(f"⏩ Skipping (already embedded): {chunk_file.name}")
            skipped_count += 1
            continue

        embed_chunks_file(chunk_file, output_file)
        embedded_count += 1

    # --- Summary ---
    logger.info("\n🎯 Embedding Summary:")
    logger.info(f"🆕 Embedded files: {embedded_count}")
    logger.info(f"⏭️ Skipped files : {skipped_count}")
    logger.info("✅ Embedding complete!")

# --- CLI entry ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Embed caption chunks using SentenceTransformer (SBERT)")
    parser.add_argument("--overwrite", action="store_true", help="Force overwrite existing embedding files")
    args = parser.parse_args()

    main(overwrite=args.overwrite)
