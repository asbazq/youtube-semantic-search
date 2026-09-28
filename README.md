# 🦏 Rhino Strength YouTube Search

라이노스트렝스 YouTube 영상의 자막에서 운동 동작과 코칭 내용을 자연어로
찾아주는 검색 서비스입니다. yt-dlp, SentenceTransformers, ChromaDB, Vue를
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

## 🧰 트러블슈팅

### 검색 결과가 없거나 관련 없는 영상 구간이 나올 때

자막은 `scripts/preprocess_captions.py`에서 다음 기준으로 청크로 묶습니다.

| 단계 | 현재 기준 | 검색에 미치는 영향 |
| --- | --- | --- |
| 인접 자막 결합 | 간격 0.5초 이하 | 짧게 끊긴 자동 자막을 한 발화로 합침 |
| 긴 발화 분할 | 30초 초과 또는 80단어 초과 시 분할; 문장 경계를 우선 사용 | 문장 경계를 못 찾으면 40단어씩 나누고 시점은 길이에 비례해 추정 |
| 검색 청크 구성 | 약 25단어 목표, 다음 문장을 더하면 50단어를 넘을 때 문장 경계에서 분리 | 문장 블록을 중간에서 자르거나 앞 청크와 겹치지 않음 |
| 짧은 청크 병합 | 10단어 미만 또는 3초 미만이며 이웃 청크와 간격이 3초 이하 | 지나치게 짧은 구간을 합침 |

25·50단어는 글자 수나 모델 토큰 수가 아닌 **공백으로 나눈 단어 수**입니다.
긴 문장 블록을 보존하거나 짧은 청크를 나중에 합치면 최종 청크가 50단어를
넘을 수 있습니다. 청크가 너무 짧으면 질문의 맥락이 빠지고, 너무 길면 다른
내용이 섞여 검색 정확도와 영상 시점 링크가 흐려질 수 있습니다.

청킹 기준을 코드에서 변경했다면 **기존 데이터에는 자동 반영되지 않습니다.**
저장된 자막을 다시 처리하고 임베딩과 ChromaDB 인덱스를 갱신하세요.
Docker Compose 환경에서는 다음 순서로 실행합니다. `--overwrite`는 모든
등록 자막을 다시 계산하므로 데이터가 많으면 시간이 걸립니다.

```bash
docker compose exec backend python scripts/preprocess_captions.py --overwrite
docker compose exec backend python scripts/embed_chunks.py --overwrite
docker compose exec backend python db/upload_embeddings.py --all
```

검색 화면은 점수가 낮아도 후보를 일부 보여 줄 수 있습니다. 챗봇은 검색된
후보 중 유사도 `CHAT_MIN_SCORE`(기본 `0.45`) 이상인 자막만 근거로 씁니다.
따라서 검색 결과가 보이는데 챗봇이 “관련 자막에서 답을 확인하지 못했습니다”라고
답할 수 있습니다. 먼저 영상 선택 범위와 실제 자막 내용을 확인하세요.
`CHAT_MIN_SCORE`를 낮추면 근거가 늘지만 관련성이 낮은 자막도 포함될 수 있습니다.

### “답변 중…”이 오래 지속될 때

Ollama 호출에는 검색어 생성 **최대 128토큰**, 답변 생성 **최대 512토큰**의
`num_predict` 제한과 `repeat_penalty=1.1`을 적용합니다. 생성량 제한은
응답 시간을 줄이고 같은 문장을 반복하다 JSON이 잘리는 현상을 줄이기 위한
것이며 답변 품질을 보장하는 값은 아닙니다. Ollama HTTP 호출은 회당 120초,
브라우저 요청은 180초가 지나면 중단됩니다. 모델이 느리거나 다른 요청을
처리 중이면 기다리는 시간이 길어질 수 있습니다.

```bash
docker compose ps
docker compose logs --tail=100 backend ollama
```

Ollama가 실행 중인지와 모델이 설치됐는지 확인하세요. 모델 이름은
`.env`의 `OLLAMA_MODEL`(기본 `qwen2.5:1.5b`)과 같아야 합니다.

```bash
docker compose exec ollama ollama list
docker compose exec ollama ollama pull qwen2.5:1.5b
```

### “모델 응답 형식을 확인할 수 없습니다” 또는 자막 원문이 보일 때

작은 모델은 반복 문장을 생성해 JSON을 끝내지 못하거나 존재하지 않는 출처
번호를 돌려줄 수 있습니다. 서버는 모델 출력을 검증하고 한 번 더 형식 수정을
요청합니다. 두 번 모두 실패하면 검증되지 않은 문장 대신 **검색된 자막 원문**을
명시해서 보여 주며, 아래 영상 시점 링크로 원문을 확인할 수 있습니다. 이때
반환된 내용은 AI가 정리한 답변이 아닙니다. 같은 현상이 반복되면 `backend`와
`ollama` 로그를 확인하고 질문을 더 구체적으로 바꿔 보세요.

### 설정을 바꿨는데 반영되지 않거나 관리자 로그인이 안 될 때

`.env`의 `ADMIN_USERNAME`·`ADMIN_PASSWORD`는 백엔드 컨테이너에 전달됩니다.
터미널에서 `echo "$ADMIN_PASSWORD"`가 비어 있어도 `.env` 값이 없는 것은
아닙니다. 로그인 401은 입력한 계정과 컨테이너 설정이 일치하지 않는다는
뜻입니다. `.env`에서 관리자 계정, `OLLAMA_MODEL`, `CHAT_MIN_SCORE`,
`APP_PORT` 등을 수정했다면 컨테이너를 다시 만드세요.

```bash
docker compose up -d --force-recreate backend frontend
```

비밀번호를 로그나 이슈에 붙여 넣지 마세요.

---

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
