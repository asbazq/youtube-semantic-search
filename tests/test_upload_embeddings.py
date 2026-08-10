import unittest

from db.upload_embeddings import prepare_chunks_for_chroma


class UploadEmbeddingsTest(unittest.TestCase):
    def test_display_text_does_not_join_neighboring_chunks(self):
        chunks = [
            {"text": "첫 문장입니다.", "start": 0.0, "end": 5.0, "embedding": [0.1]},
            {"text": "다음 문장입니다.", "start": 5.0, "end": 10.0, "embedding": [0.2]},
        ]

        records = prepare_chunks_for_chroma(chunks, "제목", "video-id", "source.json")

        self.assertEqual(records[0]["metadata"]["text"], "첫 문장입니다.")
        self.assertEqual(records[0]["metadata"]["end_time"], 5.0)
        self.assertEqual(records[1]["metadata"]["text"], "다음 문장입니다.")


if __name__ == "__main__":
    unittest.main()
