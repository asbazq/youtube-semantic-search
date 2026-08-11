"""Vue frontend에서 사용하는 YouTube semantic search HTTP API."""

import hmac
import os
import secrets
from functools import lru_cache
from time import monotonic
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from main import full_pipeline, get_playlist_videos, normalize_video_id
from search.semantic_search import YouTubeSemanticSearch

load_dotenv()

app = FastAPI(title="Rhino Strength Search API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    video_id: str | None = None
    top_k: int = Field(default=10, ge=1, le=30)


class VideoRequest(BaseModel):
    url: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=120)


class VideoBatchRequest(BaseModel):
    videos: list[VideoRequest] = Field(min_items=1, max_items=100)


class PlaylistRequest(BaseModel):
    url: str = Field(min_length=1)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


processing_jobs: dict[str, dict[str, str]] = {}
import_jobs: dict[str, dict] = {}
playlist_jobs = import_jobs
admin_sessions: dict[str, dict[str, str]] = {}


def require_admin(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="관리자 로그인이 필요합니다.")
    session = admin_sessions.get(authorization.removeprefix("Bearer ").strip())
    if not session or session.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="ADMIN 권한이 필요합니다.")
    return session


@lru_cache(maxsize=1)
def get_engine() -> YouTubeSemanticSearch:
    """무거운 임베딩 모델은 서버 실행 중 한 번만 로드한다."""
    return YouTubeSemanticSearch()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/login")
def login(payload: LoginRequest):
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_username or not admin_password:
        raise HTTPException(status_code=503, detail="관리자 계정이 설정되지 않았습니다.")
    valid = hmac.compare_digest(payload.username, admin_username) and hmac.compare_digest(
        payload.password, admin_password
    )
    if not valid:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
    token = secrets.token_urlsafe(32)
    admin_sessions[token] = {"username": admin_username, "role": "ADMIN"}
    return {"access_token": token, "token_type": "bearer", "role": "ADMIN", "username": admin_username}


@app.get("/api/auth/me")
def me(admin=Depends(require_admin)):
    return admin


@app.post("/api/auth/logout", status_code=204)
def logout(authorization: str | None = Header(default=None)):
    if authorization and authorization.startswith("Bearer "):
        admin_sessions.pop(authorization.removeprefix("Bearer ").strip(), None)


@app.get("/api/videos")
def videos():
    return {"videos": get_engine().get_video_list()}


@app.post("/api/search")
def search(payload: SearchRequest):
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="검색어를 입력해 주세요.")

    if payload.video_id:
        result = get_engine().search_by_video(query, payload.video_id, payload.top_k)
    else:
        result = get_engine().search(query, payload.top_k)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


def process_video(video_id: str, title: str):
    processing_jobs[video_id] = {"status": "processing", "title": title}
    try:
        succeeded = full_pipeline(video_id, title)
        processing_jobs[video_id]["status"] = "complete" if succeeded else "failed"
    except Exception:
        processing_jobs[video_id]["status"] = "failed"


def process_many(videos: list[tuple[str, str]], job_id: str):
    job = import_jobs[job_id]
    job.update(status="processing", total=len(videos), processed=0, completed=0, failed=0)
    started_at = monotonic()

    for index, (video_id, title) in enumerate(videos, 1):
        job.update(current_title=title, current=index, progress=round((index - 1) / len(videos) * 100))
        processing_jobs[video_id] = {"status": "processing", "title": title}
        try:
            succeeded = full_pipeline(video_id, title)
        except Exception:
            succeeded = False
        processing_jobs[video_id]["status"] = "complete" if succeeded else "failed"
        job["completed" if succeeded else "failed"] += 1
        job["processed"] = index
        elapsed = monotonic() - started_at
        job.update(
            elapsed_seconds=round(elapsed),
            remaining_seconds=round((elapsed / index) * (len(videos) - index)),
            progress=round(index / len(videos) * 100),
        )

    job.update(
        status="complete" if job["failed"] == 0 else "partial",
        current_title="",
        remaining_seconds=0,
    )


def process_playlist(playlist_url: str, job_id: str):
    job = import_jobs[job_id]
    job["status"] = "reading"
    try:
        playlist_videos = get_playlist_videos(playlist_url)
        if not playlist_videos:
            job.update(status="failed", error="재생목록에서 영상을 찾지 못했습니다.")
            return
        process_many(playlist_videos, job_id)
    except Exception:
        job.update(status="failed", error="재생목록 처리 중 오류가 발생했습니다.")


@app.post("/api/videos", status_code=202)
def add_video(payload: VideoRequest, background_tasks: BackgroundTasks, _admin=Depends(require_admin)):
    video_id = normalize_video_id(payload.url)
    title = payload.title.strip()
    if not video_id or not title:
        raise HTTPException(status_code=422, detail="YouTube URL과 제목을 확인해 주세요.")
    if processing_jobs.get(video_id, {}).get("status") == "processing":
        raise HTTPException(status_code=409, detail="이미 처리 중인 영상입니다.")

    processing_jobs[video_id] = {"status": "queued", "title": title}
    background_tasks.add_task(process_video, video_id, title)
    return {"video_id": video_id, "status": "queued"}


@app.post("/api/videos/batch", status_code=202)
def add_videos(payload: VideoBatchRequest, background_tasks: BackgroundTasks, _admin=Depends(require_admin)):
    queued = []
    skipped = []
    seen = set()

    for item in payload.videos:
        video_id = normalize_video_id(item.url)
        title = item.title.strip()
        if not video_id or not title:
            raise HTTPException(status_code=422, detail="영상 URL/ID와 제목을 확인해 주세요.")
        if video_id in seen:
            skipped.append({"video_id": video_id, "reason": "duplicate"})
            continue
        seen.add(video_id)
        if processing_jobs.get(video_id, {}).get("status") in {"queued", "processing"}:
            skipped.append({"video_id": video_id, "reason": "already_queued"})
            continue

        processing_jobs[video_id] = {"status": "queued", "title": title}
        queued.append({"video_id": video_id, "title": title, "status": "queued"})

    job_id = uuid4().hex
    import_jobs[job_id] = {
        "status": "queued", "total": len(queued), "processed": 0, "completed": 0,
        "failed": 0, "progress": 0, "remaining_seconds": None, "current_title": "",
    }
    if queued:
        background_tasks.add_task(
            process_many,
            [(item["video_id"], item["title"]) for item in queued],
            job_id,
        )
    else:
        import_jobs[job_id]["status"] = "complete"
    return {"job_id": job_id, "queued": queued, "skipped": skipped, "total_queued": len(queued)}


@app.post("/api/playlists", status_code=202)
def add_playlist(payload: PlaylistRequest, background_tasks: BackgroundTasks, _admin=Depends(require_admin)):
    import re
    from urllib.parse import parse_qs, urlparse

    playlist_input = payload.url.strip().strip('"').strip("'")
    if "://" in playlist_input:
        playlist_id = parse_qs(urlparse(playlist_input).query).get("list", [""])[0]
    else:
        playlist_id = playlist_input.removeprefix("list=")
    if not playlist_id or not re.fullmatch(r"[A-Za-z0-9_-]+", playlist_id):
        raise HTTPException(status_code=422, detail="YouTube 재생목록 URL 또는 재생목록 ID를 입력해 주세요.")
    playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
    if playlist_jobs.get(playlist_id, {}).get("status") in {"queued", "reading", "processing"}:
        raise HTTPException(status_code=409, detail="이미 처리 중인 재생목록입니다.")

    import_jobs[playlist_id] = {
        "status": "queued", "total": 0, "processed": 0, "completed": 0,
        "failed": 0, "progress": 0, "remaining_seconds": None, "current_title": "",
    }
    background_tasks.add_task(process_playlist, playlist_url, playlist_id)
    return {"job_id": playlist_id, "playlist_id": playlist_id, "status": "queued"}


@app.get("/api/playlist-jobs/{playlist_id}")
def playlist_job(playlist_id: str):
    if playlist_id not in playlist_jobs:
        raise HTTPException(status_code=404, detail="재생목록 작업을 찾을 수 없습니다.")
    return {"playlist_id": playlist_id, **playlist_jobs[playlist_id]}


@app.get("/api/import-jobs/{job_id}")
def import_job(job_id: str):
    if job_id not in import_jobs:
        raise HTTPException(status_code=404, detail="가져오기 작업을 찾을 수 없습니다.")
    return {"job_id": job_id, **import_jobs[job_id]}


@app.delete("/api/videos/{video_id}", status_code=204)
def delete_video(video_id: str, _admin=Depends(require_admin)):
    normalized_id = normalize_video_id(video_id)
    if not normalized_id:
        raise HTTPException(status_code=422, detail="영상 ID를 확인해 주세요.")
    get_engine().collection.delete(where={"video_id": {"$eq": normalized_id}})
    processing_jobs.pop(normalized_id, None)


@app.get("/api/jobs/{video_id}")
def job(video_id: str):
    if video_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    return {"video_id": video_id, **processing_jobs[video_id]}
