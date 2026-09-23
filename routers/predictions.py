from fastapi import APIRouter, status, HTTPException, Query
import logging
import uuid

from schemas.farm import PredictionResponse, PredictionsResponse
from storage import predictions
from typing import Optional, List

router = APIRouter(tags=['predictions'])

logger = logging.getLogger(__name__)

@router.get(
    "/predictions",
    response_model=PredictionsResponse,
    summary="Получить список прогнозов",
    description=(
            "Возвращает список выполненных прогнозов. "
            "Поддерживает ограничение количества результатов "
            "и фильтрацию по уровню риска."
    )
)
def get_predictions(
        offset: int = Query(
            default=0,
            description="Отступ для пагинации"
        ),
        limit: int = Query(
            default=10,
            ge=1,
            le=100,
            description="Максимальное количество результатов"
        ),
        risk_level: Optional[str] = Query(
            default=None,
            description=(
                    "Фильтр по категории риска: "
                    "low, medium или high"
            )
        )

):
    """
    Получение списка прогнозов.
    """

    # Преобразуем словарь в список
    values = list(predictions.values())

    # Проверяем корректность risk_level

    allowed_levels = {
        "low",
        "medium",
        "high"
    }

    if risk_level is not None:

        if risk_level not in allowed_levels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "risk_level must be "
                    "'low', 'medium' or 'high'"
                )
            )

        # Фильтрация

        values = [
            item
            for item in values
            if item.risk_level == risk_level
        ]

    return PredictionsResponse(
        limit=limit,
        offset=offset,
        predictions=values[offset:offset+limit]
    )

@router.get(
    "/predictions/{request_id}",
    response_model=PredictionResponse,
    summary="Получить прогноз по request_id",
    description=(
            "Возвращает сохраненный прогноз "
            "по его уникальному идентификатору."
    )
)
def get_prediction(request_id: str):
    """
    Получение одного прогноза
    по request_id.
    """

    # Проверяем наличие прогноза

    if request_id not in predictions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found"
        )

    # Возвращаем прогноз

    return predictions[request_id]
