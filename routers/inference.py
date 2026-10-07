import asyncio
import logging
import time

from fastapi import APIRouter, HTTPException, Request, status

from config import (
    INFERENCE_TIMEOUT_SECONDS,
    MAX_BATCH_SIZE,
    MAX_BATCH_WAIT_MS,
    MODEL_READY,
    MODEL_VERSION,
    QUEUE_MAX_SIZE,
)
from db.predictions import save_prediction, save_predictions_batch
from schemas import (
    BatchPredictionResponse,
    BatchRequest,
    FarmRequest,
    PredictionResponse,
)
from services.inference import (
    InferenceTask,
    inference_queue,
    model_predict_batch,
    model_predict_single,
)
from services.scoring import (
    get_recommendation,
    get_risk_level,
    make_prediction_result,
    validate_business_rules,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["inference"])


@router.post(
    "/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Одиночный inference",
)
async def predict(
    data: FarmRequest,
    request: Request,
):
    """
    Один HTTP-request -> один inference -> одна запись SQLite.
    """

    if not MODEL_READY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is unavailable",
        )

    validate_business_rules(
        data
    )

    request_id = (
        request.state.request_id
    )

    try:
        score = await asyncio.wait_for(
            model_predict_single(
                data
            ),
            timeout=INFERENCE_TIMEOUT_SECONDS,
        )

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Inference timeout",
        )

    result = make_prediction_result(
        data,
        score,
        request_id,
    )

    # Важно:
    # HTTP 200 возвращается только после успешного COMMIT.
    await save_prediction(
        result,
        source="single",
    )

    return result


@router.post(
    "/batch-predict",
    response_model=BatchPredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Явный пакетный inference",
)
async def batch_predict(
    batch: BatchRequest,
    request: Request,
):
    """
    Клиент сам передает несколько хозяйств одним HTTP-запросом.

    Все результаты batch сохраняются в SQLite одной транзакцией:
    executemany() + один commit().
    """

    if not MODEL_READY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is unavailable",
        )

    for item in batch.items:
        validate_business_rules(
            item
        )

    request_id = (
        request.state.request_id
    )

    start_time = time.perf_counter()

    try:
        scores = await asyncio.wait_for(
            model_predict_batch(
                batch.items
            ),
            timeout=INFERENCE_TIMEOUT_SECONDS,
        )

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Batch inference timeout",
        )

    response_items = []

    for data, score in zip(
        batch.items,
        scores,
    ):
        level = get_risk_level(
            score
        )

        response_items.append(
            {
                "farm_id": data.farm_id,
                "risk_score": score,
                "risk_level": level,
                "recommendation": get_recommendation(
                    level
                ),
                "model_version": MODEL_VERSION,
            }
        )

    # Сохраняем весь batch одной транзакцией.
    await save_predictions_batch(
        request_id=request_id,
        items=response_items,
    )

    processing_time_ms = (
        time.perf_counter()
        - start_time
    ) * 1000

    return {
        "request_id": request_id,
        "batch_size": len(
            batch.items
        ),
        "processing_time_ms": round(
            processing_time_ms,
            2,
        ),
        "items": response_items,
    }


@router.post(
    "/predict-queued",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Inference через очередь и dynamic batching",
)
async def predict_queued(
    data: FarmRequest,
    request: Request,
):
    """
    С точки зрения клиента это одиночный HTTP-request.

    Сервер помещает его в asyncio.Queue и может объединить
    несколько запросов в один вызов модели.

    После получения score каждый запрос отдельно сохраняет
    свой результат в SQLite.
    """

    if not MODEL_READY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is unavailable",
        )

    validate_business_rules(
        data
    )

    request_id = (
        request.state.request_id
    )

    # --------------------------------------------------------
    # BACKPRESSURE
    # --------------------------------------------------------

    if inference_queue.full():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Inference queue is full. "
                "Try again later."
            ),
            headers={
                "Retry-After": "1",
            },
        )

    loop = asyncio.get_running_loop()

    future = loop.create_future()

    task = InferenceTask(
        data=data,
        request_id=request_id,
        future=future,
    )

    try:
        inference_queue.put_nowait(
            task
        )

    except asyncio.QueueFull:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Inference queue is full",
            headers={
                "Retry-After": "1",
            },
        )

    logger.info(
        "Request queued | "
        "request_id=%s | queue_size=%s",
        request_id,
        inference_queue.qsize(),
    )

    try:
        score = await asyncio.wait_for(
            future,
            timeout=INFERENCE_TIMEOUT_SECONDS,
        )

    except asyncio.TimeoutError:
        if not future.done():
            future.cancel()

        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Inference timeout",
        )

    result = make_prediction_result(
        data,
        score,
        request_id,
    )

    await save_prediction(
        result,
        source="queued",
    )

    return result


@router.get(
    "/queue-status",
    summary="Состояние очереди и настройки batching",
)
async def queue_status():
    return {
        "queue_size": inference_queue.qsize(),
        "queue_max_size": QUEUE_MAX_SIZE,
        "max_batch_size": MAX_BATCH_SIZE,
        "max_batch_wait_ms": MAX_BATCH_WAIT_MS,
        "inference_timeout_seconds": INFERENCE_TIMEOUT_SECONDS,
    }
