from fastapi import APIRouter

from config import MODEL_NAME, MODEL_READY, MODEL_TYPE, MODEL_VERSION
from schemas import ModelInfoResponse

router = APIRouter(tags=["model"])


@router.get(
    "/model-info",
    response_model=ModelInfoResponse,
    summary="Информация о модели",
)
async def model_info():
    return {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "model_type": MODEL_TYPE,
        "status": (
            "ready"
            if MODEL_READY
            else "unavailable"
        ),
    }
