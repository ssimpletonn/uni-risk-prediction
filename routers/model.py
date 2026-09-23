from fastapi import APIRouter, status, HTTPException
from schemas import (
    ModelInfoResponse, PredictionResponse,
    PredictionRequest
)
import uuid
import logging

from services.model import calculate_risk, get_recommendation, get_risk_level
from config import MODEL_NAME, MODEL_VERSION, MODEL_TYPE, MODEL_READY, ALLOWED_REGIONS
from storage import predictions

logger = logging.getLogger(__name__)

router = APIRouter(tags=['model'])

@router.post(
    "/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Оценить риск хозяйства",
    description=(
            "Принимает характеристики хозяйства, "
            "выполняет валидацию, инференс модели "
            "и возвращает оценку риска."
    )
)
def predict(request: PredictionRequest):
    """
    Основной endpoint сервиса.
    """

    if not MODEL_READY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is temporarily unavailable"
        )

    if request.region not in ALLOWED_REGIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unknown region: {request.region}. "
                f"Allowed regions: "
                f"{sorted(ALLOWED_REGIONS)}"
            )
        )

    logger.info(
        "Prediction request received | farm_id=%s",
        request.farm_id
    )

    score = calculate_risk(request)

    level = get_risk_level(score)

    recommendation = get_recommendation(level)


    request_id = str(uuid.uuid4())

    result = PredictionResponse(
        request_id=request_id,
        farm_id=request.farm_id,
        risk_score=score,
        risk_level=level,
        recommendation=recommendation,
        model_version=MODEL_VERSION
    )

    predictions[request_id] = result

    logger.info(
        "Prediction completed | "
        "request_id=%s | "
        "farm_id=%s | "
        "risk_score=%s | "
        "risk_level=%s",
        request_id,
        request.farm_id,
        score,
        level
    )

    return result


@router.get(
    "/model-info",
    response_model=ModelInfoResponse,
    summary="Информация о модели",
    description=(
        "Возвращает название, версию, тип "
        "и текущее состояние модели."
    )
)
def model_info():
    """
    Возвращает информацию
    об используемой ML-модели.
    """
    model_status = 'ready' if MODEL_READY  else 'unavailable'

    return ModelInfoResponse(
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        model_type=MODEL_TYPE,
        status=model_status
    )