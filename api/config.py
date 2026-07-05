from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    google_client_id: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    # Cap generation length to reduce study-material latency. The structured
    # output (summary + 4-8 key points + 6-10 questions) fits comfortably here.
    gemini_max_output_tokens: int = 4096
    mongodb_uri: str = ""
    mongodb_db: str = "yt_recall"
    cors_origins: str = "http://localhost:5173"
    # Comma-separated allowlist of emails permitted to sign in. When empty,
    # any Google account is allowed; when set, only these emails may use the
    # app (keeps Gemini costs limited to you and your friends).
    allowed_emails: str = ""
    # When true, skip Google token verification and use a fixed dev user.
    auth_disabled: bool = False
    # Optional proxy config to work around YouTube IP bans on transcript fetches.
    # Webshare rotating residential proxies (recommended):
    webshare_proxy_username: str = ""
    webshare_proxy_password: str = ""
    # Or a generic HTTP/HTTPS/SOCKS proxy:
    proxy_http_url: str = ""
    proxy_https_url: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.allowed_emails.split(",") if e.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
