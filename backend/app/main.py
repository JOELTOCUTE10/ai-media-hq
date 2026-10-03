"""AI Media HQ - FastAPI application entrypoint."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import (
    agents,
    approvals,
    auth,
    channels,
    dashboard,
    events,
    memory,
    research,
    tasks,
    trends,
)
from app.api.routers import (
    settings as settings_router,
)
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.init_db import init_db

logger = logging.getLogger("aihq")
setup_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
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

for module in (auth, channels, agents, tasks, events, memory, research, trends, dashboard, settings_router, approvals):
    app.include_router(module.router)


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT, "ai_provider": settings.AI_PROVIDER}
