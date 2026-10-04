"""AI Media HQ - FastAPI application entrypoint."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import (
    agents,
    analytics,
    approvals,
    auth,
    channels,
    costs,
    dashboard,
    events,
    experiments,
    founder,
    ideas,
    knowledge,
    memory,
    production,
    publishing,
    qc,
    reports,
    research,
    scripts,
    suggestions,
    tasks,
    trends,
)
from app.api.routers import (
    settings as settings_router,
)  # noqa: F401
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.init_db import init_db

logger = logging.getLogger("aihq")
setup_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from app.agents.registry import AGENTS
    from app.db.session import SessionLocal
    from app.models.agent import Agent as AgentModel
    # Backfill: give existing orgs the full Agency-style dossiers the same
    # way new orgs get them at seed time. Idempotent: only fills empty ones.
    try:
        with SessionLocal() as db:
            personas = {a["key"]: a.get("persona", "") for a in AGENTS}
            legacy = db.query(AgentModel).filter(AgentModel.persona == "").all()
            for agent in legacy:
                agent.persona = personas.get(agent.key, "")
            if legacy:
                db.commit()
                logger.info("agent personas backfilled", extra={"count": len(legacy)})
    except Exception:  # noqa: BLE001
        logger.exception("persona backfill failed", extra={"error": "persona_backfill"})
    runner = None
    if settings.TASK_RUNNER_ENABLED:
        from app.services.task_runner import runner_loop
        runner = asyncio.create_task(runner_loop(settings.TASK_POLL_INTERVAL_SECONDS))
    logger.info("startup", extra={"status": "started"})
    yield
    if runner:
        runner.cancel()
    logger.info("shutdown", extra={"status": "stopped"})


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="AI-powered media company operating system. "
                "Integrations without credentials are never simulated.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_routers = (auth, channels, agents, tasks, events, memory, research, trends,
            dashboard, settings_router, approvals, knowledge, ideas, scripts, qc,
            production, publishing, analytics, experiments, costs, reports,
            founder, suggestions)
for module in _routers:
    app.include_router(module.router)


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT, "ai_provider": settings.AI_PROVIDER}


# Single-service UI: when the Docker image ships the compiled frontend in
# /app/static, serve it from the same origin as the API. API routes are
# registered above, so this catch-all only serves what is left.
from pathlib import Path as _P  # noqa: E402

from fastapi.responses import FileResponse as _FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

_STATIC_DIR = _P(__file__).resolve().parent.parent / "static"
if _STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=_STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):  # noqa: ANN201
        if full_path.startswith("api/") or full_path == "api":
            from fastapi import HTTPException as _HTTPException
            raise _HTTPException(status_code=404, detail="Not Found")
        index = _STATIC_DIR / "index.html"
        if full_path and (_STATIC_DIR / full_path).is_file():
            return _FileResponse(_STATIC_DIR / full_path)
        return _FileResponse(index)
