"""Vue 프론트엔드가 사용하는 YouTube 자막 의미 검색 HTTP API.

이 모듈의 역할은 크게 다음 다섯 가지다.

1. 관리자 로그인과 Bearer 토큰 인증
2. 저장된 영상 목록 조회와 자막 의미 검색
3. 단일 영상, 여러 영상, 재생목록의 백그라운드 등록
4. 등록 작업의 진행 개수와 예상 남은 시간 조회
5. ChromaDB에 저장된 특정 영상의 검색 데이터 삭제

개발 환경에서는 ``uvicorn api:app --reload``로 실행한다. Docker에서는
Dockerfile의 CMD가 같은 ``app`` 객체를 0.0.0.0:8000에서 실행한다.
"""

# hmac.compare_digest는 로그인 문자열 비교 시 일반 == 비교보다 타이밍 공격에
# 덜 민감한 비교 함수다.
import hmac
import logging
import os
# secrets는 예측하기 어려운 관리자 세션 토큰을 만드는 표준 라이브러리다.
import secrets
# lru_cache는 무거운 검색 엔진 객체를 요청마다 다시 만들지 않도록 캐시한다.
from functools import lru_cache
# monotonic은 시스템 시각 변경에 영향을 받지 않는 경과 시간 측정용 시계다.
from time import monotonic
# uuid4는 일괄 등록 작업마다 충돌 가능성이 매우 낮은 작업 ID를 만든다.
from uuid import uuid4

# BackgroundTasks: HTTP 응답 후 처리할 함수를 등록한다.
# Depends: 엔드포인트 실행 전에 관리자 인증 같은 의존 함수를 실행한다.
# Header: Authorization 같은 HTTP 헤더 값을 함수 인자로 받는다.
# HTTPException: 원하는 HTTP 상태 코드와 오류 메시지로 요청을 중단한다.
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
# BaseModel은 요청 JSON을 Python 객체로 변환하고, Field는 길이와 범위를 검증한다.
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# 실제 영상 처리 파이프라인과 YouTube URL 정규화는 main.py의 함수를 재사용한다.
from main import full_pipeline, get_playlist_videos, normalize_video_id
# 검색 모델 로딩과 ChromaDB 조회를 담당하는 클래스다.
from search.semantic_search import YouTubeSemanticSearch
from chatbot.ollama_client import ModelUnavailable, OllamaClient
from chatbot.service import ChatService, InvalidModelOutput, SearchFailure
from utils.logging_config import configure_error_file_logging

# 프로젝트 루트의 .env 값을 os.environ에 넣는다. 이미 설정된 환경변수는 기본적으로
# 덮어쓰지 않으므로 Docker Compose에서 전달한 값도 그대로 유지된다.
load_dotenv()
configure_error_file_logging()
logger = logging.getLogger(__name__)

# FastAPI 애플리케이션 객체다. title과 version은 /docs의 OpenAPI 문서에도 표시된다.
app = FastAPI(title="Rhino Strength Search API", version="1.0.0")

# 로컬 개발에서는 Vue 개발 서버(5173)와 API 서버(8000)의 출처가 다르기 때문에
# 브라우저의 동일 출처 정책을 통과하도록 CORS를 허용한다. Docker 배포에서는
# Nginx가 같은 출처의 /api 요청을 프록시하므로 이 설정에 의존하지 않는다.
app.add_middleware(
    CORSMiddleware,
    # 임의의 사이트가 아니라 로컬 Vue 개발 서버 두 주소만 허용한다.
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    # 쿠키나 Authorization 정보를 포함한 요청도 처리할 수 있게 한다.
    allow_credentials=True,
    # GET, POST, DELETE 등을 모두 허용한다.
    allow_methods=["*"],
    # Content-Type, Authorization 등을 포함한 모든 요청 헤더를 허용한다.
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    """POST /api/search가 받는 JSON 본문의 형식과 검증 규칙."""

    # 공백 제거 전 기준으로 1~300자만 받는다. 공백뿐인 값은 엔드포인트에서
    # strip() 후 한 번 더 검사한다.
    query: str = Field(min_length=1, max_length=300)
    # 값이 없으면 모든 영상에서, 값이 있으면 해당 video_id 안에서만 검색한다.
    video_id: str | None = None
    # 반환할 최대 검색 결과 수이며 기본 10개, 허용 범위는 1~30개다.
    top_k: int = Field(default=10, ge=1, le=30)


class ChatRequest(BaseModel):
    """패턴 ②: 브라우저 입력을 검증하는 요청 스키마.

    session_id는 대화 기록의 키이고 video_id는 검색 범위다. 모델이 반환하는
    citations JSON 스키마는 chatbot/service.py의 ANSWER_SCHEMA에 따로 있다.
    """

    question: str = Field(min_length=1, max_length=300)
    session_id: str = Field(min_length=8, max_length=80)
    video_id: str | None = Field(default=None, max_length=80)


class VideoRequest(BaseModel):
    """영상 한 개를 등록할 때 필요한 YouTube 주소/ID와 표시 제목."""

    url: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=120)


class VideoBatchRequest(BaseModel):
    """일괄 등록 요청 형식. 한 HTTP 요청에서 최대 100개까지 허용한다."""

    videos: list[VideoRequest] = Field(min_items=1, max_items=100)


class PlaylistRequest(BaseModel):
    """재생목록 등록 요청 형식. 전체 URL 또는 재생목록 ID를 받을 수 있다."""

    url: str = Field(min_length=1)


class LoginRequest(BaseModel):
    """관리자 로그인 요청 형식."""

    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


# 아래 딕셔너리들은 별도 DB가 아닌 현재 Python 프로세스의 메모리에만 존재한다.
# 따라서 API 서버가 재시작되거나 여러 worker로 실행되면 상태가 유지·공유되지 않는다.

# 영상 ID별 단건 상태를 저장한다.
# 예: {"abc123": {"status": "processing", "title": "스쿼트 강의"}}
processing_jobs: dict[str, dict[str, str]] = {}

# 일괄/재생목록 작업 ID별 집계 상태를 저장한다.
# total, processed, completed, failed, progress, remaining_seconds 등이 들어간다.
import_jobs: dict[str, dict] = {}

# 재생목록 작업도 import_jobs와 같은 구조를 쓰므로 복사본이 아니라 동일한
# 딕셔너리를 가리키는 별칭(alias)으로 둔다.
playlist_jobs = import_jobs

# 로그인 토큰을 키로 하고 사용자명과 역할을 값으로 저장한다.
# 만료 시간은 현재 구현되어 있지 않으며 로그아웃 또는 서버 재시작 때 제거된다.
admin_sessions: dict[str, dict[str, str]] = {}


def require_admin(authorization: str | None = Header(default=None)):
    """Authorization 헤더의 Bearer 토큰을 검사하는 FastAPI 의존 함수.

    엔드포인트 인자에 ``Depends(require_admin)``가 있으면 FastAPI가 실제
    엔드포인트보다 이 함수를 먼저 실행한다. 반환된 세션은 해당 인자로 전달된다.
    """
    # 헤더가 없거나 표준 "Bearer 토큰" 형식이 아니면 로그인하지 않은 요청이다.
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="관리자 로그인이 필요합니다.")

    # "Bearer " 접두사와 주변 공백을 제거해 로그인 시 발급한 원본 토큰을 얻는다.
    session = admin_sessions.get(authorization.removeprefix("Bearer ").strip())

    # 토큰을 찾을 수 없거나 ADMIN 역할이 아니면 권한 부족으로 거부한다.
    if not session or session.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="ADMIN 권한이 필요합니다.")

    # 인증된 세션을 반환하면 Depends를 선언한 엔드포인트가 이 값을 받을 수 있다.
    return session


@lru_cache(maxsize=1)
def get_engine() -> YouTubeSemanticSearch:
    """검색 엔진과 무거운 임베딩 모델을 서버 프로세스당 한 번만 생성한다.

    첫 검색/영상 목록 요청에서 객체가 생성되므로 첫 요청은 모델 로딩 때문에
    느릴 수 있다. 이후에는 ``lru_cache(maxsize=1)``가 같은 객체를 반환한다.
    """
    return YouTubeSemanticSearch()


@lru_cache(maxsize=1)
def get_chat_service() -> ChatService:
    """검색 엔진·대화 메모리를 요청마다 새로 만들지 않고 재사용한다.

    프로세스가 재시작되면 SessionMemory의 대화는 사라진다.
    """
    return ChatService(get_engine(), OllamaClient())


@app.get("/api/health")
def health():
    """프로세스가 HTTP 요청에 응답 가능한지 확인하는 가벼운 상태 점검 API."""

    # 모델이나 ChromaDB를 열지 않으므로 Docker healthcheck가 빠르게 확인할 수 있다.
    return {"status": "ok"}


@app.post("/api/auth/login")
def login(payload: LoginRequest):
    """환경변수의 관리자 계정과 비교해 임시 Bearer 토큰을 발급한다."""

    # 비밀번호를 코드나 DB에 두지 않고 .env/Docker 환경변수에서 읽는다.
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")

    # 서버 운영자가 계정을 설정하지 않았다면 인증 자체가 준비되지 않은 상태다.
    if not admin_username or not admin_password:
        raise HTTPException(status_code=503, detail="관리자 계정이 설정되지 않았습니다.")

    # 사용자명과 비밀번호가 모두 일치해야 한다. compare_digest는 문자열 비교에
    # 걸리는 시간 차이로 비밀값을 추측하는 공격 가능성을 낮춘다.
    valid = hmac.compare_digest(payload.username, admin_username) and hmac.compare_digest(
        payload.password, admin_password
    )
    if not valid:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

    # URL에 사용해도 안전한 무작위 토큰을 만들고 서버 메모리에 세션을 등록한다.
    token = secrets.token_urlsafe(32)
    admin_sessions[token] = {"username": admin_username, "role": "ADMIN"}

    # 프론트는 access_token을 localStorage에 저장한 뒤 후속 요청의
    # Authorization: Bearer <token> 헤더에 넣는다.
    return {"access_token": token, "token_type": "bearer", "role": "ADMIN", "username": admin_username}


@app.get("/api/auth/me")
def me(admin=Depends(require_admin)):
    """현재 토큰이 유효한지 확인하고 로그인한 관리자 정보를 반환한다."""

    # admin은 require_admin이 검증을 끝낸 뒤 반환한 세션 딕셔너리다.
    return admin


@app.post("/api/auth/logout", status_code=204)
def logout(authorization: str | None = Header(default=None)):
    """현재 Bearer 토큰을 서버 메모리에서 제거해 로그아웃한다."""

    if authorization and authorization.startswith("Bearer "):
        # pop의 기본값 None 덕분에 이미 없는 토큰도 오류 없이 처리된다.
        admin_sessions.pop(authorization.removeprefix("Bearer ").strip(), None)


@app.get("/api/videos")
def videos():
    """ChromaDB 메타데이터를 바탕으로 검색 가능한 영상 목록을 반환한다."""

    return {"videos": get_engine().get_video_list()}


@app.post("/api/search")
def search(payload: SearchRequest):
    """질문을 임베딩하고 ChromaDB에서 의미가 가까운 자막 조각을 검색한다."""

    # 앞뒤 공백을 제거한다. Pydantic의 min_length를 통과한 "   " 같은 입력도
    # 실제 검색어가 비었으면 422로 거부한다.
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="검색어를 입력해 주세요.")

    # video_id 유무에 따라 특정 영상 제한 검색과 전체 영상 검색을 나눈다.
    if payload.video_id:
        result = get_engine().search_by_video(query, payload.video_id, payload.top_k)
    else:
        result = get_engine().search(query, payload.top_k)

    # 검색 계층이 예외 대신 {"error": "..."}를 반환한 경우 HTTP 500으로 변환한다.
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@app.post("/api/chat")
def chat(payload: ChatRequest):
    """자막을 근거로 로컬 Ollama 모델이 답변한다.

    422=입력 문제, 503=로컬 모델 연결/설치 문제, 502=모델 출력 형식 문제,
    500=검색 문제로 구분해 화면에서 원인을 알 수 있게 한다.
    """
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="질문을 입력해 주세요.")
    try:
        return get_chat_service().ask(question, payload.session_id, payload.video_id)
    except ModelUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except InvalidModelOutput as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except SearchFailure as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.delete("/api/chat/sessions/{session_id}", status_code=204)
def clear_chat_session(session_id: str):
    """Let the browser discard an in-memory conversation."""
    get_chat_service().memory.clear(session_id)


def process_video(video_id: str, title: str):
    """단일 영상을 백그라운드에서 처리하고 영상별 상태를 갱신한다."""

    # full_pipeline은 자막 다운로드 → 전처리 → 임베딩 → ChromaDB 업로드를 수행한다.
    processing_jobs[video_id] = {"status": "processing", "title": title}
    try:
        succeeded = full_pipeline(video_id, title)
        processing_jobs[video_id]["status"] = "complete" if succeeded else "failed"
        if not succeeded:
            logger.error("영상 분석 실패: video_id=%s title=%r", video_id, title)
    except Exception:
        # 백그라운드 예외가 작업 상태를 영원히 processing으로 남기지 않게 한다.
        processing_jobs[video_id]["status"] = "failed"
        logger.exception("영상 분석 중 예외 발생: video_id=%s title=%r", video_id, title)


def process_many(videos: list[tuple[str, str]], job_id: str):
    """여러 영상을 순서대로 처리하면서 개수, 진행률, 예상 시간을 기록한다.

    ``import_jobs``는 프론트엔드가 작업 상태를 조회할 때 사용하는 메모리 저장소다.
    이 함수가 여기의 값을 계속 갱신하고, ``GET /api/import-jobs/{job_id}``가
    현재 값을 반환한다. 서버를 재시작하면 메모리에 있던 작업 상태는 사라진다.
    """
    job = import_jobs[job_id]

    # 작업 시작 시 전체 영상 개수를 확정하고 각 집계 값을 0으로 초기화한다.
    # total: 전체 처리 대상, processed: 성공 여부와 관계없이 처리가 끝난 개수
    # completed: 성공 개수, failed: 실패 개수
    job.update(status="processing", total=len(videos), processed=0, completed=0, failed=0)

    # monotonic()은 시스템 시계가 변경되어도 항상 앞으로 증가하는 타이머다.
    # 작업 시작 후 실제로 몇 초가 흘렀는지 계산하는 용도로 사용한다.
    started_at = monotonic()

    # enumerate(..., 1)을 사용하므로 index는 0이 아니라 1부터 시작한다.
    # 예: 영상이 10개라면 index는 1, 2, ..., 10 순서로 증가한다.
    for index, (video_id, title) in enumerate(videos, 1):
        # 현재 영상을 시작하기 직전의 진행률이다.
        # 첫 영상 시작 전에는 (1 - 1) / 전체 = 0%, 두 번째 시작 전에는
        # 1 / 전체가 된다. current_title은 화면에 현재 처리 중인 제목으로 표시된다.
        job.update(current_title=title, current=index, progress=round((index - 1) / len(videos) * 100))
        processing_jobs[video_id] = {"status": "processing", "title": title}
        try:
            succeeded = full_pipeline(video_id, title)
        except Exception:
            succeeded = False
            logger.exception(
                "일괄 영상 분석 중 예외 발생: job_id=%s video_id=%s title=%r",
                job_id, video_id, title,
            )
        processing_jobs[video_id]["status"] = "complete" if succeeded else "failed"
        if not succeeded:
            logger.error(
                "일괄 영상 분석 실패: job_id=%s video_id=%s title=%r",
                job_id, video_id, title,
            )

        # 영상 하나의 전체 파이프라인이 끝난 후 성공/실패 개수를 하나 증가시킨다.
        job["completed" if succeeded else "failed"] += 1

        # 실패한 영상도 시도와 처리가 끝난 것이므로 processed에 포함한다.
        # 따라서 화면에 표시되는 "processed / total"은 성공 개수만 뜻하지 않는다.
        job["processed"] = index

        # 지금까지 모든 영상을 처리하는 데 걸린 누적 시간(초)이다.
        elapsed = monotonic() - started_at
        job.update(
            elapsed_seconds=round(elapsed),

            # 예상 남은 시간 계산식:
            #   지금까지 영상당 평균 처리 시간 × 아직 처리하지 않은 영상 개수
            # = (누적 시간 / 처리한 개수) × (전체 개수 - 처리한 개수)
            #
            # 예: 5개 처리에 100초가 걸렸고 총 20개라면
            #     (100 / 5) × (20 - 5) = 약 300초가 남았다고 예상한다.
            # 영상마다 자막 길이와 네트워크 속도가 달라 초반 예상치는 흔들릴 수 있다.
            remaining_seconds=round((elapsed / index) * (len(videos) - index)),

            # 방금 끝난 영상까지 반영한 진행률이다.
            # 마지막 영상에서는 전체/전체 × 100이므로 정확히 100이 된다.
            progress=round(index / len(videos) * 100),
        )

    # 모든 영상을 시도한 뒤 실패가 하나도 없으면 complete, 하나라도 있으면
    # partial로 기록한다. 작업이 끝났으므로 현재 제목은 비우고 남은 시간은 0이다.
    job.update(
        status="complete" if job["failed"] == 0 else "partial",
        current_title="",
        remaining_seconds=0,
    )


def process_playlist(playlist_url: str, job_id: str):
    """재생목록의 영상 목록을 먼저 읽은 뒤 공통 일괄 처리 함수에 넘긴다."""

    job = import_jobs[job_id]

    # 영상 수를 아직 모르므로 processing 전에 목록을 읽는 reading 상태로 둔다.
    job["status"] = "reading"
    try:
        # yt-dlp의 flat-playlist 기능으로 영상 파일은 받지 않고 ID와 제목만 얻는다.
        playlist_videos = get_playlist_videos(playlist_url)
        if not playlist_videos:
            job.update(status="failed", error="재생목록에서 영상을 찾지 못했습니다.")
            return

        # [(video_id, title), ...] 형식은 수동 일괄 등록과 동일하므로 처리 로직을 공유한다.
        process_many(playlist_videos, job_id)
    except Exception:
        # 내부 예외 상세를 사용자에게 노출하지 않고 작업 상태와 일반 메시지만 기록한다.
        job.update(status="failed", error="재생목록 처리 중 오류가 발생했습니다.")
        logger.exception("재생목록 처리 중 예외 발생: job_id=%s url=%s", job_id, playlist_url)


@app.post("/api/videos", status_code=202)
def add_video(payload: VideoRequest, background_tasks: BackgroundTasks, _admin=Depends(require_admin)):
    """영상 한 개를 처리 대기열에 등록하고 즉시 HTTP 202를 반환한다.

    ``_admin``은 함수 본문에서 값을 쓰지는 않지만, Depends가 먼저 실행되므로
    유효한 관리자만 이 엔드포인트에 접근할 수 있다. 앞의 밑줄은 의도적으로
    사용하지 않는 인자라는 Python 관례다.
    """
    # 전체 YouTube URL, youtu.be 주소 또는 순수 ID를 공통 영상 ID로 변환한다.
    video_id = normalize_video_id(payload.url)
    title = payload.title.strip()

    # 정규화 결과나 공백 제거 후 제목이 비면 처리할 수 없는 요청이다.
    if not video_id or not title:
        raise HTTPException(status_code=422, detail="YouTube URL과 제목을 확인해 주세요.")

    # 동일 영상의 파이프라인을 동시에 두 번 실행하는 것을 방지한다.
    if processing_jobs.get(video_id, {}).get("status") == "processing":
        raise HTTPException(status_code=409, detail="이미 처리 중인 영상입니다.")

    # 응답 전에 queued 상태를 기록해 후속 상태 조회가 즉시 가능하게 한다.
    processing_jobs[video_id] = {"status": "queued", "title": title}

    # FastAPI는 아래 함수를 HTTP 응답을 보낸 뒤 실행한다. 따라서 자막 분석이
    # 오래 걸려도 이 요청은 완료를 기다리지 않고 202 Accepted를 반환한다.
    background_tasks.add_task(process_video, video_id, title)
    return {"video_id": video_id, "status": "queued"}


@app.post("/api/videos/batch", status_code=202)
def add_videos(payload: VideoBatchRequest, background_tasks: BackgroundTasks, _admin=Depends(require_admin)):
    """사용자가 입력한 여러 영상을 검증·중복 제거한 뒤 순차 처리한다."""

    # queued에는 실제 처리할 항목, skipped에는 제외된 항목과 이유를 넣는다.
    queued = []
    skipped = []

    # 한 요청 본문 안에서 같은 video_id가 반복되는지 빠르게 확인하는 집합이다.
    seen = set()

    for item in payload.videos:
        video_id = normalize_video_id(item.url)
        title = item.title.strip()
        if not video_id or not title:
            raise HTTPException(status_code=422, detail="영상 URL/ID와 제목을 확인해 주세요.")

        # 이번 요청 안에서 이미 나온 ID라면 첫 항목만 남기고 duplicate로 제외한다.
        if video_id in seen:
            skipped.append({"video_id": video_id, "reason": "duplicate"})
            continue
        seen.add(video_id)

        # 이전 요청으로 이미 대기 또는 처리 중인 영상도 중복 실행하지 않는다.
        if processing_jobs.get(video_id, {}).get("status") in {"queued", "processing"}:
            skipped.append({"video_id": video_id, "reason": "already_queued"})
            continue

        # 검증을 통과한 영상은 영상별 상태와 일괄 처리 목록 양쪽에 등록한다.
        processing_jobs[video_id] = {"status": "queued", "title": title}
        queued.append({"video_id": video_id, "title": title, "status": "queued"})

    # 프론트가 이 일괄 작업만 지속적으로 조회할 수 있도록 고유 ID를 생성한다.
    job_id = uuid4().hex

    # remaining_seconds가 None이면 첫 영상이 끝나지 않아 평균 시간을 아직 계산할
    # 수 없다는 뜻이며, 프론트에서는 "계산 중…"으로 표시한다.
    import_jobs[job_id] = {
        "status": "queued", "total": len(queued), "processed": 0, "completed": 0,
        "failed": 0, "progress": 0, "remaining_seconds": None, "current_title": "",
    }
    if queued:
        # process_many이 요구하는 [(video_id, title), ...] 튜플 목록으로 변환한다.
        # 이 함수는 영상을 동시에 처리하지 않고 입력 순서대로 하나씩 처리한다.
        background_tasks.add_task(
            process_many,
            [(item["video_id"], item["title"]) for item in queued],
            job_id,
        )
    else:
        # 모든 항목이 중복 등으로 제외됐다면 실행할 작업이 없으므로 즉시 완료한다.
        import_jobs[job_id]["status"] = "complete"

    # queued/skipped를 같이 반환해 프론트가 등록 수와 제외 수를 알 수 있게 한다.
    return {"job_id": job_id, "queued": queued, "skipped": skipped, "total_queued": len(queued)}


@app.post("/api/playlists", status_code=202)
def add_playlist(payload: PlaylistRequest, background_tasks: BackgroundTasks, _admin=Depends(require_admin)):
    """YouTube 재생목록 URL/ID를 받아 모든 공개 영상을 순차 처리한다."""

    # 이 엔드포인트에서만 사용하는 모듈이라 함수가 호출될 때 지역 import한다.
    import re
    from urllib.parse import parse_qs, urlparse

    # 사용자가 복사 과정에서 함께 넣은 공백이나 따옴표를 제거한다.
    playlist_input = payload.url.strip().strip('"').strip("'")
    if "://" in playlist_input:
        # 전체 URL이면 ?list= 뒤의 재생목록 ID만 추출한다.
        # get(..., [""])[0]은 list 파라미터가 없을 때 빈 문자열을 안전하게 얻는다.
        playlist_id = parse_qs(urlparse(playlist_input).query).get("list", [""])[0]
    else:
        # 순수 ID와 "list=ID" 형식을 모두 허용한다.
        playlist_id = playlist_input.removeprefix("list=")

    # YouTube ID에서 사용하는 영문, 숫자, 밑줄, 하이픈 이외의 문자를 거부해
    # 잘못된 URL이나 명령 문자열 등이 후속 yt-dlp 호출로 넘어가지 않게 한다.
    if not playlist_id or not re.fullmatch(r"[A-Za-z0-9_-]+", playlist_id):
        raise HTTPException(status_code=422, detail="YouTube 재생목록 URL 또는 재생목록 ID를 입력해 주세요.")

    # 검증한 ID로 표준 YouTube 재생목록 URL을 다시 만든다.
    playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"

    # 같은 재생목록이 이미 대기/조회/처리 중이면 중복 등록을 거부한다.
    if playlist_jobs.get(playlist_id, {}).get("status") in {"queued", "reading", "processing"}:
        raise HTTPException(status_code=409, detail="이미 처리 중인 재생목록입니다.")

    # 아직 영상 목록을 읽기 전이므로 total은 0이다. process_playlist가 목록을
    # 구한 뒤 process_many을 호출하면 실제 전체 개수로 갱신된다.
    import_jobs[playlist_id] = {
        "status": "queued", "total": 0, "processed": 0, "completed": 0,
        "failed": 0, "progress": 0, "remaining_seconds": None, "current_title": "",
    }

    # 재생목록 조회와 전체 영상 처리는 오래 걸릴 수 있으므로 응답 후 실행한다.
    background_tasks.add_task(process_playlist, playlist_url, playlist_id)

    # 재생목록에서는 playlist_id 자체를 상태 조회용 job_id로 재사용한다.
    return {"job_id": playlist_id, "playlist_id": playlist_id, "status": "queued"}


@app.get("/api/playlist-jobs/{playlist_id}")
def playlist_job(playlist_id: str):
    """재생목록 ID에 해당하는 현재 작업 상태를 반환한다."""

    if playlist_id not in playlist_jobs:
        raise HTTPException(status_code=404, detail="재생목록 작업을 찾을 수 없습니다.")

    # **로 상태 딕셔너리의 필드를 응답 최상위에 펼친다.
    return {"playlist_id": playlist_id, **playlist_jobs[playlist_id]}


@app.get("/api/import-jobs/{job_id}")
def import_job(job_id: str):
    """일괄 또는 재생목록 가져오기 작업의 진행 상태를 반환한다.

    프론트엔드는 작업 중 이 API를 2초마다 호출하여 진행 바, 처리 개수,
    현재 제목과 예상 남은 시간을 갱신한다.
    """
    if job_id not in import_jobs:
        raise HTTPException(status_code=404, detail="가져오기 작업을 찾을 수 없습니다.")
    return {"job_id": job_id, **import_jobs[job_id]}


@app.delete("/api/videos/{video_id}", status_code=204)
def delete_video(video_id: str, _admin=Depends(require_admin)):
    """특정 영상의 검색 레코드를 ChromaDB에서 삭제한다.

    이 작업은 영상 파일을 삭제하는 것이 아니다. 이 프로젝트는 영상 파일을
    저장하지 않는다. 또한 현재 구현은 data/captions, data/chunks,
    data/embeddings의 중간 JSON 파일까지 지우지는 않는다.
    """
    # URL 형태로 전달된 경우에도 순수 ID로 맞춘다.
    normalized_id = normalize_video_id(video_id)
    if not normalized_id:
        raise HTTPException(status_code=422, detail="영상 ID를 확인해 주세요.")

    # ChromaDB metadata의 video_id가 정확히 일치하는 모든 자막 벡터를 삭제한다.
    get_engine().collection.delete(where={"video_id": {"$eq": normalized_id}})

    # 삭제된 영상에 대한 단건 작업 상태도 메모리에서 정리한다.
    processing_jobs.pop(normalized_id, None)


@app.get("/api/jobs/{video_id}")
def job(video_id: str):
    """단일 영상 등록 작업의 queued/processing/complete/failed 상태를 조회한다."""

    if video_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")

    # video_id와 저장된 title/status를 한 JSON 객체로 합쳐 반환한다.
    return {"video_id": video_id, **processing_jobs[video_id]}
