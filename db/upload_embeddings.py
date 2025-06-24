# import json
# import logging
# from pathlib import Path
# from typing import List, Dict
# import sys
# import os
# import concurrent.futures

# # Add parent directory to path to import pinecone_setup
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# from db.pinecone_setup import get_pinecone_client, get_pinecone_index

# # --- Configurations ---
# EMBEDDINGS_DIR = Path("data/embeddings")
# BATCH_SIZE = 100
# NAMESPACE = "youtube-semantic-search"
# MAX_WORKERS = 4

# # --- Logging Setup ---
# logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
# logger = logging.getLogger(__name__)

# def extract_video_info_from_filename(filename: str):
#     try:
#         name_part = filename.replace('processed_', '').replace('.json', '')
#         parts = name_part.rsplit('_', 1)
#         if len(parts) == 2:
#             title, video_id = parts
#             return title.replace('_', ' '), video_id
#         else:
#             return name_part.replace('_', ' '), "unknown"
#     except Exception as e:
#         logger.warning(f"⚠️ Could not parse filename {filename}: {e}")
#         return "Unknown Title", "unknown"

# def prepare_chunks_for_pinecone(chunks: List[Dict], video_title: str, video_id: str, filename: str):
#     pinecone_vectors = []
#     for i, chunk in enumerate(chunks):
#         try:
#             chunk_id = f"{video_id}_{i:04d}"
#             metadata = {
#                 "video_id": video_id,
#                 "video_title": video_title,
#                 "chunk_index": i,
#                 "text": chunk["text"],
#                 "start_time": chunk["start"],
#                 "end_time": chunk["end"],
#                 "duration": chunk["duration"],
#                 "source_file": filename
#             }
#             vector_data = {
#                 "id": chunk_id,
#                 "values": chunk["embedding"],
#                 "metadata": metadata
#             }
#             pinecone_vectors.append(vector_data)
#         except KeyError as e:
#             logger.error(f"❌ Missing key in chunk {i}: {e}")
#         except Exception as e:
#             logger.error(f"❌ Error processing chunk {i}: {e}")
#     return pinecone_vectors

# def upload_file_to_pinecone(index, filepath: Path):
#     try:
#         logger.info(f"🔄 Processing {filepath.name}...")
#         with open(filepath, 'r', encoding='utf-8') as f:
#             chunks = json.load(f)
#         if not chunks:
#             logger.warning(f"⚠️ No chunks found in {filepath.name}")
#             return 0

#         video_title, video_id = extract_video_info_from_filename(filepath.name)
#         pinecone_vectors = prepare_chunks_for_pinecone(chunks, video_title, video_id, filepath.name)
#         if not pinecone_vectors:
#             logger.warning(f"⚠️ No valid vectors prepared from {filepath.name}")
#             return 0

#         uploaded_count = 0
#         for i in range(0, len(pinecone_vectors), BATCH_SIZE):
#             batch = pinecone_vectors[i:i + BATCH_SIZE]
#             try:
#                 index.upsert(vectors=batch, namespace=NAMESPACE)
#                 uploaded_count += len(batch)
#                 logger.info(f"✅ Uploaded batch {i//BATCH_SIZE + 1}: {len(batch)} vectors")
#             except Exception as e:
#                 logger.error(f"❌ Failed to upload batch {i//BATCH_SIZE + 1}: {e}")

#         logger.info(f"🎯 Completed {filepath.name}: {uploaded_count}/{len(pinecone_vectors)} vectors uploaded")
#         return uploaded_count

#     except Exception as e:
#         logger.error(f"❌ Error processing {filepath}: {e}")
#         return 0

# def upload_all_embeddings():
#     try:
#         pc = get_pinecone_client()
#         index = get_pinecone_index()
#         embedding_files = list(EMBEDDINGS_DIR.glob("*.json"))

#         if not embedding_files:
#             logger.error(f"❌ No embedding files found in {EMBEDDINGS_DIR}")
#             return

#         logger.info(f"🚀 Found {len(embedding_files)} embedding files to upload")

#         initial_stats = index.describe_index_stats(namespace=NAMESPACE)
#         initial_count = initial_stats.get('total_vector_count', 0)
#         logger.info(f"📊 Current index has {initial_count} vectors in namespace '{NAMESPACE}'")

#         total_uploaded = 0
#         with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
#             futures = [executor.submit(upload_file_to_pinecone, index, file) for file in embedding_files]
#             for future in concurrent.futures.as_completed(futures):
#                 result = future.result()
#                 total_uploaded += result

#         final_stats = index.describe_index_stats(namespace=NAMESPACE)
#         final_count = final_stats.get('total_vector_count', 0)

#         logger.info(f"🎉 Upload complete!")
#         logger.info(f"📊 Vectors uploaded this session: {total_uploaded}")
#         logger.info(f"📊 Total vectors in index: {final_count}")
#         logger.info(f"📊 Net increase: {final_count - initial_count}")

#     except Exception as e:
#         logger.error(f"❌ Upload failed: {e}")

# def check_index_status():
#     try:
#         pc = get_pinecone_client()
#         index = get_pinecone_index()
#         stats = index.describe_index_stats(namespace=NAMESPACE)

#         logger.info(f"📊 Index Status for namespace '{NAMESPACE}':")
#         logger.info(f"   Total vectors: {stats['total_vector_count']}")
#         logger.info(f"   Index fullness: {stats.get('index_fullness', 'N/A')}")

#         if stats['total_vector_count'] > 0:
#             sample_query = index.query(
#                 vector=[0.1] * 768,
#                 top_k=1,
#                 include_metadata=True,
#                 namespace=NAMESPACE
#             )
#             if sample_query['matches']:
#                 sample_match = sample_query['matches'][0]
#                 logger.info(f"📋 Sample record:")
#                 logger.info(f"   ID: {sample_match['id']}")
#                 logger.info(f"   Video: {sample_match['metadata'].get('video_title', 'Unknown')}")
#                 logger.info(f"   Text preview: {sample_match['metadata'].get('text', '')[:100]}...")

#     except Exception as e:
#         logger.error(f"❌ Status check failed: {e}")

# if __name__ == "__main__":
#     import argparse

#     parser = argparse.ArgumentParser(description="Upload embeddings to Pinecone")
#     parser.add_argument("--check", action="store_true", help="Check index status only")
#     args = parser.parse_args()

#     if args.check:
#         check_index_status()
#     else:
#         upload_all_embeddings()

import json
import logging
from pathlib import Path
from typing import List, Dict
import sys
import os
import concurrent.futures

# Add parent directory to path to import pinecone_setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.pinecone_setup import get_pinecone_client, get_pinecone_index

# --- Configurations ---
EMBEDDINGS_DIR = Path("data/embeddings")
BATCH_SIZE = 100
NAMESPACE = "youtube-semantic-search"
MAX_WORKERS = 4

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

def extract_video_info_from_filename(filename: str):
    try:
        name_part = filename.replace('processed_', '').replace('.json', '')
        parts = name_part.rsplit('_', 1)
        if len(parts) == 2:
            title, video_id = parts
            return title.replace('_', ' '), video_id
        else:
            return name_part.replace('_', ' '), "unknown"
    except Exception as e:
        logger.warning(f"⚠️ Could not parse filename {filename}: {e}")
        return "Unknown Title", "unknown"

def prepare_chunks_for_pinecone(chunks: List[Dict], video_title: str, video_id: str, filename: str):
    pinecone_vectors = []
    for i, chunk in enumerate(chunks):
        try:
            chunk_id = f"{video_id}_{i:04d}"
            metadata = {
                "video_id": video_id,
                "video_title": video_title,
                "chunk_index": i,
                "text": chunk["text"],
                "start_time": chunk["start"],
                "end_time": chunk["end"],
                "duration": chunk["duration"],
                "source_file": filename
            }
            vector_data = {
                "id": chunk_id,
                "values": chunk["embedding"],
                "metadata": metadata
            }
            pinecone_vectors.append(vector_data)
        except KeyError as e:
            logger.error(f"❌ Missing key in chunk {i}: {e}")
        except Exception as e:
            logger.error(f"❌ Error processing chunk {i}: {e}")
    return pinecone_vectors

def upload_file_to_pinecone(index, filepath: Path):
    try:
        logger.info(f"🔄 Processing {filepath.name}...")
        with open(filepath, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        if not chunks:
            logger.warning(f"⚠️ No chunks found in {filepath.name}")
            return 0

        video_title, video_id = extract_video_info_from_filename(filepath.name)
        pinecone_vectors = prepare_chunks_for_pinecone(chunks, video_title, video_id, filepath.name)
        if not pinecone_vectors:
            logger.warning(f"⚠️ No valid vectors prepared from {filepath.name}")
            return 0

        uploaded_count = 0
        for i in range(0, len(pinecone_vectors), BATCH_SIZE):
            batch = pinecone_vectors[i:i + BATCH_SIZE]
            try:
                index.upsert(vectors=batch, namespace=NAMESPACE)
                uploaded_count += len(batch)
                logger.info(f"✅ Uploaded batch {i//BATCH_SIZE + 1}: {len(batch)} vectors")
            except Exception as e:
                logger.error(f"❌ Failed to upload batch {i//BATCH_SIZE + 1}: {e}")

        logger.info(f"🎯 Completed {filepath.name}: {uploaded_count}/{len(pinecone_vectors)} vectors uploaded")
        return uploaded_count

    except Exception as e:
        logger.error(f"❌ Error processing {filepath}: {e}")
        return 0

def upload_all_embeddings():
    try:
        pc = get_pinecone_client()
        index = get_pinecone_index()
        embedding_files = list(EMBEDDINGS_DIR.glob("*.json"))

        if not embedding_files:
            logger.error(f"❌ No embedding files found in {EMBEDDINGS_DIR}")
            return

        logger.info(f"🚀 Found {len(embedding_files)} embedding files to upload")

        initial_stats = index.describe_index_stats(namespace=NAMESPACE)
        initial_count = initial_stats.get('total_vector_count', 0)
        logger.info(f"📊 Current index has {initial_count} vectors in namespace '{NAMESPACE}'")

        total_uploaded = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(upload_file_to_pinecone, index, file) for file in embedding_files]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                total_uploaded += result

        final_stats = index.describe_index_stats(namespace=NAMESPACE)
        final_count = final_stats.get('total_vector_count', 0)

        logger.info(f"🎉 Upload complete!")
        logger.info(f"📊 Vectors uploaded this session: {total_uploaded}")
        logger.info(f"📊 Total vectors in index: {final_count}")
        logger.info(f"📊 Net increase: {final_count - initial_count}")

    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")

def check_index_status():
    try:
        pc = get_pinecone_client()
        index = get_pinecone_index()
        stats = index.describe_index_stats(namespace=NAMESPACE)

        logger.info(f"📊 Index Status for namespace '{NAMESPACE}':")
        logger.info(f"   Total vectors: {stats['total_vector_count']}")
        logger.info(f"   Index fullness: {stats.get('index_fullness', 'N/A')}")

        if stats['total_vector_count'] > 0:
            sample_query = index.query(
                vector=[0.1] * 768,
                top_k=1,
                include_metadata=True,
                namespace=NAMESPACE
            )
            if sample_query['matches']:
                sample_match = sample_query['matches'][0]
                logger.info(f"📋 Sample record:")
                logger.info(f"   ID: {sample_match['id']}")
                logger.info(f"   Video: {sample_match['metadata'].get('video_title', 'Unknown')}")
                logger.info(f"   Text preview: {sample_match['metadata'].get('text', '')[:100]}...")

    except Exception as e:
        logger.error(f"❌ Status check failed: {e}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Upload embeddings to Pinecone")
    parser.add_argument("--check", action="store_true", help="Check index status only")
    parser.add_argument("--file", type=str, help="Path to a specific embeddings file to upload")
    args = parser.parse_args()

    if args.check:
        check_index_status()
    elif args.file:
        pc = get_pinecone_client()
        index = get_pinecone_index()
        upload_file_to_pinecone(index, Path(args.file))
    else:
        upload_all_embeddings()

