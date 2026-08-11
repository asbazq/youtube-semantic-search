"""Vue frontend에서 사용하는 YouTube semantic search HTTP API."""

from functools import lru_cache

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from main import full_pipeline, normalize_video_id
from search.semantic_search import YouTubeSemanticSearch


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


processing_jobs: dict[str, dict[str, str]] = {}


@lru_cache(maxsize=1)
def get_engine() -> YouTubeSemanticSearch:
    """무거운 임베딩 모델은 서버 실행 중 한 번만 로드한다."""
    return YouTubeSemanticSearch()


@app.get("/api/health")
def health():
    return {"status": "ok"}


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


@app.post("/api/videos", status_code=202)
def add_video(payload: VideoRequest, background_tasks: BackgroundTasks):
    video_id = normalize_video_id(payload.url)
    title = payload.title.strip()
    if not video_id or not title:
        raise HTTPException(status_code=422, detail="YouTube URL과 제목을 확인해 주세요.")
    if processing_jobs.get(video_id, {}).get("status") == "processing":
        raise HTTPException(status_code=409, detail="이미 처리 중인 영상입니다.")

    processing_jobs[video_id] = {"status": "queued", "title": title}
    background_tasks.add_task(process_video, video_id, title)
    return {"video_id": video_id, "status": "queued"}


@app.get("/api/jobs/{video_id}")
def job(video_id: str):
    if video_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    return {"video_id": video_id, **processing_jobs[video_id]}
