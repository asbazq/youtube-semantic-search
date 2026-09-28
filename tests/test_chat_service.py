"""실제 LLM 다운로드나 ChromaDB 없이 호출 순서와 폴백을 검증한다."""

import unittest

from chatbot.service import ChatService, InvalidModelOutput, SessionMemory


HIT = {
    "text": "데드리프트에서는 허리를 중립으로 유지합니다.",
    "video_id": "abc123",
    "video_title": "데드리프트 코칭",
    "start_time": 42,
    "end_time": 53,
    "score": 0.82,
    "youtube_url": "https://www.youtube.com/watch?v=abc123&t=42s",
}


class FakeSearch:
    """기존 검색기를 흉내 내고 전달된 검색어·영상 범위를 기록한다."""
    def __init__(self, hits):
        self.hits = hits
        self.calls = []

    def search(self, query, top_k):
        self.calls.append((query, None, top_k))
        return {"results": self.hits}

    def search_by_video(self, query, video_id, top_k):
        self.calls.append((query, video_id, top_k))
        return {"results": self.hits}


class FakeModel:
    """Ollama 응답을 순서대로 돌려 주어 도구 호출과 JSON 검증을 재현한다."""
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        return self.responses.pop(0)


class ChatServiceTests(unittest.TestCase):
    def test_tool_query_uses_selected_video_and_returns_existing_source(self):
        model = FakeModel(
            {"tool_calls": [{"function": {"name": "search_transcripts",
                                          "arguments": {"query": "데드리프트 허리 자세"}}}]},
            {"content": '{"answer":"허리를 중립으로 유지합니다.","citations":[1]}'},
        )
        search = FakeSearch([HIT])
        result = ChatService(search, model).ask("허리는 어떻게 해?", "session-1", "abc123")

        self.assertEqual(search.calls, [("데드리프트 허리 자세", "abc123", 6)])
        self.assertEqual(result["sources"], [HIT])
        self.assertEqual(result["citations"], [1])
        self.assertIn("tools", model.calls[0][1])
        self.assertIn("response_format", model.calls[1][1])

    def test_low_score_results_do_not_become_evidence(self):
        model = FakeModel({"content": "No tool call"})
        search = FakeSearch([{**HIT, "score": 0.2}])
        result = ChatService(search, model).ask("관련 없는 질문", "session-1")

        self.assertEqual(result["sources"], [])
        self.assertIn("확인하지 못했습니다", result["answer"])
        self.assertEqual(len(model.calls), 1)

    def test_invalid_source_number_is_retried_then_rejected(self):
        model = FakeModel({"content": "No tool call"},
                          {"content": '{"answer":"내용","citations":[9]}'},
                          {"content": '{"answer":"내용","citations":[9]}'})
        with self.assertRaises(InvalidModelOutput):
            ChatService(FakeSearch([HIT]), model).ask("질문", "session-1")
        self.assertEqual(len(model.calls), 3)

    def test_memory_is_bounded_and_isolated_by_video(self):
        memory = SessionMemory(max_sessions=2, max_turns=1)
        memory.add("alice", "video-a", "첫 질문", "첫 답변")
        memory.add("alice", "video-a", "다음 질문", "다음 답변")
        self.assertEqual(len(memory.get("alice", "video-a")), 2)
        self.assertEqual(memory.get("alice", "video-b"), [])
        memory.add("bob", None, "질문", "답변")
        memory.add("carol", None, "질문", "답변")
        self.assertEqual(memory.get("alice", "video-a"), [])


if __name__ == "__main__":
    unittest.main()
