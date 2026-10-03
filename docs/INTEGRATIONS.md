# Integrations

Every integration is real and credential-gated. Nothing is simulated.

## AI provider (required for agents to run)

Set in `backend/.env`:

```
AI_PROVIDER=openai          # or anthropic
AI_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
```

Without a key, the provider raises `ProviderNotConfiguredError`; tasks fail
with a clear setup message and are never marked successful.

## Web research (Tavily)

1. Create an account at tavily.com and copy the API key.
2. Set `TAVILY_API_KEY=tvly-...` in `backend/.env`.
3. `POST /api/research/search {"query": "...", "provider": "tavily"}` stores
   real results as ResearchDocuments (source type, relevance, credibility meta).

## YouTube search/analytics (YouTube Data API v3)

1. Google Cloud Console -> enable "YouTube Data API v3" -> create API key.
2. Set `YOUTUBE_DATA_API_KEY=...`.
3. `POST /api/research/search {"query": "...", "provider": "youtube"}`.

## YouTube publishing (Phase 6 - architecture ready)

Requires OAuth (user's own channel):

1. Google Cloud Console -> OAuth consent screen -> enable YouTube Data API.
2. Create OAuth client (Web) -> set redirect URI to
   `YOUTUBE_REDIRECT_URI` (default `http://localhost:8000/api/publishing/youtube/callback`).
3. Set `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` in `backend/.env`.
4. Complete the consent flow; store the refresh token securely.
5. Publishing Agent uploads only after an Approval is granted (auto_publish
   stays off by default - human approval is required).

`YouTubePublisher.upload()` intentionally raises until the full OAuth callback
flow ships in Phase 6. Uploads are NEVER faked.

## Source hierarchy (Section 14)

Research documents carry `source_type`; trend scoring dampens social signals,
and factual claims must cite primary/official/research sources. Social posts
are trend-discovery signals, not evidence.
