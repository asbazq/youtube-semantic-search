import unittest

from scripts.preprocess_captions import (
    combine_caption_segments,
    create_semantic_chunks,
    split_long_blocks,
    split_korean_sentences,
)


class PreprocessCaptionsTest(unittest.TestCase):
    def test_splits_unpunctuated_korean_at_sentence_endings(self):
        text = "앞으로 밀릴 수밖에 없게 됩니다 다음 동작을 시작해 보세요 마지막 설명입니다"

        self.assertEqual(
            split_korean_sentences(text),
            [
                "앞으로 밀릴 수밖에 없게 됩니다.",
                "다음 동작을 시작해 보세요.",
                "마지막 설명입니다.",
            ],
        )

    def test_splits_plain_korean_endings_and_adds_periods(self):
        text = "중심을 아래로 내린다 그러면 자세가 안정된다 통증은 없다"

        self.assertEqual(
            split_korean_sentences(text),
            ["중심을 아래로 내린다.", "그러면 자세가 안정된다.", "통증은 없다."],
        )

    def test_preserves_existing_caption_punctuation(self):
        text = "중심을 잡는다. 다음 자세인가요? 그대로 내려간다!"

        self.assertEqual(
            split_korean_sentences(text),
            ["중심을 잡는다.", "다음 자세인가요?", "그대로 내려간다!"],
        )

    def test_splits_haeyo_style_endings_without_splitting_yo_nouns(self):
        text = "무릎을 조금 굽혀요 그러면 중심이 편해져요 이 동작은 필요 없어요"

        self.assertEqual(
            split_korean_sentences(text),
            ["무릎을 조금 굽혀요.", "그러면 중심이 편해져요.", "이 동작은 필요 없어요."],
        )

    def test_short_auto_caption_duration_extends_to_next_segment(self):
        segments = [
            {"text": "첫 자막", "start": 1.0, "duration": 0.5},
            {"text": "다음 자막", "start": 3.0, "duration": 0.5},
        ]

        blocks = combine_caption_segments(segments)

        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["text"], "첫 자막 다음 자막")

    def test_does_not_bridge_a_long_silence(self):
        segments = [
            {"text": "첫 발화", "start": 1.0, "duration": 0.5},
            {"text": "다음 발화", "start": 20.0, "duration": 0.5},
        ]

        self.assertEqual(len(combine_caption_segments(segments)), 2)

    def test_semantic_chunks_do_not_repeat_previous_sentence(self):
        blocks = [
            {"text": "첫 번째 문장 " * 15, "start": 0.0, "end": 10.0},
            {"text": "두 번째 문장 " * 15, "start": 10.0, "end": 20.0},
        ]

        chunks = create_semantic_chunks(blocks, target_length=25, max_length=50)

        self.assertEqual(len(chunks), 2)
        self.assertNotIn("첫 번째", chunks[1]["text"])

    def test_short_block_still_splits_on_sentence_boundaries(self):
        blocks = [{
            "text": "허리는 불편해집니다 자세를 낮춰야 합니다 내려가 보세요",
            "start": 0.0,
            "end": 12.0,
        }]

        split_blocks = split_long_blocks(blocks)

        self.assertEqual(len(split_blocks), 3)
        self.assertEqual(split_blocks[0]["text"], "허리는 불편해집니다.")

    def test_very_long_sentence_uses_bounded_fallback(self):
        blocks = [{
            "text": "단어 " * 121,
            "start": 0.0,
            "end": 60.0,
        }]

        split_blocks = split_long_blocks(blocks, max_words=80)

        self.assertEqual([len(block["text"].split()) for block in split_blocks], [40, 40, 40, 1])


if __name__ == "__main__":
    unittest.main()
