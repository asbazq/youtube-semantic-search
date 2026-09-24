"""로컬 Ollama HTTP API 어댑터.

브라우저는 FastAPI만 호출한다. 생성 모델의 주소와 모델 이름은 서버 환경변수로
관리하므로 Docker 실행과 PC에서 직접 실행할 때 같은 챗봇 코드를 쓸 수 있다.
"""

import json
import os
import socket
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ModelUnavailable(RuntimeError):
    """Ollama 서버·모델 연결 실패를 API의 HTTP 503으로 전달하기 위한 오류."""


class OllamaClient:
    def __init__(self, base_url=None, model=None, timeout=120):
        # PC 직접 실행: 127.0.0.1 / Compose 실행: 서비스 이름 ollama.
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
        self.timeout = timeout

    def chat(self, messages, *, tools=None, response_format=None):
        """Ollama /api/chat의 message만 반환한다.

        tools는 함수 설명서를 보내는 Tool Binding, response_format은 JSON Schema
        구조화 출력에 대응한다. stream=False여야 단일 JSON 응답을 읽을 수 있다.
        """
        payload = {"model": self.model, "messages": messages, "stream": False,
                   "options": {"temperature": 0}}
        if tools is not None:
            payload["tools"] = tools
        if response_format is not None:
            payload["format"] = response_format
        request = Request(
            self.base_url + "/api/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        for attempt in range(2):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    body = json.load(response)
                message = body.get("message")
                if not isinstance(message, dict):
                    raise ModelUnavailable("로컬 모델이 올바른 응답을 반환하지 않았습니다.")
                return message
            except HTTPError as error:
                if error.code == 404:
                    # 모델이 없을 때 같은 요청을 재시도해도 해결되지 않는다.
                    raise ModelUnavailable(
                        f"Ollama 모델 '{self.model}'을 찾을 수 없습니다. "
                        f"ollama pull {self.model} 명령으로 설치해 주세요."
                    ) from error
                if error.code not in (429, 500, 502, 503, 504) or attempt:
                    raise ModelUnavailable("로컬 모델 요청에 실패했습니다.") from error
            except (URLError, socket.timeout, TimeoutError, OSError) as error:
                if attempt:
                    raise ModelUnavailable(
                        "Ollama에 연결할 수 없습니다. Ollama 서버 실행 상태를 확인해 주세요."
                    ) from error
            # 일시적인 연결 문제/서버 오류만 최대 한 번 더 시도한다.
            time.sleep(0.3)
        raise ModelUnavailable("로컬 모델 요청에 실패했습니다.")
