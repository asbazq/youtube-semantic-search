# 🦏 Rhino Strength YouTube Search

라이노스트렝스 YouTube 영상의 자막에서 운동 동작과 코칭 내용을 자연어로
찾아주는 검색 서비스입니다. yt-dlp, SentenceTransformers, ChromaDB, Vue를
사용합니다.

---

## 🚀 Features

- ✅ Fetch YouTube captions using yt-dlp
- ✅ Preprocess captions into timestamped semantic chunks
- ✅ Generate Korean/multilingual embeddings using paraphrase-multilingual-mpnet-base-v2
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
- `1`: Process and upload one video
- `2`: Process and upload multiple videos
- `3`: Process every available video in a YouTube playlist
- `4`: Search across every uploaded video and print timestamp links
- `5`: View uploaded videos
- `6`: Exit

## 🌐 Vue Web UI

백엔드와 프론트엔드를 각각 실행합니다.

```bash
# terminal 1
uvicorn api:app --reload

# terminal 2
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:5173`을 열면 전체/영상별 의미 검색, 타임스탬프
이동, 새 영상 등록 기능을 사용할 수 있습니다. 임베딩 모델은 첫 API 요청 때 한 번
로드되므로 최초 요청에는 시간이 조금 걸릴 수 있습니다.

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
