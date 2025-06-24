import os
import logging
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec, PineconeException

# --- Logging setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# --- Load environment variables ---
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = "youtube-semantic-search"
DIMENSION = 768  # Adjust to your model's dimension
SERVERLESS_CLOUD = "aws"
SERVERLESS_REGION = "us-east-1"

# --- Function to get Pinecone client ---
def get_pinecone_client():
    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        logger.info("✅ Pinecone client initialized")
        return pc
    except PineconeException as e:
        logger.error(f"❌ Pinecone error: {type(e).__name__}: {e}")
        raise
    except Exception as e:
        logger.error(f"🔥 Unexpected error: {type(e).__name__}: {e}")
        raise

# --- Function to get or create index ---
def get_pinecone_index():
    pc = get_pinecone_client()
    try:
        index_names = pc.list_indexes().names()

        if INDEX_NAME not in index_names:
            logger.info(f"🆕 Creating index '{INDEX_NAME}' with dimension {DIMENSION}")
            pc.create_index(
                name=INDEX_NAME,
                dimension=DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(cloud=SERVERLESS_CLOUD, region=SERVERLESS_REGION)
            )
            logger.info(f"✅ Created index: {INDEX_NAME}")
        else:
            logger.info(f"📌 Index '{INDEX_NAME}' already exists")

        return pc.Index(INDEX_NAME)
    except PineconeException as e:
        logger.error(f"❌ Pinecone error while accessing index: {type(e).__name__}: {e}")
        raise
    except Exception as e:
        logger.error(f"🔥 Unexpected error while accessing index: {type(e).__name__}: {e}")
        raise

# --- Optional run block (only for manual script execution) ---
if __name__ == "__main__":
    try:
        get_pinecone_index()
    except Exception:
        logger.error("❌ Failed to initialize Pinecone setup")
