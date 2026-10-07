from fastapi import APIRouter

from schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Проверка состояния API",
)
async def health():
    return HealthResponse(status="ok")
