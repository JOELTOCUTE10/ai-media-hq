"""YouTube publishing adapter (Section 25) - Phase 6 skeleton.

Implements the OAuth/Publish architecture surface. Requires
YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET and a completed OAuth flow.
NEVER fakes a successful upload - see docs/INTEGRATIONS.md.
"""
from app.core.config import get_settings


class PublishingNotConfiguredError(RuntimeError):
    pass


class YouTubePublisher:
    """Uploads videos via the YouTube Data API v3 after a valid OAuth grant.

    Status: architecture only. upload() intentionally raises until the full
    OAuth callback flow (Phase 6) is implemented and credentials exist.
    """

    name = "youtube"

    def auth_url(self) -> str:
        settings = get_settings()
        if not settings.YOUTUBE_CLIENT_ID:
            raise PublishingNotConfiguredError(
                "YOUTUBE_CLIENT_ID is not set. See docs/INTEGRATIONS.md for the OAuth setup."
            )
        scopes = "https://www.googleapis.com/auth/youtube.upload"
        return (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={settings.YOUTUBE_CLIENT_ID}"
            f"&redirect_uri={settings.YOUTUBE_REDIRECT_URI}"
            f"&response_type=code&scope={scopes.replace(':', '%3A')}&access_type=offline"
            "&prompt=consent"
        )

    def upload(self, video_path: str, title: str, description: str, tags: list[str]) -> dict:
        raise PublishingNotConfiguredError(
            "YouTube publishing is not fully wired yet (Phase 6). "
            "Configure YOUTUBE_CLIENT_ID/SECRET and complete the OAuth flow; uploads are never simulated."
        )
