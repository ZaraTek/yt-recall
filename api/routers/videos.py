import asyncio
import logging
import time
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from auth import get_current_user
from db import get_db
from models import (
    ChatRequest,
    ChatResponse,
    NotesUpdate,
    Question,
    User,
    Video,
    VideoCreate,
    VideoSummary,
)
from services.gemini import (
    GeminiError,
    chat_about_video,
    generate_study_material,
    generate_study_material_from_url,
)
from services.transcript import (
    TranscriptError,
    extract_video_id,
    fetch_metadata,
    fetch_transcript,
)

router = APIRouter(prefix="/api/videos", tags=["videos"])

logger = logging.getLogger("yt_recall.videos")


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    doc.pop("user_id", None)
    return doc


def _parse_object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError) as exc:
        raise HTTPException(status_code=404, detail="Video not found") from exc


@router.get("", response_model=list[VideoSummary])
async def list_videos(user: User = Depends(get_current_user)):
    db = get_db()
    cursor = db.videos.find({"user_id": user.id}).sort("created_at", -1)
    return [VideoSummary(**_serialize(doc)) async for doc in cursor]


@router.post("", response_model=Video, status_code=status.HTTP_201_CREATED)
async def create_video(payload: VideoCreate, user: User = Depends(get_current_user)):
    db = get_db()

    try:
        video_id = extract_video_id(payload.url)
    except TranscriptError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    existing = await db.videos.find_one({"user_id": user.id, "youtube_id": video_id})
    if existing:
        return Video(**_serialize(existing))

    # Prefer the transcript (cheaper/faster). If YouTube blocks it or there are
    # no captions, fall back to letting Gemini watch the video URL directly.
    # Transcript fetch and metadata only depend on the video id, so run them
    # concurrently to keep both off the critical path.
    transcript: str | None = None
    lang: str | None = None

    fetch_start = time.perf_counter()
    transcript_result, meta = await asyncio.gather(
        run_in_threadpool(fetch_transcript, video_id),
        fetch_metadata(video_id),
        return_exceptions=True,
    )
    fetch_ms = (time.perf_counter() - fetch_start) * 1000

    # metadata is best-effort and never raises, but guard defensively so a
    # transcript failure in the gather doesn't mask a usable metadata result.
    if isinstance(meta, BaseException):
        raise meta

    if isinstance(transcript_result, TranscriptError):
        transcript = None
    elif isinstance(transcript_result, BaseException):
        raise transcript_result
    else:
        transcript, lang = transcript_result

    logger.info(
        "video=%s fetch phase: %.0fms (transcript=%s)",
        video_id,
        fetch_ms,
        "hit" if transcript else "miss",
    )

    gen_start = time.perf_counter()
    try:
        if transcript:
            material = await run_in_threadpool(
                generate_study_material, transcript, meta["title"]
            )
        else:
            material = await run_in_threadpool(
                generate_study_material_from_url, meta["url"], meta["title"]
            )
    except GeminiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    gen_ms = (time.perf_counter() - gen_start) * 1000

    logger.info(
        "video=%s gemini phase: %.0fms (path=%s)",
        video_id,
        gen_ms,
        "transcript" if transcript else "url_fallback",
    )

    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user.id,
        "youtube_id": video_id,
        "url": meta["url"],
        "title": meta["title"],
        "channel": meta.get("channel"),
        "thumbnail": meta.get("thumbnail"),
        "summary": material["summary"],
        "key_points": material["key_points"],
        "questions": [q.model_dump() for q in material["questions"]],
        "notes": "",
        "transcript_lang": lang,
        # Stored so the chat assistant can ground answers/customizations in the
        # full source text. Not exposed via the Video response model.
        "transcript": transcript,
        "chat": [],
        "created_at": now,
        "updated_at": now,
    }
    result = await db.videos.insert_one(doc)
    doc["_id"] = result.inserted_id
    return Video(**_serialize(doc))


@router.get("/{video_id}", response_model=Video)
async def get_video(video_id: str, user: User = Depends(get_current_user)):
    db = get_db()
    doc = await db.videos.find_one({"_id": _parse_object_id(video_id), "user_id": user.id})
    if not doc:
        raise HTTPException(status_code=404, detail="Video not found")
    return Video(**_serialize(doc))


@router.patch("/{video_id}", response_model=Video)
async def update_notes(
    video_id: str, payload: NotesUpdate, user: User = Depends(get_current_user)
):
    db = get_db()
    doc = await db.videos.find_one_and_update(
        {"_id": _parse_object_id(video_id), "user_id": user.id},
        {"$set": {"notes": payload.notes, "updated_at": datetime.now(timezone.utc)}},
        return_document=True,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Video not found")
    return Video(**_serialize(doc))


@router.post("/{video_id}/chat", response_model=ChatResponse)
async def chat_video(
    video_id: str, payload: ChatRequest, user: User = Depends(get_current_user)
):
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    db = get_db()
    oid = _parse_object_id(video_id)
    doc = await db.videos.find_one({"_id": oid, "user_id": user.id})
    if not doc:
        raise HTTPException(status_code=404, detail="Video not found")

    existing_questions = [Question(**q) for q in doc.get("questions", [])]

    try:
        result = await run_in_threadpool(
            chat_about_video,
            title=doc.get("title", ""),
            summary=doc.get("summary", ""),
            key_points=doc.get("key_points", []),
            questions=existing_questions,
            notes=doc.get("notes", ""),
            transcript=doc.get("transcript"),
            history=doc.get("chat", []),
            message=message,
        )
    except GeminiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    now = datetime.now(timezone.utc)
    new_messages = [
        {"role": "user", "content": message, "created_at": now},
        {"role": "assistant", "content": result["reply"], "created_at": now},
    ]

    set_fields: dict = {"updated_at": now}
    applied = False
    if result.get("apply_changes"):
        if "summary" in result:
            set_fields["summary"] = result["summary"]
            applied = True
        if "key_points" in result:
            set_fields["key_points"] = result["key_points"]
            applied = True
        if "questions" in result:
            set_fields["questions"] = [q.model_dump() for q in result["questions"]]
            applied = True

    updated = await db.videos.find_one_and_update(
        {"_id": oid, "user_id": user.id},
        {"$push": {"chat": {"$each": new_messages}}, "$set": set_fields},
        return_document=True,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Video not found")

    return ChatResponse(
        reply=result["reply"], updated=applied, video=Video(**_serialize(updated))
    )


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(video_id: str, user: User = Depends(get_current_user)):
    db = get_db()
    result = await db.videos.delete_one(
        {"_id": _parse_object_id(video_id), "user_id": user.id}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Video not found")
