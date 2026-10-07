import logging
import math
from typing import List, Optional

import aiosqlite
from fastapi import HTTPException, status

from db.connection import get_db
from schemas import BatchItemResponse, PredictionResponse

logger = logging.getLogger(__name__)

INSERT_PREDICTION_SQL = """
    INSERT INTO predictions (
        request_id,
        farm_id,
        risk_score,
        risk_level,
        recommendation,
        model_version,
        source
    )
    VALUES (?, ?, ?, ?, ?, ?, ?);
"""


def _storage_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Prediction storage is unavailable",
    )


async def save_prediction(
    result: PredictionResponse,
    source: str,
) -> None:
    """
    Сохраняет один prediction.

    request_id не используется как PRIMARY KEY:
    один HTTP batch-request может породить несколько прогнозов
    с одним и тем же request_id.
    """

    try:
        async with get_db() as db:
            await db.execute(
                INSERT_PREDICTION_SQL,
                (
                    result.request_id,
                    result.farm_id,
                    result.risk_score,
                    result.risk_level,
                    result.recommendation,
                    result.model_version,
                    source,
                ),
            )

            await db.commit()

    except aiosqlite.Error as exc:
        logger.exception(
            "Database write error | request_id=%s",
            result.request_id,
        )

        raise _storage_unavailable() from exc


async def save_predictions_batch(
    request_id: str,
    items: List[BatchItemResponse],
) -> None:
    """
    Сохраняет весь batch через executemany()
    и один COMMIT.
    """

    rows = [
        (
            request_id,
            item.farm_id,
            item.risk_score,
            item.risk_level,
            item.recommendation,
            item.model_version,
            "batch",
        )
        for item in items
    ]

    try:
        async with get_db() as db:
            await db.executemany(
                INSERT_PREDICTION_SQL,
                rows,
            )

            await db.commit()

    except aiosqlite.Error as exc:
        logger.exception(
            "Batch database write error | request_id=%s",
            request_id,
        )

        raise _storage_unavailable() from exc


async def get_predictions_from_db(
    limit: int,
    risk_level: Optional[str] = None,
) -> List[PredictionResponse]:
    """Возвращает историю прогнозов из SQLite."""

    try:
        async with get_db() as db:
            if risk_level is None:
                cursor = await db.execute(
                    """
                    SELECT
                        request_id,
                        farm_id,
                        risk_score,
                        risk_level,
                        recommendation,
                        model_version
                    FROM predictions
                    ORDER BY id DESC
                    LIMIT ?;
                    """,
                    (limit,),
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT
                        request_id,
                        farm_id,
                        risk_score,
                        risk_level,
                        recommendation,
                        model_version
                    FROM predictions
                    WHERE risk_level = ?
                    ORDER BY id DESC
                    LIMIT ?;
                    """,
                    (
                        risk_level,
                        limit,
                    ),
                )

            rows = await cursor.fetchall()
            await cursor.close()

        return [
            PredictionResponse(**dict(row))
            for row in rows
        ]

    except aiosqlite.Error as exc:
        logger.exception(
            "Database read error"
        )

        raise _storage_unavailable() from exc


async def get_predictions_by_weekday_page(
    weekday_number: str,
    page: int,
    per_page: int,
) -> tuple[List[PredictionResponse], int, int]:
    """
    Возвращает одну страницу прогнозов для выбранного дня недели.

    Используется классическая offset-pagination:
        LIMIT ? OFFSET ?

    Пример:
        page=1, per_page=5 -> LIMIT 5 OFFSET 0
        page=2, per_page=5 -> LIMIT 5 OFFSET 5
    """

    offset = (page - 1) * per_page

    try:
        async with get_db() as db:
            # 1. Получаем записи текущей страницы.
            cursor = await db.execute(
                """
                SELECT
                    request_id,
                    farm_id,
                    risk_score,
                    risk_level,
                    recommendation,
                    model_version
                FROM predictions
                WHERE strftime('%w', created_at) = ?
                ORDER BY id DESC
                LIMIT ? OFFSET ?;
                """,
                (
                    weekday_number,
                    per_page,
                    offset,
                ),
            )

            rows = await cursor.fetchall()
            await cursor.close()

            # 2. Считаем общее количество записей этого дня недели.
            cursor = await db.execute(
                """
                SELECT COUNT(*)
                FROM predictions
                WHERE strftime('%w', created_at) = ?;
                """,
                (weekday_number,),
            )

            row = await cursor.fetchone()
            await cursor.close()

        total_items = row[0]

        total_pages = (
            math.ceil(total_items / per_page)
            if total_items > 0
            else 0
        )

        return (
            [PredictionResponse(**dict(row)) for row in rows],
            total_items,
            total_pages,
        )

    except aiosqlite.Error as exc:
        logger.exception(
            "Database read error | weekday=%s",
            weekday_number,
        )

        raise _storage_unavailable() from exc


async def get_predictions_by_request_id(
    request_id: str,
) -> List[PredictionResponse]:
    """
    Возвращает все прогнозы, связанные с HTTP request_id.

    Для /predict и /predict-queued обычно будет одна строка.
    Для /batch-predict — несколько строк.
    """

    try:
        async with get_db() as db:
            cursor = await db.execute(
                """
                SELECT
                    request_id,
                    farm_id,
                    risk_score,
                    risk_level,
                    recommendation,
                    model_version
                FROM predictions
                WHERE request_id = ?
                ORDER BY id;
                """,
                (request_id,),
            )

            rows = await cursor.fetchall()
            await cursor.close()

        return [
            PredictionResponse(**dict(row))
            for row in rows
        ]

    except aiosqlite.Error as exc:
        logger.exception(
            "Database read error | request_id=%s",
            request_id,
        )

        raise _storage_unavailable() from exc


async def insert_seed_predictions(
    rows: List[tuple],
) -> None:
    """
    Вставляет демонстрационные predictions.

    Каждая строка: (request_id, farm_id, risk_score, risk_level,
    recommendation, model_version, source, created_at_offset),
    где created_at_offset — модификатор SQLite datetime, например '-3 days'.
    """

    try:
        async with get_db() as db:
            await db.executemany(
                """
                INSERT INTO predictions (
                    request_id,
                    farm_id,
                    risk_score,
                    risk_level,
                    recommendation,
                    model_version,
                    source,
                    created_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?,
                    datetime('now', ?)
                );
                """,
                rows,
            )

            await db.commit()

    except aiosqlite.Error as exc:
        logger.exception(
            "Demo seed database error"
        )

        raise _storage_unavailable() from exc
