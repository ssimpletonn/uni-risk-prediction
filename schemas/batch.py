from typing import List

from pydantic import BaseModel, Field

from config import MAX_BATCH_SIZE
from schemas.farm import FarmRequest


class BatchRequest(BaseModel):
    """Явный batch, который клиент отправляет одним HTTP-запросом."""

    items: List[FarmRequest] = Field(
        ...,
        min_length=1,
        max_length=MAX_BATCH_SIZE,
        description="Список объектов для пакетного инференса",
    )


class BatchItemResponse(BaseModel):
    farm_id: str
    risk_score: float
    risk_level: str
    recommendation: str
    model_version: str


class BatchPredictionResponse(BaseModel):
    request_id: str
    batch_size: int
    processing_time_ms: float
    items: List[BatchItemResponse]
