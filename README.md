# AI Media HQ

An AI-powered media company operating system: manage multiple YouTube Shorts
channels from one headquarters with a permissioned organization of 33 AI agents,
a real task/event/memory architecture, and honest integrations.

**Not a mockup.** Real FastAPI backend, real database, real orchestrator, real
permission enforcement, tested (26 passing tests) and Dockerized. Integrations
without credentials are explicitly inert - never simulated.

## Features

- **Command Center** - live dashboard built from real data (channels, agents,
  tasks, approvals, costs, events, computed recommendations)
- **Channels** - configuration-driven; the 5 initial channels (AI & Technology,
  Soccer, Business & Money, Transformative Clips, Interesting Facts) are seed
  data, and new channels are created from the UI. No niche logic in code.
- **Agents** - 33-agent organization (executive, intelligence, creative,
  production, quality, publishing, growth, operations) with 5 permission levels,
  pause/resume, run history
- **Tasks** - high-level commands with dependencies, priorities, retries,
  cancellation; executed by the orchestrator with kill-switch, budget and
  permission checks
- **Trend Radar** - scores computed only from stored research documents with
  documented signals (volume, growth ratio, social signal) - shows WHY a trend
  was detected
- **Memory** - six scopes (short-term, long-term, channel, agent, content,
  strategic), keyword search, capped per-task retrieval
- **Kill switches** - pause all operations, pause publishing, human-approval
  default for publishing; audit-logged
- **Honesty guarantees** - unconfigured AI provider -> clear failure; no
  research key -> HTTP 503; no trend data -> empty scan; YouTube upload ->
  never faked

## Prerequisites

- Python 3.11+, Node 20+ (local dev) or Docker + Docker Compose

## Quick start (Docker)

```bash
cp .env.example .env        # fill in SECRET_KEY and any API keys you have
docker compose up --build
```

- Frontend: http://localhost:3000
- API: http://localhost:8000 (OpenAPI docs at /docs)

Postgres runs in Docker; Alembic migrations apply automatically on backend start.

## Quick start (local dev)

```bash
# Backend
cd backend
pip install -r requirements.txt
cp ../.env.example .env            # edit: AI_PROVIDER, keys, SECRET_KEY
alembic upgrade head              # or let init_db create tables
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                       # http://localhost:5173 (proxies /api)
```

## Environment variables

See `.env.example` (all documented). Highlights:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLite locally, Postgres in Docker |
| `SECRET_KEY` | JWT signing - generate a strong value |
| `AI_PROVIDER` / `AI_MODEL` | `openai` or `anthropic` + model name |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | AI credentials |
| `TAVILY_API_KEY` | web research |
| `YOUTUBE_DATA_API_KEY` | YouTube search |
| `YOUTUBE_CLIENT_ID/SECRET/REDIRECT_URI` | publishing OAuth (Phase 6) |
| `MONTHLY_BUDGET_USD` | spending guard rail enforced by the orchestrator |

## Authentication

`POST /api/auth/register` creates an organization (with seeded channels +
agent org) and an owner user. `POST /api/auth/login` returns a JWT. Frontend
stores the token locally and sends `Authorization: Bearer`.

## Testing

```bash
cd backend && python -m pytest tests -q     # 26 tests
cd backend && ruff check app tests          # lint
cd frontend && npm run build                # type-check + build
```

Tests cover: auth, channel config-driven behavior, agent registry shape,
permission enforcement (blocked runs), paused agents, kill switch, task
dependencies, cancel/retry, event emission, memory search, trend scan from
real documents, unconfigured-integration honesty, dashboard data, settings.

## Repository layout

```
backend/    FastAPI app (models, routers, services, agents, integrations, tests, alembic)
frontend/   React + TypeScript dashboard (Vite)
docs/       ARCHITECTURE.md, INTEGRATIONS.md, AGENTS.md, ROADMAP.md
scripts/    dev helper
.github/    CI workflow (backend tests+lint, frontend build)
docker-compose.yml, .env.example
```

## Integrations & YouTube setup

See `docs/INTEGRATIONS.md` for Tavily, YouTube Data API, and the YouTube OAuth
publishing flow (Phase 6; uploads are never simulated).

## Status & roadmap

Phase 1 (foundation) and Phase 2 (agent infrastructure) are implemented and
working, plus research/trend foundations. The full honest phase inventory is in
`docs/ROADMAP.md`. Models and architecture for Phases 3-8 already exist
(ideas, scripts, claims, QC, rights, approvals, publishing, analytics,
experiments, costs, reports are all modeled with migrations).

## Troubleshooting

- **Agents fail with "No AI provider configured"** - set `AI_PROVIDER` + key in
  `backend/.env` (intentional honest failure, not a bug).
- **Research returns 503** - add the matching API key.
- **Tasks stay queued** - the background runner is on (`TASK_RUNNER_ENABLED`);
  you can also press Run in the UI. Check kill switch in Settings.
- **Port conflicts** - change ports in docker-compose.yml / vite config.
