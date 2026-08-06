# YouTube Semantic Search 학습 순서

이 프로젝트는 아래 데이터 흐름으로 동작합니다.

```text
YouTube 영상 ID
  → VTT 자막 다운로드
  → 자막 JSON
  → 의미 단위 청크
  → 임베딩 벡터
  → ChromaDB
  → 검색 결과
```

## 추천 파일 순서

### 1. `utils/utils.py`

가장 작은 함수부터 시작합니다. 파일 읽기/쓰기, 리스트, 딕셔너리, 반복문을
복습하기 좋습니다. 먼저 `vtt_time_to_seconds()`에 중단점을 걸어 보세요.

### 2. `scripts/fetch_captions.py`

외부 프로그램인 yt-dlp를 Python에서 실행하고, 결과 파일을 JSON으로 바꾸는
과정을 봅니다. `fetch_caption_with_ytdlp()`의 `subprocess.run()` 전후 값을
디버거의 Variables 창에서 비교하세요.

### 3. `scripts/preprocess_captions.py`

리스트 안의 여러 자막 딕셔너리를 합치고 나누는 과정입니다. 다음 함수 순서로
읽으면 됩니다.

1. `combine_caption_segments()`
2. `split_long_blocks()`
3. `create_semantic_chunks()`
4. `process_caption_file()`

### 4. `scripts/embed_chunks.py`

문자열 리스트가 숫자 벡터 리스트로 변하는 단계입니다. 모델 내부 수학보다
`model.encode()`의 입력 `texts`와 출력 `embeddings`의 자료형과 크기에 먼저
집중하세요.

### 5. `db/chroma_setup.py`

ChromaDB 클라이언트와 컬렉션이 무엇인지 확인합니다. 코드가 짧아서 먼저 읽고
다음 파일로 넘어가기 좋습니다.

### 6. `db/upload_embeddings.py`

JSON 딕셔너리를 DB 레코드 구조로 바꾸고 여러 건씩 저장합니다.
`prepare_chunks_for_chroma()`의 `chunk`와 `records[0]`을 비교해 보세요.

### 7. `search/semantic_search.py`

클래스를 학습하는 파일입니다. 다음 순서로 읽습니다.

1. `__init__()` — 객체가 만들어질 때 실행
2. `embed_query()` — 질문을 벡터로 변환
3. `_query()` — ChromaDB에 검색 요청
4. `search_by_video()` — 검색 결과 딕셔너리 구성

`self`는 현재 생성된 `YouTubeSemanticSearch` 객체 자신을 가리킵니다.

### 8. `main.py`

마지막에 봅니다. 앞에서 학습한 파일들을 `full_pipeline()`이 어떤 순서로
연결하는지 확인합니다. 전체 실행을 디버깅할 때 시작할 파일도 `main.py`입니다.

## 디버거 사용법

처음부터 모든 줄에서 멈추기보다 함수 입구에 중단점을 하나씩 둡니다.

1. VS Code의 실행 구성에서 `YouTube Search: main.py`를 선택합니다.
2. `F5`로 시작합니다.
3. `F10`은 현재 줄을 실행하고 다음 줄로 이동합니다.
4. `F11`은 호출되는 함수 안으로 들어갑니다.
5. `Shift+F11`은 현재 함수에서 호출한 곳으로 돌아갑니다.
6. Variables에서 리스트를 펼쳐 원소와 딕셔너리 키를 확인합니다.

처음 한 번은 `F11`을 무조건 누르지 마세요. 표준 라이브러리나 외부 패키지
내부까지 들어가면 학습 흐름을 놓치기 쉽습니다. 이 프로젝트에서 정의한 함수
호출에서만 `F11`을 사용하고, `subprocess.run()`, `json.load()`, `model.encode()`
같은 외부 함수는 `F10`으로 넘기는 편이 좋습니다.

## 첫 디버깅에서 확인할 값

- `video_id`: URL에서 추출한 11자리 영상 ID
- `segments`: 짧은 원본 자막 딕셔너리의 리스트
- `chunks`: 검색하기 좋은 길이로 합쳐진 자막 리스트
- `embedding`: 한 문장을 표현하는 실수 리스트
- `metadata`: 영상 ID, 제목, 시간, 원문을 담은 딕셔너리
- `results`: 검색 결과들을 담은 딕셔너리
