from fastapi import APIRouter, Query

from services.demo import seed_weekday_predictions

router = APIRouter(tags=["demo"])


@router.post(
    "/demo/seed-weekdays",
    summary="Создать демонстрационные predictions за разные дни",
)
async def seed_demo_weekdays(
    count: int = Query(
        default=70,
        ge=7,
        le=1000,
        description="Количество демонстрационных записей",
    ),
):
    """
    Учебный endpoint.

    Создает данные за последние 21 день, чтобы можно было
    протестировать выборку по дням недели и пагинацию.
    """

    created = await seed_weekday_predictions(
        count=count
    )

    return {
        "status": "ok",
        "created": created,
        "message": (
            "Demo predictions created. "
            "Use /predictions/by-weekday for pagination."
        ),
    }
