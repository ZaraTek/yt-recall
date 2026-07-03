from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

QuestionType = Literal["flashcard", "mcq", "open"]


class Question(BaseModel):
    id: str
    type: QuestionType
    prompt: str
    answer: str
    options: list[str] | None = None
    explanation: str | None = None


class User(BaseModel):
    id: str
    email: str
    name: str
    picture: str | None = None


class VideoCreate(BaseModel):
    url: str


class NotesUpdate(BaseModel):
    notes: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class ChatRequest(BaseModel):
    message: str


class VideoSummary(BaseModel):
    """Lightweight shape used for library listings."""

    id: str
    youtube_id: str
    url: str
    title: str
    channel: str | None = None
    thumbnail: str | None = None
    created_at: datetime


class Video(VideoSummary):
    summary: str = ""
    key_points: list[str] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)
    notes: str = ""
    transcript_lang: str | None = None
    chat: list[ChatMessage] = Field(default_factory=list)
    updated_at: datetime | None = None


class ChatResponse(BaseModel):
    reply: str
    updated: bool
    video: Video
