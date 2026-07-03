from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from config import get_settings
from db import get_db
from models import User

_request_adapter = google_requests.Request()

DEV_USER_SUB = "dev-user"


async def _upsert_user(google_sub: str, email: str, name: str, picture: str | None) -> User:
    db = get_db()
    now = datetime.now(timezone.utc)
    result = await db.users.find_one_and_update(
        {"google_sub": google_sub},
        {
            "$set": {
                "google_sub": google_sub,
                "email": email,
                "name": name,
                "picture": picture,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
        return_document=True,
    )
    return User(
        id=str(result["_id"]),
        email=result["email"],
        name=result["name"],
        picture=result.get("picture"),
    )


async def get_current_user(authorization: str = Header(default="")) -> User:
    """Verify the Google ID token from the Authorization header and upsert the user."""
    settings = get_settings()

    # Dev bypass: skip Google verification and use a fixed local user.
    if settings.auth_disabled:
        return await _upsert_user(
            DEV_USER_SUB, "dev@localhost", "Dev User", None
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
        )

    token = authorization.split(" ", 1)[1].strip()

    try:
        claims = id_token.verify_oauth2_token(
            token, _request_adapter, settings.google_client_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google ID token",
        ) from exc

    google_sub = claims.get("sub")
    if not google_sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )

    return await _upsert_user(
        google_sub,
        claims.get("email", ""),
        claims.get("name", claims.get("email", "")),
        claims.get("picture"),
    )


CurrentUser = Depends(get_current_user)
