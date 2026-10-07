import logging
from contextlib import asynccontextmanager

import aiosqlite

from config import DATABASE_PATH, DB_BUSY_TIMEOUT_MS

logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_db():
    """
    Открывает отдельное асинхронное соединение с SQLite
    на одну логическую операцию.
    """

    db = await aiosqlite.connect(
        str(DATABASE_PATH),
        timeout=DB_BUSY_TIMEOUT_MS / 1000,
    )

    db.row_factory = aiosqlite.Row

    # busy_timeout задается для каждого нового соединения.
    await db.execute(
        f"PRAGMA busy_timeout={DB_BUSY_TIMEOUT_MS};"
    )

    try:
        yield db
    finally:
        await db.close()


async def init_db() -> None:
    """
    Создает таблицу predictions при старте приложения.

    WAL улучшает совместную работу чтения и записи.
    """

    async with get_db() as db:
        await db.execute(
            "PRAGMA journal_mode=WAL;"
        )

        await db.execute(
            "PRAGMA synchronous=NORMAL;"
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL,
                farm_id TEXT NOT NULL,
                risk_score REAL NOT NULL,
                risk_level TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                model_version TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_predictions_request_id
            ON predictions(request_id);
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_predictions_risk_level
            ON predictions(risk_level);
            """
        )

        await db.commit()

    logger.info(
        "SQLite initialized | path=%s",
        DATABASE_PATH,
    )
