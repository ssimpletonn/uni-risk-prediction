import uuid

from config import MODEL_VERSION
from db.predictions import insert_seed_predictions
from services.scoring import get_recommendation, get_risk_level


async def seed_weekday_predictions(
    count: int = 70,
) -> int:
    """
    Создает демонстрационные predictions за разные дни.

    created_at распределяется по последним 21 дням,
    поэтому в базе появляются записи для всех дней недели.
    """

    rows = []

    for i in range(count):
        request_id = str(uuid.uuid4())
        farm_id = f"DEMO-{i + 1:03d}"

        risk_score = round(
            min(0.1 + (i % 9) * 0.1, 1.0),
            2,
        )

        risk_level = get_risk_level(risk_score)

        rows.append(
            (
                request_id,
                farm_id,
                risk_score,
                risk_level,
                get_recommendation(risk_level),
                MODEL_VERSION,
                "seed",
                f"-{i % 21} days",
            )
        )

    await insert_seed_predictions(rows)

    return count
