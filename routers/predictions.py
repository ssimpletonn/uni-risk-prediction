from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status

from config import ALLOWED_RISK_LEVELS, WEEKDAY_MAP
from db.predictions import (
    get_predictions_by_request_id,
    get_predictions_by_weekday_page,
    get_predictions_from_db,
)
from schemas import (
    PaginatedPredictionsResponse,
    PaginationMeta,
    PredictionResponse,
)

router = APIRouter(tags=["predictions"])


@router.get(
    "/predictions",
    response_model=List[PredictionResponse],
    summary="Получить историю прогнозов из SQLite",
)
async def get_predictions(
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
    ),
    risk_level: Optional[str] = Query(
        default=None,
        description="low, medium или high",
    ),
):
    if (
        risk_level is not None
        and risk_level not in ALLOWED_RISK_LEVELS
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "risk_level must be "
                "low, medium or high"
            ),
        )

    return await get_predictions_from_db(
        limit=limit,
        risk_level=risk_level,
    )


@router.get(
    "/requests/{request_id}/predictions",
    response_model=List[PredictionResponse],
    summary="Все прогнозы, созданные одним HTTP request",
)
async def get_request_predictions(
    request_id: str,
):
    """
    Для single / queued обычно возвращает один элемент.
    Для explicit batch может вернуть несколько элементов.
    """

    results = await get_predictions_by_request_id(
        request_id
    )

    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found",
        )

    return results


# Важно: объявлен раньше /predictions/{request_id},
# иначе "by-weekday" будет воспринят как request_id.
@router.get(
    "/predictions/by-weekday",
    response_model=PaginatedPredictionsResponse,
    summary="Прогнозы по дню недели с пагинацией",
)
async def get_predictions_by_weekday(
    request: Request,

    weekday: str = Query(
        ...,
        description=(
            "День недели: monday, tuesday, wednesday, "
            "thursday, friday, saturday, sunday"
        ),
    ),

    page: int = Query(
        default=1,
        ge=1,
        description="Номер страницы",
    ),

    size: int = Query(
        default=5,
        ge=1,
        le=100,
        description="Количество записей на странице",
    ),
):
    """
    Пример:
        GET /predictions/by-weekday?weekday=monday&page=1&size=5

    Вернет первые 5 записей для понедельника.
    """

    weekday = weekday.lower()

    if weekday not in WEEKDAY_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "weekday must be one of: "
                "monday, tuesday, wednesday, thursday, "
                "friday, saturday, sunday"
            ),
        )

    (
        data,
        total_items,
        total_pages,
    ) = await get_predictions_by_weekday_page(
        weekday_number=WEEKDAY_MAP[weekday],
        page=page,
        size=size,
    )

    # Если записи существуют, но номер страницы слишком большой.
    if total_pages > 0 and page > total_pages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Page {page} does not exist. "
                f"Total pages: {total_pages}"
            ),
        )

    # Если записей нет вообще, разрешаем только page=1.
    if total_pages == 0 and page > 1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data for this weekday",
        )

    next_page = None

    if page < total_pages:
        next_page = str(
            request.url.include_query_params(
                weekday=weekday,
                page=page + 1,
                size=size,
            )
        )

    prev_page = None

    if page > 1 and total_pages > 0:
        prev_page = str(
            request.url.include_query_params(
                weekday=weekday,
                page=page - 1,
                size=size,
            )
        )

    return PaginatedPredictionsResponse(
        data=data,
        meta=PaginationMeta(
            weekday=weekday,
            current_page=page,
            size=size,
            total_pages=total_pages,
            total_items=total_items,
            next_page=next_page,
            prev_page=prev_page,
        ),
    )


@router.get(
    "/predictions/{request_id}",
    response_model=PredictionResponse,
    summary="Получить одиночный прогноз по request_id",
)
async def get_prediction(
    request_id: str,
):
    """
    Сохраняет обратную совместимость старого API.

    Если request_id относится к batch и в БД несколько строк,
    возвращается 409 и предлагается использовать endpoint:
    /requests/{request_id}/predictions
    """

    results = await get_predictions_by_request_id(
        request_id
    )

    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found",
        )

    if len(results) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This request_id contains multiple predictions. "
                f"Use /requests/{request_id}/predictions"
            ),
        )

    return results[0]
