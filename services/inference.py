import asyncio
import logging
import time
from dataclasses import dataclass
from typing import List

from config import (
    INFERENCE_TIMEOUT_SECONDS,
    MAX_BATCH_SIZE,
    MAX_BATCH_WAIT_MS,
    MODEL_FIXED_OVERHEAD_SECONDS,
    MODEL_PER_ITEM_SECONDS,
    QUEUE_MAX_SIZE,
)
from schemas import FarmRequest
from services.scoring import calculate_risk

logger = logging.getLogger(__name__)


# Один lock имитирует один экземпляр модели /
# один вычислительный ресурс.

model_lock = asyncio.Lock()


async def model_predict_single(
    data: FarmRequest,
) -> float:
    """Одиночный вызов модели."""

    async with model_lock:
        await asyncio.sleep(
            MODEL_FIXED_OVERHEAD_SECONDS
            + MODEL_PER_ITEM_SECONDS
        )

        return calculate_risk(
            data
        )


async def model_predict_batch(
    items: List[FarmRequest],
) -> List[float]:
    """Один пакетный вызов модели."""

    async with model_lock:
        await asyncio.sleep(
            MODEL_FIXED_OVERHEAD_SECONDS
            + MODEL_PER_ITEM_SECONDS * len(items)
        )

        return [
            calculate_risk(item)
            for item in items
        ]


# ============================================================
# ОЧЕРЕДЬ ДЛЯ DYNAMIC BATCHING
# ============================================================

inference_queue = asyncio.Queue(
    maxsize=QUEUE_MAX_SIZE
)


@dataclass
class InferenceTask:
    data: FarmRequest
    request_id: str
    future: asyncio.Future


async def batch_worker() -> None:
    """
    Фоновый worker:

    1. Берет первый запрос.
    2. Накопляет дополнительные запросы до MAX_BATCH_SIZE
       или до истечения MAX_BATCH_WAIT_MS.
    3. Выполняет один batch inference.
    4. Возвращает каждому HTTP-запросу его score.
    """

    logger.info(
        "Batch worker started"
    )

    while True:
        first_task = await inference_queue.get()

        if first_task.future.cancelled():
            inference_queue.task_done()
            continue

        batch = [
            first_task
        ]

        deadline = (
            time.perf_counter()
            + MAX_BATCH_WAIT_MS / 1000
        )

        # ----------------------------------------------------
        # Накопление dynamic batch
        # ----------------------------------------------------

        while len(batch) < MAX_BATCH_SIZE:
            remaining_time = (
                deadline
                - time.perf_counter()
            )

            if remaining_time <= 0:
                break

            try:
                task = await asyncio.wait_for(
                    inference_queue.get(),
                    timeout=remaining_time,
                )

                if task.future.cancelled():
                    inference_queue.task_done()
                    continue

                batch.append(
                    task
                )

            except asyncio.TimeoutError:
                break

        logger.info(
            "Dynamic batch formed | size=%s | queue_size=%s",
            len(batch),
            inference_queue.qsize(),
        )

        try:
            scores = await asyncio.wait_for(
                model_predict_batch(
                    [
                        task.data
                        for task in batch
                    ]
                ),
                timeout=INFERENCE_TIMEOUT_SECONDS,
            )

            for task, score in zip(
                batch,
                scores,
            ):
                if not task.future.done():
                    task.future.set_result(
                        score
                    )

        except Exception as exc:
            logger.exception(
                "Batch inference failed"
            )

            for task in batch:
                if not task.future.done():
                    task.future.set_exception(
                        exc
                    )

        finally:
            # На каждый queue.get() должен быть task_done().
            for _ in batch:
                inference_queue.task_done()
