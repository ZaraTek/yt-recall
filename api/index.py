from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth import get_current_user
from config import get_settings
from db import ensure_indexes
from models import User
from routers import videos


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await ensure_indexes()
    except Exception:  # noqa: BLE001 - don't crash startup if DB is unreachable
        pass
    yield


app = FastAPI(title="YouTube Recall API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(videos.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/me", response_model=User)
async def me(user: User = Depends(get_current_user)):
    return user
