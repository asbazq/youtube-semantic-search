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

챗봇은 질문과 관련된 자막 구절을 원문 그대로 보여 주고 영상 시점 링크를 제공합니다.
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
조정할 수 있습니다.

### 임베딩 저장과 재사용

| 대상 | 저장·재사용 방식 |
| --- | --- |
| 영상 자막 청크의 임베딩 | `scripts/embed_chunks.py`가 벡터를 `data/embeddings/*.json`에 저장하고, `db/upload_embeddings.py`가 검색용 ChromaDB(`data/chroma/`)에 저장합니다. 서버를 재시작해도 남습니다. |
| 임베딩 모델 파일 | Docker Compose의 `huggingface-cache` 볼륨에 보관해 컨테이너를 다시 만들어도 다운로드 파일을 재사용합니다. 실행 중에는 검색 엔진 객체도 재사용합니다. |
| 검색 질문의 임베딩 | 질문할 때마다 `search/semantic_search.py`가 새로 계산합니다. 같은 질문의 벡터나 챗봇 답변을 따로 캐시하지 않습니다. |

자막 청크 파일보다 임베딩 JSON 파일이 최신이면 해당 파일의 임베딩 생성을
건너뜁니다. 청크가 수정됐거나 출력 파일이 없으면 다시 계산합니다.
`--overwrite`로 전체 재계산할 수도 있습니다. **청킹 기준을 변경했다면
청크 생성 → 임베딩 생성 → ChromaDB 업로드**, 임베딩 모델만 변경했다면
**임베딩 생성 → ChromaDB 업로드**가 필요합니다. 명령은 아래
[트러블슈팅](#-트러블슈팅)에 있습니다.

### 챗봇 설계에서 고려한 8가지 패턴

| 패턴 | 적용 여부 | 이 프로젝트에서의 역할 |
| --- | --- | --- |
| ① 체인 | 적용 | 질문 → 검색 → 근거 확인 → 답변 단계를 `ChatService.ask()`가 순서대로 연결 |
| ② 구조화 출력 | 적용 | Ollama에 JSON 형식을 요청하고 인용 구절·출처 번호를 서버에서 다시 검증 |
| ③ 대화 메모리 | 적용 | 세션과 선택한 영상별로 최근 4회 대화를 보관해 후속 질문에 활용 |
| ④ 도구 연결(Tool Binding) | 적용 | 모델이 자막 검색어를 제안하고, 실제 검색은 서버가 실행 |
| ⑤ 안정성·복구 | 적용 | 일시 오류 재시도, 생성량 제한, 근거 부족 시 생성 생략, 형식 오류 시 자막 원문 표시 |
| ⑥ 복합 체인 | 적용 | 검색어 선택·영상 범위 검색·관련성 검사·자막 구절 선택·기록 저장을 하나의 흐름으로 연결 |
| ⑦ RAG | 적용 | ChromaDB에서 찾은 자막을 답변 근거로 넣고 실제 영상 시점 링크를 반환 |
| ⑧ Agent | 검토 후 미적용 | 현재는 자막 검색 도구 한 번이면 충분해 모델에 반복적인 도구 선택 권한을 주지 않음 |

#### 적용된 7가지 패턴의 코드 예시

아래 코드는 실제 구현의 핵심 부분을 발췌한 것입니다. 각 예시는 표시된 함수·
메서드 안에서 실행되며 `question`, `history`, `sources` 등은 그 함수에서 앞서
준비한 값입니다. 전체 호출 순서는 [챗봇 학습 가이드](CHATBOT_STUDY.md)를
참고하세요.

**① 체인 — 단계의 출력을 다음 단계의 입력으로 전달**
[`chatbot/service.py`](chatbot/service.py)의 `ChatService.ask()`에서 모델이 고른
검색어를 실제 검색에 사용합니다.

```python
plan = self.model.chat(planner_messages, tools=[SEARCH_TOOL])
search_query = self._tool_query(plan, question, history)
# 선택한 영상이 없을 때
found = self.search_engine.search(search_query, top_k=6)
```

**② 구조화 출력 — 자막 구절과 출처 번호 검증**
같은 파일의 `QUOTE_SCHEMA`와 `ChatService.ask()`입니다. 모델에 JSON 형식을
요청한 후 서버가 다시 파싱하고 선택한 구절이 해당 자막의 원문인지 확인합니다.

```python
response = self.model.chat(answer_messages, response_format=answer_schema)
content = response.get("content", "").strip()
# 코드 블록으로 감싼 JSON이면 실제 구현에서 감싼 부분을 제거
# ...
draft = json.loads(content)
citation = draft["citation"]
quote = draft["quote"].strip()
if (type(citation) is not int or citation < 1 or citation > len(sources)
        or quote not in sources[citation - 1]["text"]):
    raise ValueError("Quote is not grounded in selected source")
answer = f"영상 자막 원문 [{citation}]:\n{quote}"
```

실제 구현은 JSON 코드 블록, 구절 길이, 현재 질문의 주제어 포함 여부도 검사합니다.

**③ 대화 메모리 — 세션과 영상별 최근 대화**
[`chatbot/service.py`](chatbot/service.py)의 `SessionMemory`가 질문·답변을
한 턴으로 저장하고 최근 4턴만 남깁니다.

```python
key = (session_id, video_id or "")
history = self._sessions.setdefault(key, [])
history.extend([{"role": "user", "content": question},
                {"role": "assistant", "content": answer}])
del history[:-2 * self.max_turns]
```

**④ 도구 연결 — 모델은 검색어를 제안하고 서버가 검색**
[`chatbot/service.py`](chatbot/service.py)의 도구 선언과 `ChatService.ask()`의
실행 단계입니다. 영상 선택 값은 서버가 전달받은 값을 사용합니다.

```python
SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_transcripts",
        "description": "Search indexed YouTube transcript passages for evidence about the user's question.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "A standalone Korean search query"}},
            "required": ["query"],
        },
    },
}
# ChatService.ask() 안에서
plan = self.model.chat(planner_messages, tools=[SEARCH_TOOL])
search_query = self._tool_query(plan, question, history)
found = self.search_engine.search_by_video(search_query, video_id, top_k=6)
```

**⑤ 안정성·복구 — 출력량 제한과 근거 부족 처리**
[`chatbot/ollama_client.py`](chatbot/ollama_client.py)는 모델 호출의 생성량을
제한합니다. [`chatbot/service.py`](chatbot/service.py)는 근거가 없으면 답변
구절 선택을 건너뛰고, JSON 검증이 두 번 실패하면 자막 원문을 반환합니다.

```python
# OllamaClient.chat()
payload = {"model": self.model, "messages": messages, "stream": False,
           "options": {"temperature": 0, "repeat_penalty": 1.1,
                       "num_predict": 128 if tools is not None else 512}}

# ChatService.ask()
if not sources:
    self.memory.add(session_id, video_id, question, NO_EVIDENCE)
    return {"answer": NO_EVIDENCE, "sources": [], "citations": [],
            "search_query": search_query, "session_id": session_id,
            "answer_type": "no_evidence"}
```

**⑥ 복합 체인 — 영상 범위 검색, 근거 선별, 대화 저장**
[`chatbot/service.py`](chatbot/service.py)의 `ChatService.ask()`는 한 요청에서
검색 범위를 선택하고 점수와 질문 주제어를 검사한 뒤, 표시한 원문을 메모리에 남깁니다.

```python
if video_id:
    found = self.search_engine.search_by_video(search_query, video_id, top_k=6)
else:
    found = self.search_engine.search(search_query, top_k=6)
focus = question_terms(question) or question_terms(search_query)
sources = [item for item in found.get("results", [])
           if item.get("text") and float(item.get("score", 0)) >= self.min_score
           and (not focus or any(term in item["text"].lower() for term in focus))][:4]
# 모델 응답 검증이 끝난 뒤
self.memory.add(session_id, video_id, question, answer)
```

**⑦ RAG — 검색된 자막만 답변 근거로 전달**
[`chatbot/service.py`](chatbot/service.py)는 검색 결과의 자막에 번호를 붙여
모델에 주고, 응답의 `sources`는 모델이 만든 링크가 아닌 원본 검색 결과를
사용합니다.

```python
evidence = "\n\n".join(
    f"[{index}] 영상: {item['video_title']} | 시점: {item['start_time']}초\n"
    f"자막: {item['text'][:1300]}"
    for index, item in enumerate(sources, 1)
)
# answer_messages 안의 사용자 메시지에 evidence를 넣음
# ...
response = self.model.chat(answer_messages, response_format=answer_schema)
# 선택한 구절을 원문과 대조한 후 검색 결과 원본을 반환
return {"answer": answer, "sources": sources, "citations": citations,
        "search_query": search_query, "session_id": session_id,
        "answer_type": answer_type}
```

이 이름들은 설계 패턴을 설명합니다. 현재 코드는 일반 Python 함수와 Ollama
HTTP API로 구성되며 LangChain의 `Runnable`이나 Agent를 사용하지 않습니다.
모델 설치·실행 방법과 각 패턴의 코드 위치, 향후 LangGraph 확장 기준은
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
후보 중 유사도 `CHAT_MIN_SCORE`(기본 `0.45`) 이상인 결과를 쓰고, 주제어를
추출할 수 있으면 그 단어가 자막에 실제로 포함된 구간만 근거로 씁니다.
후속 질문에서 주제가 바뀌면 이전
질문의 세부 주제어를 검색어에서 제외합니다.
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

### 자막 원문이 길게 보일 때

작은 모델은 반복 문장을 생성해 JSON을 끝내지 못하거나 존재하지 않는 출처
번호나 원문에 없는 문장을 돌려줄 수 있습니다. 서버는 선택한 구절이 실제
자막에 있는지 검사하고 한 번 더 수정을 요청합니다. 두 번 모두 실패하면
**검색된 자막 원문**을 발췌해서 보여 줍니다. 정상 응답도 요약문이 아닌
자막의 정확한 인용이므로 자동 자막의 오류나 어색한 표현이 남을 수 있습니다.
같은 현상이 반복되면 `backend`와
`ollama` 로그를 확인하고 질문을 더 구체적으로 바꿔 보세요.

### 챗봇 가드레일과 설정을 확인할 때

이 챗봇은 **기본형 RAG**처럼 질문마다 검색을 한 번 실행합니다. 다음 검사는
검색 결과가 부족하거나 모델 출력이 잘못됐을 때 근거 없는 문장을 답변으로
보내지 않기 위한 것입니다. 모델의 프롬프트만으로 정확성을 보장하지는 않습니다.

| 단계 | 현재 설정·동작 | 조정 위치 |
| --- | --- | --- |
| 입력·검색 범위 | 질문 1~300자, 세션 ID 8~80자 검증. 선택한 `video_id`는 서버가 검색 범위로 사용하며 모델이 바꿀 수 없음 | `api.py`, `chatbot/service.py` |
| 근거 후보 | 검색 상위 6개 중 점수 `CHAT_MIN_SCORE`(기본 `0.45`) 이상인 결과를 최대 4개 사용. 주제어를 추출할 수 있으면 자막에 해당 단어가 포함돼야 함 | `.env`의 `CHAT_MIN_SCORE`, `chatbot/service.py` |
| 근거 부족 | 통과한 자막이 없으면 답변 모델을 호출하지 않고 `no_evidence` 반환 | `chatbot/service.py` |
| 모델 출력 | `temperature=0`, `repeat_penalty=1.1`, 검색어 최대 128토큰·구절 선택 최대 512토큰. JSON의 출처 번호·구절 길이(8~400자)·질문 주제어·원문 일치를 서버에서 재검증 | `chatbot/ollama_client.py`, `chatbot/service.py` |
| 실패·출처 | 출력 검증 실패 시 한 번 재요청하고, 재실패하면 자막 원문 최대 2개·각 400자를 발췌. 영상 링크는 모델 출력이 아닌 검색 결과에서 생성 | `chatbot/service.py`, `search/semantic_search.py` |
| 시간 제한 | Ollama 요청당 120초, 브라우저 요청 180초. 일시적 연결·서버 오류만 최대 한 번 재시도 | `chatbot/ollama_client.py`, `frontend/src/App.vue` |

자막의 명령을 따르지 말라는 프롬프트도 사용하지만, 이것만으로 프롬프트 주입을
완전히 막는다고 주장하지 않습니다. 원문 일치 검사는 모델이 새로운 사실을
꾸며내는 위험을 줄이는 장치입니다. 자동 자막 자체가 틀렸거나 질문과 관련된
단어만 우연히 포함한 경우까지 판정하지는 못합니다. 주제어 검사는 동의어로만
표현된 좋은 근거를 놓칠 수도 있습니다.

### 로컬 RAG 정량 테스트 결과를 재현할 때

2026-09-29에 색인 영상 **119개**, `qwen2.5:1.5b`, `CHAT_MIN_SCORE=0.45`인
로컬 Docker Compose 환경에서 [`scripts/benchmark_chat.py`](scripts/benchmark_chat.py)의
고정 질문 13개를 **3회 반복**했습니다. 영상 제목을 보고 만든 운동 질문 8개는
각각 해당 영상을 선택했고, 운동과 무관한 질문 5개는 전체 영상에서 검색했습니다.
새 세션을 사용해 순차 요청했으며, 지연 시간은 실행 중인 서버에 대한 API
왕복 시간입니다(콜드 스타트 제외, p95는 nearest-rank 방식).

| 검사항목 | 측정값 |
| --- | ---: |
| API 요청 오류 | 0/39 |
| 운동 질문에 자막 근거 반환 | 24/24 (서로 다른 질문 8개 × 3회) |
| 무관 질문에 `no_evidence` 반환 | 15/15 (서로 다른 질문 5개 × 3회) |
| 직접 인용이 해당 자막의 연속 원문과 일치 | 13/13 |
| 폴백 발췌가 해당 자막의 시작 부분과 일치 | 11/11 |
| 운동 질문 응답 시간 p50 / p95 | 4.17초 / 6.96초 |

운동 질문 24회 중 **11회(45.8%)**는 모델이 유효한 짧은 인용을 고르지 못해
자막 발췌로 대체됐습니다. 아래 명령으로 같은 질문을 다시 실행할 수 있습니다.
`APP_PORT`를 바꿨다면 `--base-url`도 맞춰 주세요.

```bash
for run in 1 2 3; do
  python3 scripts/benchmark_chat.py --output "benchmark-run-${run}.json"
done
```

이 수치는 **8개 운동 질문과 5개 무관 질문으로 만든 소규모 편의 표본**의 동작
결과입니다. 39개 서로 다른 질문에 대한 정확도가 아닙니다. 인용의 원문 일치는
출처 검증이며, 자막 자체의 사실 여부나 답변의 충분성을 평가한 점수가 아닙니다.
영상 목록·모델·컴퓨터 부하가 바뀌면 결과와 응답 시간도 달라질 수 있습니다.

검색 순위 자체는 별도로 평가했습니다. 같은 운동 질문 8개를 **영상 선택 없이**
`/api/search`에 보내고, 반환된 상위 10개 자막의 내용을 읽어 질문에 직접 답하는
구간만 관련 있다고 판정했습니다. 단어만 등장하거나 다른 운동 설명인 구간은
제외했습니다. [`판정 라벨`](benchmarks/retrieval_labels_2026-09-29.json)은
총 71개 검색 구간을 포함합니다. Hit@K는 관련 구간이 상위 K개 안에 있는 질문의
비율이고, MRR@K는 각 질문의 **첫 관련 구간 순위의 역수**를 평균한 값입니다
(검색 실패는 0점).

| 검색 지표 | 결과 (질문 8개) |
| --- | ---: |
| Hit@1 | 1/8 = 12.5% |
| Hit@3 · Hit@10 | 7/8 = 87.5% |
| MRR@10 | 0.417 |

[`scripts/benchmark_retrieval.py`](scripts/benchmark_retrieval.py)로 다시 계산할 수
있습니다. 색인이나 검색 결과가 바뀌어 **판정되지 않은 구간**이 나오면 점수를
출력하지 않고 라벨 갱신을 요구합니다.

```bash
python3 scripts/benchmark_retrieval.py --output retrieval-benchmark.json
```

이 검색 지표도 작은 표본에 대한 **단일 수동 판정**이며 독립 검수는 거치지
않았습니다. 특히 첫 결과의 관련성은 낮았고, 오버헤드프레스 질문에는 관련
구간이 반환되지 않았습니다. 다른 영상의 자막도 정답이 될 수 있어, 질문을 만든
영상 ID 하나가 검색됐는지만으로 Hit Rate를 계산하지 않았습니다.

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
