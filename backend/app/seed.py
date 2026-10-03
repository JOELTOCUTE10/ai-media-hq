"""Seed data (Section 45): the five initial channels + the 33-agent organization.

Everything is configuration-driven and clearly labeled as sample/seed data.
No fake analytics, no fake published videos are ever created.
"""
from sqlalchemy.orm import Session

from app.agents.permissions import LEVEL_PERMISSIONS
from app.agents.registry import AGENTS
from app.core.config import get_settings
from app.models.agent import Agent, AgentPermission
from app.models.channel import Channel
from app.models.enums import IntegrationStatus
from app.models.ops import Integration

DEFAULT_CHANNELS = [
    {
        "slug": "ai-technology",
        "name": "AI & Technology",
        "description": "Shorts explaining AI breakthroughs, tools and tech news.",
        "niche": "AI / technology news and explainers",
        "audience": "Tech-curious viewers 18-40 who want sharp explainers, not hype",
        "brand_settings": {"tone": "sharp, factual, energetic", "colors": ["#22d3ee", "#0ea5e9"], "avoid": ["hype", "clickbait"]},
        "content_rules": {"max_claims_per_video": 5, "every_claim_needs_source": True, "banned_phrases": ["you won't believe"]},
        "publishing_rules": {"cadence_per_week": 5, "best_hours_utc": [15, 18, 21], "requires_approval": True},
        "research_sources": ["tavily", "youtube"],
        "style": {"format": "voiceover + b-roll", "captions": "always", "length_seconds": [35, 60]},
    },
    {
        "slug": "soccer",
        "name": "Soccer",
        "description": "Soccer moments, tactics and storylines as fast Shorts.",
        "niche": "Soccer highlights, tactics and narratives",
        "audience": "Global soccer fans 16-35 following leagues and transfers",
        "brand_settings": {"tone": "passionate, quick, fan-first", "colors": ["#22c55e", "#059669"], "avoid": ["disrespecting clubs"]},
        "content_rules": {"only_licensed_or_permitted_footage": True, "no_unverified_transfer_claims": True},
        "publishing_rules": {"cadence_per_week": 5, "best_hours_utc": [12, 17, 20], "requires_approval": True},
        "research_sources": ["tavily", "youtube"],
        "style": {"format": "clip + narration", "captions": "always", "length_seconds": [25, 50]},
    },
    {
        "slug": "business-money",
        "name": "Business & Money",
        "description": "Money concepts, business stories and financial literacy Shorts.",
        "niche": "Business, finance and economics explainers",
        "audience": "Aspiring professionals and entrepreneurs 20-45",
        "brand_settings": {"tone": "clear, credible, no-hype", "colors": ["#f59e0b", "#d97706"], "avoid": ["financial advice"]},
        "content_rules": {"disclaimer_on_any_number": True, "no_specific_investment_advice": True},
        "publishing_rules": {"cadence_per_week": 4, "best_hours_utc": [13, 19], "requires_approval": True},
        "research_sources": ["tavily", "youtube"],
        "style": {"format": "voiceover + motion graphics", "captions": "always", "length_seconds": [40, 60]},
    },
    {
        "slug": "transformative-clips",
        "name": "Transformative Clips",
        "description": "Third-party clips transformed with original commentary and context.",
        "niche": "Transformative commentary content",
        "audience": "Viewers who want the story behind viral moments",
        "brand_settings": {"tone": "thoughtful, narrative", "colors": ["#a78bfa", "#7c3aed"], "avoid": ["reaction-only content"]},
        "content_rules": {"rights_status_required_before_publish": True, "must_add_substantial_original_value": True},
        "publishing_rules": {"cadence_per_week": 3, "best_hours_utc": [16, 21], "requires_approval": True},
        "research_sources": ["tavily", "youtube"],
        "style": {"format": "clip + analysis overlay", "captions": "always", "length_seconds": [30, 60]},
    },
    {
        "slug": "interesting-facts",
        "name": "Interesting Facts",
        "description": "Surprising, verified facts with visual proof and sources.",
        "niche": "Facts and curiosity content",
        "audience": "Curious viewers of all ages, strong share behavior",
        "brand_settings": {"tone": "curious, precise, fun", "colors": ["#f472b6", "#e11d48"], "avoid": ["facts without sources"]},
        "content_rules": {"every_fact_is_a_trackable_claim": True, "min_two_sources_for_surprising_claims": True},
        "publishing_rules": {"cadence_per_week": 5, "best_hours_utc": [14, 20], "requires_approval": True},
        "research_sources": ["tavily", "youtube"],
        "style": {"format": "voiceover + stock/b-roll", "captions": "always", "length_seconds": [25, 55]},
    },
]

INTEGRATION_DEFS = [
    ("ai_openai", "OpenAI (AI provider)"),
    ("ai_anthropic", "Anthropic (AI provider)"),
    ("ai_groq", "Groq (free tier)"),
    ("ai_mistral", "Mistral (free tier)"),
    ("ai_openrouter", "OpenRouter free models"),
    ("ai_gemini", "Google Gemini (free tier)"),
    ("research_tavily", "Tavily web search"),
    ("research_youtube", "YouTube Data API (search/analytics)"),
    ("youtube_publishing", "YouTube publishing (OAuth)"),
]


def seed_org(db: Session, org_id: int) -> None:
    """Create the default channels, agent org, integrations for a new org."""
    for c in DEFAULT_CHANNELS:
        db.add(Channel(org_id=org_id, **c))

    settings = get_settings()
    for a in AGENTS:
        agent = Agent(
            org_id=org_id, key=a["key"], name=a["name"], role=a["role"],
            description=a["description"], department=a["department"],
            capabilities=a["capabilities"], tools=a["tools"],
            permission_level=a["permission_level"],
            model_config_json={"model": settings.AI_MODEL, "temperature": 0.4},
            memory_access=["short_term", "long_term", "channel"],
        )
        db.add(agent)
        db.flush()
        for perm in sorted(LEVEL_PERMISSIONS[a["permission_level"]]):
            db.add(AgentPermission(agent_id=agent.id, permission=perm, granted=True))

    integration_keys = {
        "ai_openai": bool(settings.OPENAI_API_KEY),
        "ai_anthropic": bool(settings.ANTHROPIC_API_KEY),
        "ai_groq": bool(settings.GROQ_API_KEY),
        "ai_mistral": bool(settings.MISTRAL_API_KEY),
        "ai_openrouter": bool(settings.OPENROUTER_API_KEY),
        "ai_gemini": bool(settings.GEMINI_API_KEY),
        "research_tavily": bool(settings.TAVILY_API_KEY),
        "research_youtube": bool(settings.YOUTUBE_DATA_API_KEY),
        "youtube_publishing": bool(settings.YOUTUBE_CLIENT_ID and settings.YOUTUBE_CLIENT_SECRET),
    }
    for key, name in INTEGRATION_DEFS:
        status = IntegrationStatus.CONFIGURED.value if integration_keys[key] else IntegrationStatus.UNCONFIGURED.value
        db.add(Integration(org_id=org_id, key=key, name=name, status=status, config={"requires_credentials": True}))

    db.commit()
