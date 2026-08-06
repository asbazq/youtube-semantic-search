"""여러 스크립트에서 공통으로 사용하는 파일·문자열 처리 함수 모음."""

import os
import json
import re
import logging
from pathlib import Path
from difflib import SequenceMatcher  # ✅ For fuzzy text similarity

logger = logging.getLogger(__name__)

# ``from utils.utils import *``를 사용할 때 외부로 공개할 이름을 제한한다.
__all__ = [
    "load_json", "save_json", "ensure_dir_exists",
    "vtt_time_to_seconds", "is_similar", "parse_vtt_file",
    "split_into_chunks"
]

def ensure_dir_exists(path):
    """폴더가 없으면 만들고, 이미 있으면 아무 작업도 하지 않는다."""
    # isinstance는 객체가 특정 자료형인지 확인한다.
    path = str(path) if isinstance(path, Path) else path
    os.makedirs(path, exist_ok=True)

def load_json(filepath):
    """JSON 파일을 Python의 dict/list 자료구조로 읽는다."""
    filepath = str(filepath) if isinstance(filepath, Path) else filepath
    with open(filepath, "r", encoding="utf-8") as f:
        # with가 끝나면 파일 객체 f는 예외가 발생해도 자동으로 닫힌다.
        return json.load(f)

def save_json(data, filepath):
    """Python dict/list를 한글이 보존되는 JSON 파일로 저장한다."""
    filepath = str(filepath) if isinstance(filepath, Path) else filepath
    with open(filepath, "w", encoding="utf-8") as f:
        # indent=2는 들여쓰기, ensure_ascii=False는 한글을 \uXXXX로 바꾸지 않는 옵션이다.
        json.dump(data, f, indent=2, ensure_ascii=False)

def vtt_time_to_seconds(time_str):
    """VTT의 ``시:분:초.밀리초`` 문자열을 초 단위 float으로 바꾼다.

    예: ``"00:01:02.500"`` → ``62.5``. 문자열을 ``:``과 ``.``으로
    차례로 나눈 뒤 각 부분을 숫자로 바꾸는 과정을 관찰하면 된다.
    """
    try:
        # 종료 시간 뒤에 설정 문자열이 붙는 VTT도 있어 첫 번째 값만 사용한다.
        time_str = time_str.strip().split()[0]
        # "00:01:02.500" -> ["00", "01", "02.500"]
        parts = time_str.split(':')
        if len(parts) != 3:
            raise ValueError("Invalid time format")
        hours = int(parts[0])
        minutes = int(parts[1])
        # "02.500" -> ["02", "500"]
        seconds_parts = parts[2].split('.')
        seconds = int(seconds_parts[0])
        milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
        # 모든 단위를 초로 통일한 뒤 더한다.
        return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000
    except Exception as e:
        logger.warning(f"⚠️ Failed to parse time: '{time_str}' ({e})")
        return 0.0

def is_similar(a, b, threshold=0.9):
    """두 문자열의 유사도가 threshold(기본 90%)보다 높은지 확인한다."""
    if a is None or b is None:
        return False
    return SequenceMatcher(None, a, b).ratio() > threshold

def parse_vtt_file(vtt_file: Path):
    """VTT 파일을 읽어 자막 딕셔너리의 리스트로 변환한다.

    입력 VTT 한 블록 예시::

        00:00:01.000 --> 00:00:03.000
        안녕하세요

    반환 리스트의 원소 예시::

        {"text": "안녕하세요", "start": 1.0, "duration": 2.0}

    ``transcript``는 최종 결과 리스트이고, 반복할 때마다 자막 딕셔너리
    하나가 ``append``된다.
    """
    transcript = []
    last_text = None
    last_start_time = -1.0

    try:
        with vtt_file.open("r", encoding="utf-8") as f:
            lines = f.readlines()

        i = 0
        # for 대신 while을 쓰는 이유는 한 자막 블록을 읽으며 i를 여러 줄 이동하기 때문이다.
        while i < len(lines):
            line = lines[i].strip()

            # VTT에서 '-->'가 들어간 줄은 시작/종료 시각을 나타낸다.
            if '-->' in line:
                timestamp_parts = line.split(' --> ')
                if len(timestamp_parts) != 2:
                    i += 1
                    continue

                start_time = vtt_time_to_seconds(timestamp_parts[0])
                end_time = vtt_time_to_seconds(timestamp_parts[1])

                if end_time <= start_time:
                    logger.warning(f"⚠️ Invalid duration in VTT: start={start_time}, end={end_time}")
                    # 임시로 3초짜리 자막이라고 가정
                    # duration = 3.0
                    # 잘못된 시간 건너 뜀
                    i += 1
                    continue;
                else:
                    duration = round(end_time - start_time, 3)
                    duration = max(duration, 0.5)

                # Collect subtitle text
                i += 1
                text_lines = []
                # 빈 줄은 한 자막 블록의 끝이다. 그 전까지 모든 텍스트 줄을 모은다.
                while i < len(lines) and lines[i].strip():
                    clean_line = re.sub(r'<.*?>', '', lines[i].strip())  # Remove HTML tags
                    clean_line = re.sub(r'\[.*?\]', '', clean_line)     # Remove square bracket content
                    clean_line = clean_line.replace('♪', '')
                    clean_line = re.sub(r'\s+', ' ', clean_line).strip()
                    if clean_line:
                        text_lines.append(clean_line)
                    i += 1

                text = ' '.join(text_lines).strip()

                # 자동 자막에는 거의 같은 문장이 반복되므로 중복을 제거한다.
                if not text or is_similar(text, last_text):
                    continue
                if last_start_time >= 0 and abs(start_time - last_start_time) < 0.3:
                    logger.debug(f"⏩ Skipping overlapping segment at {start_time}")
                    continue

                # 하나의 자막 정보를 dict로 묶어 결과 list의 끝에 추가한다.
                transcript.append({
                    'text': text,
                    'start': start_time,
                    'duration': duration
                })
                last_text = text
                last_start_time = start_time
            else:
                i += 1

    except Exception as e:
        logger.error(f"🔥 Error parsing VTT file: {type(e).__name__}: {e}")
        return None

    return transcript

def split_into_chunks(segments, chunk_size=30):
    """
    자막 조각을 chunk_size개씩 묶어 더 큰 임베딩용 청크를 만든다.

    이 함수는 단순 분할 방식이며 현재의 정교한 전처리는
    scripts/preprocess_captions.py에서 수행한다.
    """
    chunks = []
    # 슬라이싱 segments[i:i + chunk_size]은 원본 리스트의 일부를 새 리스트로 만든다.
    for i in range(0, len(segments), chunk_size):
        chunk = segments[i:i + chunk_size] # 리스트[시작위치:종료위치] Python 슬라이싱은 가능한 마지막 원소까지만 가져옴
        combined_text = " ".join([seg["text"] for seg in chunk])
        chunks.append({
            "text": combined_text,
            "start": chunk[0]["start"],
            "end": chunk[-1]["start"] + chunk[-1]["duration"]
        })
    return chunks
