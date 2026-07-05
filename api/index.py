import os
import sys
from contextlib import asynccontextmanager

# On Vercel the function runs from the repo root (/var/task), so the api/
# directory is not on sys.path and the bare imports below fail. Add this
# file's directory so imports resolve both on Vercel and when running
# `uvicorn index:app` locally from the api/ directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import Depends, FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from auth import get_current_user  # noqa: E402
from config import get_settings  # noqa: E402
from db import ensure_indexes  # noqa: E402
from models import User  # noqa: E402
from routers import videos  # noqa: E402


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
