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

## 학습을 시작하기 전 준비

한 번에 전체 프로그램을 이해하려고 하지 않습니다. 한 학습 세션은 30~45분으로
정하고, 함수 한두 개만 완전히 이해하는 것을 목표로 합니다.

VS Code에서 먼저 프로젝트 가상환경을 선택합니다.

```text
Cmd + Shift + P
→ Python: Select Interpreter
→ .venv/bin/python
```

터미널에서 선택된 Python도 확인합니다.

```bash
which python
python --version
```

`which python`의 결과가 프로젝트의 `.venv/bin/python`으로 끝나야 합니다.

학습 노트를 하나 만들고 함수마다 아래 네 항목을 기록하세요.

```text
함수 이름:
입력 자료형:
반환 자료형:
이 함수가 필요한 이유:
```

코드를 읽은 설명을 그대로 복사하지 말고 자신의 말로 한두 문장을 적는 것이
중요합니다.

## 한 함수를 공부하는 구체적인 방법

모든 함수에 아래 7단계를 반복 적용합니다.

### 1단계: 함수 이름만 보고 예상하기

함수 내용을 읽기 전에 이름과 매개변수만 봅니다.

```python
def vtt_time_to_seconds(time_str):
```

다음 내용을 먼저 예상합니다.

- `time_str`에는 어떤 값이 들어올까?
- 성공하면 무엇을 반환할까?
- 문자열을 숫자로 바꾸려면 어떤 처리가 필요할까?

예상이 틀려도 괜찮습니다. 예상과 실제 구현의 차이가 학습할 부분입니다.

### 2단계: 입력과 출력의 실제 예를 적기

```text
입력:  "00:01:02.500"
출력:  62.5
```

리스트나 딕셔너리라면 원소 하나까지 구체적으로 적습니다.

```python
segments = [
    {"text": "안녕하세요", "start": 1.0, "duration": 2.0}
]
```

### 3단계: 첫 실행 줄에 중단점 걸기

`def` 줄은 함수 등록 시점이므로 함수 내부 실행을 관찰하기 어렵습니다. `def`
아래에서 실제 값을 처리하는 첫 줄에 중단점을 겁니다.

```python
time_str = time_str.strip().split()[0]  # 이 줄에 중단점
```

### 4단계: 실행 전에 Variables 확인하기

중단점에서 바로 `F10`을 누르지 말고 다음을 확인합니다.

- 매개변수의 현재 값
- 값 왼쪽에 표시되는 자료형
- 리스트의 길이
- 딕셔너리의 키

Debug Console에서 표현식을 직접 실행할 수도 있습니다.

```python
type(time_str)
repr(time_str)
len(time_str)
```

`repr()`은 공백이나 줄바꿈처럼 화면에서 놓치기 쉬운 문자까지 보여 줍니다.

### 5단계: 한 줄 실행 후 이전 값과 비교하기

`F10`을 한 번 누른 후 변수 값이 어떻게 변했는지 봅니다.

```text
실행 전 time_str: " 00:01:02.500 "
실행 후 time_str: "00:01:02.500"
```

변화가 없다면 그 줄은 새 변수를 만들었는지, 조건만 확인했는지 살펴봅니다.

### 6단계: 조건문을 말로 읽기

```python
if gap <= max_gap:
```

아래처럼 자신의 말로 바꿉니다.

```text
두 자막 사이의 빈 시간이 0.5초 이하면 같은 발화로 합친다.
```

`and`, `or`, `not`이 있다면 조건을 한 부분씩 나눠 확인하세요.

### 7단계: 작은 값을 바꿔 다시 실행하기

한 번 관찰한 뒤 매개변수를 바꿔 결과를 예상합니다.

```python
max_gap = 0.5  # 원래 값
max_gap = 0.1  # 실험 값
```

변경 전후의 블록 개수를 비교한 뒤 실험이 끝나면 원래 값으로 되돌립니다.

## 단계별 실습 계획

### 1일차: 문자열과 시간 변환

대상 파일: `utils/utils.py`

대상 함수:

1. `ensure_dir_exists()`
2. `load_json()`
3. `save_json()`
4. `vtt_time_to_seconds()`

`vtt_time_to_seconds()`의 아래 줄에 중단점을 겁니다.

```python
parts = time_str.split(':')
```

Variables 또는 Debug Console에서 확인합니다.

```python
time_str
parts
parts[0]
parts[1]
parts[2]
type(parts)
```

이해 확인 질문:

- `split(':')`의 반환값은 왜 문자열이 아니라 리스트인가?
- 1분을 초로 바꾸려면 왜 60을 곱하는가?
- 잘못된 시간 문자열에서 왜 `0.0`을 반환하는가?

직접 실험할 값:

```text
00:00:05.000 → 예상 5.0
00:01:30.500 → 예상 90.5
01:00:00.000 → 예상 3600.0
```

### 2일차: VTT 자막을 리스트로 만들기

대상 함수: `parse_vtt_file()`

중단점 위치:

```python
line = lines[i].strip()
```

한 자막 블록이 처리될 때 다음 변화를 관찰합니다.

```text
lines[i]
→ timestamp_parts
→ start_time / end_time
→ text_lines
→ text
→ transcript[-1]
```

특히 `i`가 한 번에 1씩만 증가하지 않는 이유를 확인하세요. 시간 줄을 찾은 후
그 아래의 여러 텍스트 줄까지 같은 `while` 반복에서 읽기 때문입니다.

이해 확인 질문:

- 이 함수가 `for`보다 `while`을 사용한 이유는 무엇인가?
- `transcript`는 리스트이고 각 원소는 왜 딕셔너리인가?
- `continue`를 실행하면 반복문의 어느 지점으로 이동하는가?

### 3일차: 짧은 자막 합치고 나누기

대상 파일: `scripts/preprocess_captions.py`

먼저 `combine_caption_segments()`만 봅니다. 중단점은 다음 줄에 둡니다.

```python
gap = segment['start'] - current_block['end']
```

확인할 값:

```python
segment
current_block
gap
max_gap
len(combined)
```

`F10`으로 `if gap <= max_gap`의 양쪽 경로를 모두 관찰하세요. 계속 같은 경로만
실행된다면 조건식에서 오른쪽 클릭 후 조건부 중단점을 사용할 수 있습니다.

그다음 아래 순서로 이동합니다.

```text
combine_caption_segments
→ split_korean_sentences
→ split_long_blocks
→ create_semantic_chunks
```

각 함수 호출 전후의 리스트 길이를 표로 기록합니다.

```text
segments 개수:
combined_blocks 개수:
split_blocks 개수:
chunks 개수:
```

### 4일차: 외부 프로그램 실행 이해하기

대상 파일: `scripts/fetch_captions.py`

중단점 위치:

```python
result = subprocess.run(...)
```

실행 전에는 `cmd` 리스트를 확인합니다. 실행 후에는 다음 값을 확인합니다.

```python
result.returncode
result.stdout
result.stderr
```

`subprocess.run()` 내부는 외부 라이브러리 영역이므로 `F11` 대신 `F10`으로
넘깁니다. 이 단계의 목표는 yt-dlp 내부 구현이 아니라 Python이 외부 프로그램에
인자를 전달하고 종료 코드를 받는 구조를 이해하는 것입니다.

이해 확인 질문:

- `cmd`를 하나의 긴 문자열이 아니라 리스트로 만든 이유는 무엇인가?
- `returncode == 0`은 무엇을 의미하는가?
- 임시 폴더가 `with` 블록 이후 자동 삭제되는 이유는 무엇인가?

### 5일차: 문장을 벡터로 변환하기

대상 파일: `scripts/embed_chunks.py`

중단점 위치:

```python
embeddings = model.encode(...)
```

실행 전에 확인합니다.

```python
type(texts)
len(texts)
texts[0]
```

`F10`으로 모델 실행을 넘긴 후 확인합니다.

```python
type(embeddings)
embeddings.shape
embeddings[0].shape
embeddings[0][:5]
```

벡터의 모든 숫자를 이해하려 하지 마세요. 이 단계에서는 문장 N개가 벡터 N개로
바뀌며 같은 인덱스끼리 대응한다는 사실만 이해하면 충분합니다.

### 6일차: ChromaDB 저장 구조 이해하기

대상 파일: `db/upload_embeddings.py`

먼저 `prepare_chunks_for_chroma()`의 다음 줄에 중단점을 겁니다.

```python
records.append(...)
```

`chunk`와 완성된 `records[-1]`을 비교합니다.

```python
chunk.keys()
records[-1].keys()
records[-1]['metadata']
len(records[-1]['embedding'])
```

다음 세 값을 구분할 수 있어야 합니다.

- `id`: 레코드를 구분하는 고유 문자열
- `embedding`: 유사도 계산에 사용하는 숫자 리스트
- `metadata`: 검색 결과에 표시할 제목, 시간, 자막

### 7일차: 검색 클래스와 전체 흐름

대상 파일: `search/semantic_search.py`, `main.py`

아래 순서로 중단점을 이동합니다.

```text
YouTubeSemanticSearch.__init__
→ embed_query
→ _query
→ search_by_video
→ main.py의 results 처리
```

`self.model`과 `self.collection`을 확인해 `self`가 현재 객체에 보관된 값에
접근한다는 것을 확인합니다.

검색 시에는 다음 값을 기록합니다.

```text
검색어:
검색어 embedding 길이:
DB가 반환한 distance:
변환된 score:
1위 자막:
```

마지막으로 `main.py`의 `full_pipeline()`에서 각 스크립트가 어떤 파일을 입력받고
어떤 파일을 만드는지 자신의 말로 설명해 보세요.

## 막혔을 때 사용하는 질문 순서

코드가 이해되지 않을 때 바로 전체 함수의 해설을 찾기보다 아래 순서로 질문을
작게 나눕니다.

1. 현재 변수의 자료형은 무엇인가?
2. 현재 변수에는 실제로 어떤 값이 들어 있는가?
3. 이 줄은 기존 변수를 바꾸는가, 새 변수를 만드는가?
4. 반복문이라면 현재 몇 번째 원소를 처리하고 있는가?
5. 조건문이라면 어떤 부분이 True 또는 False인가?
6. 함수 호출이라면 입력과 반환값은 무엇인가?
7. 이 함수의 결과를 다음 어느 함수가 사용하는가?

## 학습 완료 기준

코드를 외우는 것이 완료 기준은 아닙니다. 아래 항목을 코드 없이 말할 수 있으면
프로젝트의 기본 구조를 이해한 것입니다.

- 영상 ID가 자막 JSON으로 바뀌는 과정을 설명할 수 있다.
- 리스트 안의 자막 딕셔너리 구조를 직접 작성할 수 있다.
- 원본 자막을 합친 뒤 다시 나누는 이유를 설명할 수 있다.
- 문자열과 임베딩 벡터의 차이를 설명할 수 있다.
- ChromaDB의 embedding과 metadata 역할을 구분할 수 있다.
- 검색어가 결과 자막으로 이어지는 함수 호출 순서를 설명할 수 있다.
- 오류가 발생했을 때 어느 파이프라인 단계에서 실패했는지 찾을 수 있다.
