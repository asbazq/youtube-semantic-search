import json
from pathlib import Path
import re    
import nltk
import argparse
import sys
from nltk.tokenize import sent_tokenize

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

def combine_caption_segments(segments, max_gap=0.5):
    """Combine short caption segments into longer text blocks"""
    if not segments:
        return []

    combined = []
    current_block = {
        'text': segments[0]['text'],
        'start': segments[0]['start'],
        'end': segments[0]['start'] + segments[0]['duration']
    }

    for segment in segments[1:]:
        gap = segment['start'] - current_block['end']

        if gap <= max_gap:
            current_block['text'] += ' ' + segment['text']
            current_block['end'] = segment['start'] + segment['duration']
        else:
            combined.append(current_block)
            current_block = {
                'text': segment['text'],
                'start': segment['start'],
                'end': segment['start'] + segment['duration']
            }

    combined.append(current_block)
    return combined

def add_punctuation(text):
    """Add basic punctuation"""
    try:
        clean_text = re.sub(r'\s+', ' ', text.strip())
        clean_text = re.sub(r'\b(well|so|now|then|first|second|also|however|therefore)\s+', r'\1, ', clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(r'(?<![.!?])\s+(now|so|well|first|then|also|however|therefore)\s+', r'. \1 ', clean_text, flags=re.IGNORECASE)

        if clean_text:
            clean_text = clean_text[0].upper() + clean_text[1:]
        if clean_text and clean_text[-1] not in '.!?':
            clean_text += '.'

        return clean_text

    except Exception as e:
        print(f"⚠️ Punctuation failed: {e}")
        fallback = text.strip()
        return fallback[0].upper() + fallback[1:] + '.' if fallback else text

def create_semantic_chunks(blocks, target_length=30, max_length=60):
    """Create chunks by combining multiple blocks to reach target length"""
    chunks = []
    current_chunk = {
        'text': '',
        'start': None,
        'blocks': []
    }
    word_count = 0

    for block in blocks:
        punctuated_text = add_punctuation(block['text'])
        block_words = len(punctuated_text.split())

        if current_chunk['start'] is None:
            current_chunk['start'] = block['start']

        if word_count > 0 and (word_count + block_words > target_length or word_count > max_length):
            current_chunk['end'] = current_chunk['blocks'][-1]['end']
            current_chunk['duration'] = current_chunk['end'] - current_chunk['start']
            current_chunk['text'] = ' '.join([add_punctuation(b['text']) for b in current_chunk['blocks']])
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
    """Split blocks that are too long into smaller pieces"""
    result = []

    for block in blocks:
        block_words = len(block['text'].split())
        if block['end'] - block['start'] <= max_duration and block_words <= max_words:
            result.append(block)
            continue

        text = block['text']
        sentences = sent_tokenize(text) if text else [text]

        if len(sentences) <= 1:
            words = text.split()
            sentences = []
            for i in range(0, len(words), max_words // 2):
                sentences.append(' '.join(words[i:i + max_words // 2]))

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
    """Process a complete caption file"""
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
    captions_dir = Path("data/captions")
    chunks_dir = Path("data/chunks")
    chunks_dir.mkdir(parents=True, exist_ok=True)

    caption_files = sorted(captions_dir.glob("*.json"))

    if not caption_files:
        print("❌ No caption files found in data/captions/")
        exit(1)

    print(f"🔍 Found {len(caption_files)} caption files")
    new_files_found = False
    processed_count = 0

    for input_file in caption_files:
        output_file = chunks_dir / f"processed_{input_file.stem}.json"

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
        word_counts = [len(chunk['text'].split()) for chunk in chunks]
        durations = [chunk['duration'] for chunk in chunks]

        print(f"Total chunks: {len(chunks)}")
        print(f"Word count - Min: {min(word_counts)}, Max: {max(word_counts)}, Avg: {sum(word_counts)/len(word_counts):.1f}")
        print(f"Duration - Min: {min(durations):.1f}s, Max: {max(durations):.1f}s, Avg: {sum(durations)/len(durations):.1f}s")

    if not new_files_found:
        print("\n✅ No new caption files to process. All files are up to date!")
    else:
        print(f"\n🎉 Processing complete! Processed {processed_count} files.")
