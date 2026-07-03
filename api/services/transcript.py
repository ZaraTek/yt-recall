import re
from urllib.parse import parse_qs, urlparse

import httpx
from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeTranscriptApi,
)
from youtube_transcript_api.proxies import GenericProxyConfig, WebshareProxyConfig

from config import get_settings

try:
    from youtube_transcript_api import IpBlocked, RequestBlocked

    _BLOCK_ERRORS: tuple[type[Exception], ...] = (RequestBlocked, IpBlocked)
except ImportError:  # older versions don't expose these
    _BLOCK_ERRORS = ()


class TranscriptError(Exception):
    """Raised when a transcript cannot be retrieved for a video."""


class TranscriptBlockedError(TranscriptError):
    """Raised specifically when YouTube blocks transcript requests from this IP."""


_YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_video_id(url: str) -> str:
    """Extract an 11-char YouTube video id from a variety of URL formats."""
    url = url.strip()
    if _YOUTUBE_ID_RE.match(url):
        return url

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    if host in {"youtu.be"}:
        candidate = parsed.path.lstrip("/").split("/")[0]
        if _YOUTUBE_ID_RE.match(candidate):
            return candidate

    if "youtube.com" in host:
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [""])[0]
            if _YOUTUBE_ID_RE.match(candidate):
                return candidate
        # /embed/<id>, /shorts/<id>, /live/<id>
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2 and parts[0] in {"embed", "shorts", "live", "v"}:
            if _YOUTUBE_ID_RE.match(parts[1]):
                return parts[1]

    raise TranscriptError("Could not parse a YouTube video id from the provided URL.")


def _build_api() -> YouTubeTranscriptApi:
    """Construct the transcript API, wiring in a proxy if one is configured."""
    settings = get_settings()
    if settings.webshare_proxy_username and settings.webshare_proxy_password:
        return YouTubeTranscriptApi(
            proxy_config=WebshareProxyConfig(
                proxy_username=settings.webshare_proxy_username,
                proxy_password=settings.webshare_proxy_password,
            )
        )
    if settings.proxy_http_url or settings.proxy_https_url:
        return YouTubeTranscriptApi(
            proxy_config=GenericProxyConfig(
                http_url=settings.proxy_http_url or None,
                https_url=settings.proxy_https_url or None,
            )
        )
    return YouTubeTranscriptApi()


def fetch_transcript(video_id: str) -> tuple[str, str | None]:
    """Return (transcript_text, language_code). Raises TranscriptError on failure."""
    try:
        api = _build_api()
        transcript_list = api.list(video_id)
        try:
            transcript = transcript_list.find_transcript(["en"])
        except NoTranscriptFound:
            transcript = next(iter(transcript_list))
        fetched = transcript.fetch()
        text = " ".join(
            snippet.text.strip() for snippet in fetched if snippet.text.strip()
        )
        if not text:
            raise TranscriptError("Transcript is empty for this video.")
        return text, transcript.language_code
    except _BLOCK_ERRORS as exc:
        raise TranscriptBlockedError(
            "YouTube is blocking transcript requests from this IP."
        ) from exc
    except (TranscriptsDisabled, NoTranscriptFound):
        raise TranscriptError("This video has no available captions/transcript.")
    except VideoUnavailable:
        raise TranscriptError("This video is unavailable.")
    except TranscriptError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface a friendly message
        raise TranscriptError(f"Failed to fetch transcript: {exc}") from exc


async def fetch_metadata(video_id: str) -> dict:
    """Fetch title/channel/thumbnail via the public oEmbed endpoint."""
    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    meta = {
        "title": watch_url,
        "channel": None,
        "thumbnail": thumbnail,
        "url": watch_url,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://www.youtube.com/oembed",
                params={"url": watch_url, "format": "json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                meta["title"] = data.get("title", watch_url)
                meta["channel"] = data.get("author_name")
                meta["thumbnail"] = data.get("thumbnail_url", thumbnail)
    except Exception:  # noqa: BLE001 - metadata is best-effort
        pass
    return meta
