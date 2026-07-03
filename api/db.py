import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from config import get_settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.mongodb_uri:
            raise RuntimeError("MONGODB_URI is not configured")
        # Use certifi's CA bundle so TLS to Atlas works even when the system
        # Python has no root certificates installed (common on macOS).
        _client = AsyncIOMotorClient(
            settings.mongodb_uri, tlsCAFile=certifi.where()
        )
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[get_settings().mongodb_db]


async def ensure_indexes() -> None:
    db = get_db()
    await db.users.create_index("google_sub", unique=True)
    await db.videos.create_index([("user_id", 1), ("youtube_id", 1)], unique=True)
    await db.videos.create_index([("user_id", 1), ("created_at", -1)])
