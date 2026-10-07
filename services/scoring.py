from fastapi import HTTPException, status

from config import ALLOWED_REGIONS, MODEL_VERSION
from schemas import FarmRequest, PredictionResponse


def calculate_risk(
    data: FarmRequest,
) -> float:
    """
    Имитация ML-модели.
    """

    score = 0.1

    if data.payment_delay_days > 30:
        score += 0.3

    if data.previous_defaults > 0:
        score += 0.3

    if data.debt > 5_000_000:
        score += 0.2

    if data.precipitation_mm < 100:
        score += 0.1

    return round(
        min(score, 1.0),
        2,
    )


def get_risk_level(
    score: float,
) -> str:
    if score < 0.3:
        return "low"

    if score < 0.7:
        return "medium"

    return "high"


def get_recommendation(
    level: str,
) -> str:
    if level == "low":
        return "Стандартное рассмотрение"

    if level == "medium":
        return "Требуется дополнительная проверка"

    return "Высокий риск. Требуется ручное рассмотрение"


def validate_business_rules(
    data: FarmRequest,
) -> None:
    """
    Pydantic проверяет типы, обязательность и диапазоны.
    Здесь проверяются правила предметной области.
    """

    if data.region not in ALLOWED_REGIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unknown region: {data.region}. "
                f"Allowed regions: {sorted(ALLOWED_REGIONS)}"
            ),
        )


def make_prediction_result(
    data: FarmRequest,
    score: float,
    request_id: str,
) -> PredictionResponse:
    level = get_risk_level(
        score
    )

    return PredictionResponse(
        request_id=request_id,
        farm_id=data.farm_id,
        risk_score=score,
        risk_level=level,
        recommendation=get_recommendation(level),
        model_version=MODEL_VERSION,
    )
