import io
import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

from chatbot.ollama_client import ModelUnavailable, OllamaClient


class OllamaClientTests(unittest.TestCase):
    def test_generation_is_bounded_for_planning_and_answers(self):
        for tools, limit in [([], 128), (None, 512)]:
            with self.subTest(tools=tools), patch('chatbot.ollama_client.urlopen') as request:
                request.return_value = io.BytesIO(b'{"message":{"content":"ok"}}')
                OllamaClient().chat([], tools=tools)
                payload = json.loads(request.call_args.args[0].data)
                self.assertEqual(payload['options']['num_predict'], limit)

    def test_timeouts_are_not_retried(self):
        for error in [TimeoutError(), URLError(TimeoutError())]:
            with self.subTest(error=error), patch('chatbot.ollama_client.urlopen', side_effect=error) as request:
                with self.assertRaisesRegex(ModelUnavailable, '초과'):
                    OllamaClient().chat([])
                self.assertEqual(request.call_count, 1)

    def test_invalid_json_is_reported(self):
        with patch('chatbot.ollama_client.urlopen', return_value=io.BytesIO(b'not json')):
            with self.assertRaises(ModelUnavailable):
                OllamaClient().chat([])
