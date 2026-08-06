"""짧고 중복이 많은 원본 자막을 검색하기 좋은 의미 단위 청크로 만든다.

처리 순서:
1. 시간상 가까운 자막 조각을 합친다.
2. 지나치게 긴 블록을 문장 또는 단어 단위로 나눈다.
3. 여러 블록을 적당한 길이의 검색 청크로 다시 묶는다.
"""

import json
from pathlib import Path
import re
import argparse
import sys

# 일부 터미널에서 한글/이모지가 깨지지 않도록 출력 인코딩을 UTF-8로 맞춘다.
# sys.stdout은 실행 환경에 따라 reconfigure가 없는 TextIO일 수도 있다.
# getattr의 기본값 None을 이용하면 속성이 없어도 오류가 발생하지 않는다.
stdout_reconfigure = getattr(sys.stdout, "reconfigure", None)
stderr_reconfigure = getattr(sys.stderr, "reconfigure", None)

if callable(stdout_reconfigure):
    stdout_reconfigure(encoding="utf-8")
if callable(stderr_reconfigure):
    stderr_reconfigure(encoding="utf-8")

def combine_caption_segments(segments, max_gap=0.5):
    """시간상 이어지는 짧은 자막 조각을 하나의 블록으로 합친다.

    ``segments`` 구조 예시::

        [{"text": "오늘은", "start": 0.0, "duration": 0.8}, ...]

    반환하는 블록은 ``duration`` 대신 종료 시각 ``end``를 가진다. 앞 블록의
    종료와 다음 조각의 시작 사이가 ``max_gap``초 이하면 같은 발화로 본다.
    """
    if not segments:
        return []

    combined = []
    # 첫 자막으로 현재 작업 중인 블록을 초기화한다.
    current_block = {
        'text': segments[0]['text'],
        'start': segments[0]['start'],
        'end': segments[0]['start'] + segments[0]['duration']
    }

    # 첫 원소는 current_block을 만드는 데 썼으므로 두 번째 원소부터 반복한다.
    for segment in segments[1:]:
        # 다음 자막 시작 시각 - 현재 블록 종료 시각 = 두 자막 사이의 공백 시간.
        gap = segment['start'] - current_block['end']

        if gap <= max_gap:
            # 같은 발화: 텍스트와 종료 시각을 현재 블록에 이어 붙인다.
            current_block['text'] += ' ' + segment['text']
            current_block['end'] = segment['start'] + segment['duration']
        else:
            # 긴 침묵: 현재 블록을 확정하고 다음 자막으로 새 블록을 시작한다.
            combined.append(current_block)
            current_block = {
                'text': segment['text'],
                'start': segment['start'],
                'end': segment['start'] + segment['duration']
            }

    combined.append(current_block)
    return combined

def add_punctuation(text):
    """한국어 자막의 연속 공백을 정리하고 문장 끝에 마침표를 보충한다."""
    try:
        # re.sub(패턴, 대체값, 문자열)은 정규식과 일치하는 부분을 바꾼다.
        clean_text = re.sub(r'\s+', ' ', text.strip())

        # 한국어에는 대소문자가 없으므로 첫 글자를 upper()로 바꾸지 않는다.
        # 이미 한국어/영어 문장부호로 끝나면 마침표를 중복해서 붙이지 않는다.
        if clean_text and clean_text[-1] not in '.!?。！？':
            clean_text += '.'

        return clean_text

    except Exception as e:
        print(f"⚠️ Punctuation failed: {e}")
        fallback = text.strip()
        return fallback + '.' if fallback and fallback[-1] not in '.!?。！？' else fallback


def split_korean_sentences(text):
    """한국어 문장부호 뒤의 공백을 기준으로 문장을 나눈다.

    문장부호가 없는 자동 자막은 하나의 문장으로 남는다. 그러면
    ``split_long_blocks``가 아래에서 단어 수를 기준으로 다시 나눈다.
    """
    if not text or not text.strip():
        return []

    return [
        sentence.strip()
        for sentence in re.split(r'(?<=[.!?。！？])\s+', text.strip())
        if sentence.strip()
    ]

def create_semantic_chunks(blocks, target_length=30, max_length=60):
    """여러 블록을 검색에 사용할 적당한 길이의 청크로 묶는다.

    청크 하나는 ``text/start/end/duration/blocks`` 키를 가진 딕셔너리다.
    너무 짧으면 의미가 부족하고 너무 길면 여러 주제가 섞이므로 대략
    ``target_length`` 단어를 목표로 한다.
    """
    chunks = []
    current_chunk = {
        'text': '',
        'start': None,
        'blocks': []
    }
    # 아직 완성되지 않은 current_chunk에 들어 있는 단어 수다.
    word_count = 0

    for block in blocks:
        punctuated_text = add_punctuation(block['text'])
        block_words = len(punctuated_text.split())

        if current_chunk['start'] is None:
            # 현재 청크에 처음 들어온 블록의 시작 시각을 기억한다.
            current_chunk['start'] = block['start']

        # 현재 블록을 더했을 때 목표 길이를 넘으면 기존 청크를 먼저 완성한다.
        if word_count > 0 and (word_count + block_words > target_length or word_count > max_length):
            current_chunk['end'] = current_chunk['blocks'][-1]['end']
            current_chunk['duration'] = current_chunk['end'] - current_chunk['start']
            # list comprehension으로 각 블록 텍스트를 얻고 join으로 하나의 문자열을 만든다.
            current_chunk['text'] = ' '.join([add_punctuation(b['text']) for b in current_chunk['blocks']])
            # 완성된 딕셔너리를 최종 결과 리스트에 넣는다.
            chunks.append(current_chunk)

            current_chunk = {
                'text': '',
                'start': block['start'],
                'blocks': [block]
            }
            word_count = block_words
        else:
            current_chunk['blocks'].append(block)
            word_count += block_words

    if current_chunk['blocks']:
        current_chunk['end'] = current_chunk['blocks'][-1]['end']
        current_chunk['duration'] = current_chunk['end'] - current_chunk['start']
        current_chunk['text'] = ' '.join([add_punctuation(b['text']) for b in current_chunk['blocks']])
        chunks.append(current_chunk)

    return chunks

def split_long_blocks(blocks, max_duration=30.0, max_words=80):
    """너무 긴 블록을 문장 또는 단어 묶음으로 나눈다.

    짧은 블록은 그대로 ``result``에 추가한다. 긴 블록은 먼저 문장부호로
    나누고, 문장부호가 없으면 ``max_words // 2`` 단어씩 강제로 나눈다.
    나뉜 문장의 정확한 타임스탬프는 알 수 없으므로 전체 시간을 문장 수로
    균등 분배해 근삿값을 만든다.
    """
    result = []

    for block in blocks:
        block_words = len(block['text'].split())
        if block['end'] - block['start'] <= max_duration and block_words <= max_words:
            result.append(block)
            continue

        text = block['text']
        # 한국어 문장부호를 기준으로 나누므로 외부 토크나이저가 필요 없다.
        sentences = split_korean_sentences(text)

        if len(sentences) <= 1:
            words = text.split()
            sentences = []
            # 문장 경계를 찾지 못하면 최대 단어 수의 절반씩 강제로 자른다.
            for i in range(0, len(words), max_words // 2):
                sentences.append(' '.join(words[i:i + max_words // 2]))

        # 예: 20초짜리 블록에서 문장 4개를 찾았다면 문장당 5초로 추정한다.
        duration_per_sentence = (block['end'] - block['start']) / len(sentences)
        current_time = block['start']

        for sentence in sentences:
            if sentence.strip():
                result.append({
                    'text': sentence.strip(),
                    'start': current_time,
                    'end': current_time + duration_per_sentence
                })
                current_time += duration_per_sentence

    return result

def process_caption_file(input_file, output_file):
    """자막 JSON 하나에 전처리 3단계를 적용하고 청크 리스트를 반환한다.

    이 함수는 작은 함수들을 순서대로 연결하는 조정자 역할을 한다:
    원본 segments → combined_blocks → split_blocks → 최종 chunks.
    디버거의 Variables 창에서 각 변수의 리스트 길이를 비교하면 흐름이 보인다.
    """
    print(f"🔄 Processing {input_file}...")

    with open(input_file, encoding="utf-8") as f:
        segments = json.load(f)

    print(f"📥 Loaded {len(segments)} caption segments")

    combined_blocks = combine_caption_segments(segments, max_gap=0.5)
    print(f"🔗 Combined into {len(combined_blocks)} blocks")

    split_blocks = split_long_blocks(combined_blocks)
    print(f"✂️ Split into {len(split_blocks)} manageable blocks")

    chunks = create_semantic_chunks(split_blocks, target_length=25, max_length=50)
    print(f"📝 Created {len(chunks)} semantic chunks")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved processed chunks to {output_file}")
    return chunks

def chunk_captions(video_id: str, title: str):
    """단순 고정 크기 분할이 필요할 때 사용하는 이전 방식의 보조 함수."""
    # 함수 안에서 import하면 이 함수가 호출될 때만 모듈을 불러온다.
    from utils.utils import load_json, save_json, split_into_chunks
    input_file = Path(f"data/captions/{title}_{video_id}.json")
    output_file = Path(f"data/chunks/{title}_{video_id}.json")

    if not input_file.exists():
        raise FileNotFoundError(f"Captions file not found: {input_file}")

    captions = load_json(input_file)
    chunks = split_into_chunks(captions)
    save_json(chunks, output_file)
    return True

if __name__ == "__main__":
    # 이 아래는 함수 정의가 아니라 스크립트를 직접 실행할 때의 실제 작업 흐름이다.
    captions_dir = Path("data/captions")
    chunks_dir = Path("data/chunks")
    chunks_dir.mkdir(parents=True, exist_ok=True)

    # glob("*.json")은 폴더 안에서 확장자가 json인 Path들을 찾는다.
    # sorted로 순서를 고정하면 실행할 때마다 같은 순서로 처리되어 확인하기 쉽다.
    caption_files = sorted(captions_dir.glob("*.json"))

    if not caption_files:
        print("❌ No caption files found in data/captions/")
        exit(1)

    print(f"🔍 Found {len(caption_files)} caption files")
    new_files_found = False
    processed_count = 0

    for input_file in caption_files:
        # Path의 / 연산자는 경로를 연결한다. stem은 확장자를 뺀 파일명이다.
        output_file = chunks_dir / f"processed_{input_file.stem}.json"

        # 입력 파일이 출력보다 오래됐으면 이미 최신 처리 결과가 있으므로 건너뛴다.
        if output_file.exists():
            if input_file.stat().st_mtime <= output_file.stat().st_mtime:
                print(f"⏩ Skipping {input_file.name} (already processed)")
                continue
            else:
                print(f"🔄 Re-processing {input_file.name} (source file updated)")
        else:
            print(f"🆕 Processing new file: {input_file.name}")

        new_files_found = True
        chunks = process_caption_file(input_file, output_file)
        processed_count += 1

        print(f"\n🎯 Chunk Statistics:")
        # 각 청크를 반복해 단어 수만 모은 새 리스트를 만드는 표현식이다.
        word_counts = [len(chunk['text'].split()) for chunk in chunks]
        durations = [chunk['duration'] for chunk in chunks]

        print(f"Total chunks: {len(chunks)}")
        print(f"Word count - Min: {min(word_counts)}, Max: {max(word_counts)}, Avg: {sum(word_counts)/len(word_counts):.1f}")
        print(f"Duration - Min: {min(durations):.1f}s, Max: {max(durations):.1f}s, Avg: {sum(durations)/len(durations):.1f}s")

    if not new_files_found:
        print("\n✅ No new caption files to process. All files are up to date!")
    else:
        print(f"\n🎉 Processing complete! Processed {processed_count} files.")
