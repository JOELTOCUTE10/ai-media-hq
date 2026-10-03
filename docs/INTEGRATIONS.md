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


## Video generation providers

`VIDEO_PROVIDER_URL` + `VIDEO_PROVIDER_API_KEY` activate the `external`
production provider. Contract: `POST {URL}/render` with Bearer auth and a JSON
body `{"script": {...}, "config": {...}}` must return `{"video_url": "..."}`.
The `user_media` provider needs no credentials: it registers a media URL you
supply as the produced asset. Unconfigured providers fail with explicit setup
guidance - success is never faked.

## YouTube publishing (full flow)

1. Create a Google Cloud project, enable YouTube Data API v3, create an OAuth
   client (type "Web application") with redirect URI
   `http://localhost:8000/api/publishing/youtube/callback`.
2. Set `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REDIRECT_URI`
   in `backend/.env`.
3. In the dashboard (Publishing page) click "Get consent URL", complete the
   Google consent screen. The callback exchanges the code for tokens which
   are stored server-side (never exposed through the API).
4. Publishing requires the readiness gate: QC PASS, no disputed/unsupported
   claims, no unknown/blocked rights, and (with auto-publish off) a human
   approval. Scheduled jobs are attempted automatically when due.


## Free research providers (no API key)

Four research sources work with zero credentials and are always available:

- `wikipedia` - MediaWiki full-text search (secondary reference; respects the
  source hierarchy for claim verification)
- `hackernews` - Hacker News story search via the Algolia API (trend-discovery
  signal; classified as social, never treated as factual evidence)
- `arxiv` - research preprints (original_research source tier)
- `openalex` - scholarly works catalog with reconstructed abstracts
  (original_research source tier)

All research providers share the `ResearchProvider` contract, so adding another
source is one adapter class in `app/integrations/research_providers.py` plus a
registry entry - the API and UI pick it up automatically.


## Free LLM providers (permanent free tiers)

All four are OpenAI-compatible, so they share one adapter. Set `AI_PROVIDER`
plus the matching key in `.env` - leave `AI_MODEL` empty for the default model.

| AI_PROVIDER   | Free key from                              | Default model            | Free limits (approx.)        |
|---------------|--------------------------------------------|--------------------------|------------------------------|
| `groq`        | console.groq.com/keys                      | openai/gpt-oss-20b       | 30 RPM, 1,000 requests/day  |
| `mistral`     | console.mistral.ai/api-keys               | mistral-small-latest     | ~1 request/sec               |
| `openrouter`  | openrouter.ai/keys (`:free` models)       | openai/gpt-oss-20b:free   | 20 RPM, 50 requests/day/model|
| `gemini`      | aistudio.google.com/app/apikey             | gemini-2.5-flash         | 15-30 RPM, 1,500 requests/day|

Any other OpenAI-compatible endpoint (self-hosted vLLM, Ollama, LM Studio):
`AI_PROVIDER=openai_compatible` + `OPENAI_BASE_URL` + `OPENAI_API_KEY`.

Honest caveats:
- Free-tier prompts may be used by the provider to improve their models
  (Gemini and Mistral note this in their terms). Do not route secrets through
  free tiers; paid OpenAI/Anthropic keys remain the private option.
- Rate limits fit a daily agent routine fine, but a Founder Mode burst of
  concurrent tasks can hit them; the orchestrator's retry + honest failure
  handling will surface it rather than fake success.
- Cohere is intentionally NOT included: its free tier is non-commercial only.
