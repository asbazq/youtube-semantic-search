# 🦏 Rhino Strength YouTube Search

라이노스트렝스 YouTube 영상의 자막에서 운동 동작과 코칭 내용을 자연어로
찾아주는 검색 서비스입니다. yt-dlp, PyTorch, Hugging Face Transformers, ChromaDB, Vue를
사용합니다.

---

## 🚀 Features

- ✅ yt-dlp를 사용해 유튜브 자막 가져오기
- ✅ 캡션을 타임스탬프가 포함된 의미 단위로 전처리합니다
- ✅ paraphrase-multilingual-mpnet-base-v2를 사용해 한국어 및 다국어 임베딩을 생성합니다
- ✅ ChromaDB에 벡터를 저장하고 조회하기
- ✅ 명령어 인터페이스:
  - 새 동영상 처리 및 임베드하기
  - 비디오 대본을 의미적으로 검색하기
  - 업로드된 동영상 목록
- ✅ 웹 기반 탐색을 위한 Gradio UI (선택 사항)

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
ADMIN_USERNAME=user_name
ADMIN_PASSWORD=충분히-긴-관리자-비밀번호
# Optional: use a signed-in browser if YouTube returns HTTP 429
YTDLP_COOKIES_FROM_BROWSER=edge
```

`ADMIN_USERNAME`과 `ADMIN_PASSWORD`를 설정해야 웹 화면에서 ADMIN으로 로그인해
영상을 추가하거나 삭제할 수 있습니다. 비밀번호가 포함된 `.env` 파일은 Git에
커밋하지 마세요.

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

이전 `sentence-transformers` 구현에서 만든 데이터가 이미 있다면 새 정규화
방식으로 전체 벡터를 다시 만들고 ChromaDB에 업로드합니다.

```bash
python scripts/embed_chunks.py --overwrite
python db/upload_embeddings.py --all
```

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

### 로컬 모델 챗봇

챗봇은 기존 자막 검색 결과를 근거로 답하고 영상 시점 링크를 보여 줍니다.
답변 모델은 로컬 Ollama에서 실행합니다. 임베딩 모델도 기존처럼 로컬에서
실행되므로 외부 생성 AI API 키는 필요하지 않습니다.

Docker Compose로 실행할 때는 서버를 띄운 뒤 모델을 한 번 내려받습니다.

```bash
docker compose up -d --build
docker compose exec ollama ollama pull qwen2.5:1.5b
```

이후 웹 화면의 **영상에게 물어보세요** 영역에서 질문할 수 있습니다. 다른
모델을 사용하려면 `.env`에 `OLLAMA_MODEL=모델명`을 설정하고 같은 모델을
Ollama에 내려받으세요. Docker 없이 실행한다면 로컬 Ollama 서버를 켜고
`OLLAMA_BASE_URL`(기본값 `http://127.0.0.1:11434`)을 지정하면 됩니다.

대화 기록은 API 프로세스 메모리에 최대 200개 세션·세션당 최근 4회 대화만
보관하며 재시작하면 사라집니다. 출처 점수 기준은 `CHAT_MIN_SCORE`(기본 0.45)로
조정할 수 있습니다. 모델 설치 및 실행 방법과 패턴별 코드 위치는
[챗봇 학습 가이드](CHATBOT_STUDY.md)에 정리했습니다.

## 🐳 Docker Compose

루트의 `.env`에 최소한 관리자 비밀번호를 설정합니다.

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=충분히-긴-관리자-비밀번호
CHROMA_COLLECTION=youtube-semantic-search
```

이미지를 빌드하고 서비스를 실행합니다.

```bash
docker compose up -d --build
docker compose logs -f
```

브라우저에서 `http://localhost:18765`을 엽니다. 포트를 바꾸려면 `.env`에
`APP_PORT=원하는포트`를 추가합니다. 생성한 자막, 임베딩, ChromaDB 데이터는
호스트의 `data/`에 유지되며 모델 캐시는 Docker 볼륨에 저장됩니다.

```bash
docker compose down
```

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
- `torch`, `transformers`
- `chromadb`
- `Gradio` (for web UI)
- `dotenv`, `json`, `subprocess`, `os`, `pathlib`


## 📄 License
This project is licensed under the MIT License. See `LICENSE` for more details.
