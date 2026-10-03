"""YouTube publishing integration (Section 25) - real OAuth + resumable upload.

Requires YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET (Google Cloud project with
the YouTube Data API v3 enabled) and a completed OAuth consent flow.
NEVER fakes a successful upload - see docs/INTEGRATIONS.md.
"""
import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger("aihq.youtube")

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
DEFAULT_SCOPES = (
    "https://www.googleapis.com/auth/youtube.upload "
    "https://www.googleapis.com/auth/youtube.readonly"
)


class YouTubeNotConfiguredError(RuntimeError):
    """Raised when YouTube OAuth credentials are missing."""


class YouTubePublishError(RuntimeError):
    """Raised when Google's API rejects the upload or the flow fails."""


def require_config() -> None:
    s = get_settings()
    if not (s.YOUTUBE_CLIENT_ID and s.YOUTUBE_CLIENT_SECRET):
        raise YouTubeNotConfiguredError(
            "YouTube publishing is not configured. Set YOUTUBE_CLIENT_ID and "
            "YOUTUBE_CLIENT_SECRET in backend/.env (see docs/INTEGRATIONS.md)."
        )


def consent_url(redirect_uri: str, state: str = "") -> str:
    """Build the Google OAuth consent URL (real, no credentials -> explicit error)."""
    require_config()
    s = get_settings()
    params = (
        f"client_id={s.YOUTUBE_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        f"&scope={DEFAULT_SCOPES.replace(' ', '%20')}"
        "&access_type=offline"
        "&prompt=consent"
    )
    if state:
        params += f"&state={state}"
    return f"{AUTH_URL}?{params}"


def exchange_code(code: str, redirect_uri: str) -> dict:
    """Exchange an OAuth authorization code for tokens (real Google endpoint)."""
    require_config()
    s = get_settings()
    resp = httpx.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": s.YOUTUBE_CLIENT_ID,
            "client_secret": s.YOUTUBE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise YouTubePublishError(f"Token exchange failed: {resp.status_code} {resp.text[:300]}")
    data = resp.json()
    return {
        "access_token": data.get("access_token", ""),
        "refresh_token": data.get("refresh_token", ""),
        "expires_in": data.get("expires_in", 3600),
        "scope": data.get("scope", ""),
    }


def upload_video(access_token: str, title: str, description: str,
                 tags: list[str], media_bytes: bytes, privacy: str = "public") -> str:
    """Resumable upload to the YouTube Data API. Returns the real video id.

    Raises on any failure - the caller records the error; nothing is faked.
    """
    metadata = {
        "snippet": {"title": title, "description": description, "tags": tags,
                    "categoryId": "28"},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    with httpx.Client(timeout=600) as client:
        init = client.post(
            f"{UPLOAD_URL}?uploadType=resumable&part=snippet,status",
            headers={"Authorization": f"Bearer {access_token}",
                     "Content-Type": "application/json"},
            json=metadata,
        )
        if init.status_code not in (200, 201):
            raise YouTubePublishError(f"Upload init failed: {init.status_code} {init.text[:300]}")
        upload_url = init.headers.get("Location")
        if not upload_url:
            raise YouTubePublishError("Google did not return an upload session URL")

        put = client.put(
            upload_url,
            headers={"Content-Type": "video/*", "Content-Length": str(len(media_bytes))},
            content=media_bytes,
        )
        if put.status_code not in (200, 201):
            raise YouTubePublishError(f"Upload failed: {put.status_code} {put.text[:300]}")
        video_id = put.json().get("id", "")
        if not video_id:
            raise YouTubePublishError("Upload response contained no video id")
        return video_id
