"""Production engine provider abstraction (Section 22).

The system does NOT depend on one video-generation provider. The registry
maps a provider name to an implementation; adding a provider never requires
touching the pipeline code.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.core.config import get_settings


class ProviderNotConfiguredError(RuntimeError):
    """Raised when an external production provider has no credentials."""


@dataclass
class RenderResult:
    asset_url: str = ""
    asset_type: str = "video"
    cost_usd: float = 0.0
    output: dict = field(default_factory=dict)


class VideoProvider(ABC):
    """Interface every production provider implements."""

    name: str = "abstract"

    @abstractmethod
    def render(self, config: dict, script_version: dict | None = None) -> RenderResult:
        """Produce (or register) the video asset. Never fake success."""


class UserMediaProvider(VideoProvider):
    """Registers media the user produced themselves (uploaded file / rendered clip).

    This is a real production path: the user supplies a media URL, the system
    records it as the produced asset. No generation is claimed.
    """

    name = "user_media"

    def render(self, config: dict, script_version: dict | None = None) -> RenderResult:
        media_url = (config or {}).get("media_url", "").strip()
        if not media_url:
            raise ValueError("user_media provider requires config.media_url")
        return RenderResult(
            asset_url=media_url,
            asset_type=(config or {}).get("media_type", "video"),
            cost_usd=0.0,
            output={"provider": self.name, "note": "user-supplied media registered"},
        )


class ExternalVideoProvider(VideoProvider):
    """Generic adapter for an external AI video generation service.

    Contract (documented in docs/INTEGRATIONS.md):
      POST {VIDEO_PROVIDER_URL}/render  with Bearer {VIDEO_PROVIDER_API_KEY}
      body: {"script": ..., "config": ...}  ->  {"video_url": ...}

    Without credentials it raises ProviderNotConfiguredError - never faked.
    """

    name = "external"

    def render(self, config: dict, script_version: dict | None = None) -> RenderResult:
        import httpx

        s = get_settings()
        if not (s.VIDEO_PROVIDER_URL and s.VIDEO_PROVIDER_API_KEY):
            raise ProviderNotConfiguredError(
                "External video provider is not configured. Set VIDEO_PROVIDER_URL and "
                "VIDEO_PROVIDER_API_KEY in backend/.env, or use the 'user_media' provider."
            )
        resp = httpx.post(
            f"{s.VIDEO_PROVIDER_URL.rstrip('/')}/render",
            headers={"Authorization": f"Bearer {s.VIDEO_PROVIDER_API_KEY}"},
            json={"script": script_version or {}, "config": config or {}},
            timeout=600,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Video provider returned {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        video_url = data.get("video_url", "")
        if not video_url:
            raise RuntimeError("Video provider response contained no video_url")
        return RenderResult(
            asset_url=video_url,
            cost_usd=float(data.get("cost_usd", 0.0)),
            output={"provider": self.name, "raw": data},
        )


_REGISTRY: dict[str, type[VideoProvider]] = {
    UserMediaProvider.name: UserMediaProvider,
    ExternalVideoProvider.name: ExternalVideoProvider,
}


def get_video_provider(name: str) -> VideoProvider:
    if name not in _REGISTRY:
        raise ValueError(f"Unknown video provider '{name}'. Available: {sorted(_REGISTRY)}")
    return _REGISTRY[name]()
