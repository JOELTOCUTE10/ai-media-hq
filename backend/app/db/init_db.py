"""Create tables (dev). In production use Alembic migrations instead."""
from app.db.base import Base
from app.db.session import engine


def init_db() -> None:
    import app.models  # noqa: F401  - register all models

    Base.metadata.create_all(bind=engine)
