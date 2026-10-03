# Architecture

## Stack

- Backend: Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, JWT auth
- Frontend: React 18 + TypeScript + Vite, custom futuristic dark theme
- Infra: Docker Compose (Postgres 16, backend, nginx-served frontend)
- Tests: pytest (26 tests), ruff lint; CI runs both

## Layers

    frontend (React)  ->  REST API  ->  routers  ->  services  ->  models
                                                        |
              orchestrator -> AIProvider / research providers (integrations)
              event bus, memory, trend service

- `app/models` - 45 tables (organization, channel, agent, task, research,
  content, production, analytics, knowledge, ops domains)
- `app/api/routers` - thin HTTP layer; org-scoped queries everywhere
- `app/services` - orchestrator (permission checks, kill switch, budget,
  retries, runs/costs), task_runner (swappable for Celery), event_bus,
  memory_service (capped retrieval), trend_service (documented scoring)
- `app/agents` - permissions (levels -> permission sets) + registry (data)
- `app/integrations` - AIProvider (OpenAI/Anthropic/fake/unconfigured),
  research providers (Tavily, YouTube Data), YouTube publisher skeleton

## Key design decisions

1. Channels are config records. Adding a channel or agent never touches code.
2. Agents are data seeded from `app/agents/registry.py`.
3. Honesty rule: unconfigured providers raise; tasks fail with setup guidance;
   research returns 503; trends require real documents; uploads never simulated.
4. Multi-tenant-ready: every content row carries org_id; auth creates orgs.
5. Task execution is idempotent per run: status transitions are explicit and
   only the orchestrator marks success after a real provider completion.
6. Events persist in `system_events`; subscribers are in-process, so a future
   Redis/Celery bus can replace transport without touching publishers.

## Data flow for a task

user -> POST /api/tasks (validation, agent resolve, deps) -> queued
runner (or manual /run) -> orchestrator:
  org kill switch -> agent exists/active -> permission check -> budget check
  -> deps check -> memory context -> provider.complete() -> AgentRun
  -> CostRecord -> events (TASK_*, AGENT_*) -> task completed/failed/blocked
