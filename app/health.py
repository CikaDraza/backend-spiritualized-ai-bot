import asyncio
import logging
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from . import database

logger = logging.getLogger("spiritualized.health")
router = APIRouter()


async def _database_ready(head: str) -> bool:
    async with database.engine.connect() as connection:
        result = await connection.execute(text("SELECT 1"))
        if result.scalar_one() != 1:
            raise ValueError("SELECT 1 did not return 1")
        versions = await connection.execute(text("SELECT version_num FROM alembic_version"))
        return list(versions.scalars()) == [head]


@router.get("/health/ready")
async def ready() -> JSONResponse:
    try:
        config = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
        head = ScriptDirectory.from_config(config).get_current_head()
        if head is None:
            logger.warning("Readiness unavailable: migration scripts have no head")
        elif await asyncio.wait_for(_database_ready(head), timeout=3):
            return JSONResponse({"status": "ok"})
        else:
            logger.warning("Readiness unavailable: database migration revision is not at head")
    except asyncio.TimeoutError:
        logger.warning("Readiness unavailable: database check exceeded 3 seconds")
    except Exception as exc:
        # Exception messages can contain connection details; log only the failure type.
        logger.warning("Readiness unavailable: database or migration check failed (%s)", type(exc).__name__)

    return JSONResponse({"status": "unavailable"}, status_code=503)
