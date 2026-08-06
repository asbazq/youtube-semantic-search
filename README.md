# 🎥 YouTube Semantic Search Engine

An intelligent, Python-based search engine that lets you semantically search through YouTube video transcripts. Built using yt-dlp, SentenceTransformers, ChromaDB, and Gradio.

---

## 🚀 Features

- ✅ Fetch YouTube captions using yt-dlp
- ✅ Preprocess captions into timestamped semantic chunks
- ✅ Generate embeddings using all-mpnet-base-v2
- ✅ Store and query vectors in ChromaDB
- ✅ Command-Line Interface to:
  - Process and embed new videos
  - Search video transcripts semantically
  - List uploaded videos
- ✅ Gradio UI for web-based exploration (optional)

---

## 🧠 How It Works

![image](https://github.com/user-attachments/assets/f459959e-cc4a-4dd8-a96a-f650ba950ec6)
---

## 📁 Project Structure

```
├── main.py                     # Pipeline
├── scripts/
│   ├── fetch_captions.py       # Fetch captions using yt-dlp
│   ├── preprocess_captions.py  # Clean and chunk transcripts
│   └── embed_chunks.py         # Generate embeddings
├── db/
│   ├── chroma_setup.py         # ChromaDB setup
│   └── upload_embeddings.py    # Upload to ChromaDB
├── search/
│   ├── semantic_search.py      # Search engine logic
├── data/
    ├── captions/               # Raw transcripts
    ├── chunks/                 # Preprocessed chunks
    └── embeddings/             # Final JSON embeddings
```

---

## 🛠️ Installation

```bash
git clone https://github.com/yourusername/youtube-semantic-search.git
cd youtube-semantic-search

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
```

## 🔐 Environment Setup

Create a `.env` file in the root directory:

```env
CHROMA_PERSIST_DIRECTORY=data/chroma
CHROMA_COLLECTION=youtube-semantic-search
# Optional: use a signed-in browser if YouTube returns HTTP 429
YTDLP_COOKIES_FROM_BROWSER=edge
```

## 💻 Usage (CLI)

```bash
python main.py
```

Options:
- `1`: Process and upload a new video
- `2`: View uploaded videos
- `3`: Exit

## 🌐 Web UI (Gradio - Optional)

Coming soon in `app.py`:
- Drag-and-drop YouTube processing
- Query with real-time results
- Stylish Gradio interface

## 📚 Example Output

```
📊 Found 3 result(s):

1. 🎬 Video: Intro to AI
   ⏰ Time: 00:10 - 00:20
   🔗 URL: https://youtube.com/watch?v=abc123&t=10s
   📝 Text: In this video, we explore how artificial intelligence works...
```

## 🧠 Technologies Used

- Python 3.10+
- `yt-dlp`
- `sentence-transformers`
- `chromadb`
- `Gradio` (for web UI)
- `dotenv`, `json`, `subprocess`, `os`, `pathlib`


## 📄 License
This project is licensed under the MIT License. See `LICENSE` for more details.
