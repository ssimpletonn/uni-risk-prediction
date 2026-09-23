from pydantic import BaseModel, Field
from enum import Enum
from typing import List

class RegionEnum(str, Enum):
    Krasnodar = "Krasnodar",
    Rostov = "Rostov",
    Stavropol = "Stavropol"


class PredictionRequest(BaseModel):
    """
    Данные сельскохозяйственного предприятия,
    которые клиент передает в POST /predict
    """

    farm_id: str = Field(
        ...,
        min_length=1,
        description="Идентификатор хозяйства"
    )

    region: RegionEnum = Field(
        ...,
        description="Регион хозяйства"
    )

    crop_type: str = Field(
        ...,
        min_length=1,
        description="Основная сельскохозяйственная культура"
    )

    area_ha: float = Field(
        ...,
        gt=0,
        description="Площадь посевов, га"
    )

    temperature_avg: float = Field(
        ...,
        ge=-60,
        le=60,
        description="Средняя температура, °C"
    )

    precipitation_mm: float = Field(
        ...,
        ge=0,
        description="Количество осадков, мм"
    )

    payment_delay_days: int = Field(
        ...,
        ge=0,
        description="Количество дней просрочки платежа"
    )

    previous_defaults: int = Field(
        ...,
        ge=0,
        description="Количество предыдущих дефолтов"
    )

    debt: float = Field(
        ...,
        ge=0,
        description="Текущая задолженность"
    )

class PredictionResponse(BaseModel):
    """
    Структура предсказания.
    """

    request_id: str
    farm_id: str
    risk_score: float
    risk_level: str
    recommendation: str
    model_version: str

class PredictionsResponse(BaseModel):
    """

    """
    limit: int
    offset: int
    predictions: List[PredictionResponse]