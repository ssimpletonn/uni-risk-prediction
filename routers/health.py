from fastapi import APIRouter
from schemas import HealthResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

@router.get("/health",
    response_model=HealthResponse,
    summary="Проверка состояния API",
    description=(
        "Используется для проверки того, "
        "что REST API запущен и отвечает."
    )
)
def health():
    """
    Проверка работоспособности API.
    """

    return HealthResponse(status="ok")
