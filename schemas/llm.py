from typing import Optional

from pydantic import BaseModel, Field

from config import (
    LLM_DEFAULT_MAX_TOKENS,
    LLM_DEFAULT_TEMPERATURE,
    LLM_MODEL,
)
from schemas.farm import PredictionResponse


class LLMChatRequest(BaseModel):
    """
    Запрос к внешней LLM.

    Не передавайте сюда реальные
    конфиденциальные банковские или персональные данные.
    """

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Текст запроса к LLM",
    )

    model: str = Field(
        default=LLM_MODEL,
        min_length=1,
        description="Модель Vireonix. Для демо используется auto",
    )

    temperature: float = Field(
        default=LLM_DEFAULT_TEMPERATURE,
        ge=0.0,
        le=2.0,
    )

    max_tokens: int = Field(
        default=LLM_DEFAULT_MAX_TOKENS,
        ge=1,
        le=2000,
    )


class LLMChatResponse(BaseModel):
    request_id: str
    requested_model: str
    returned_model: Optional[str]
    answer: str
    reasoning: Optional[str] = None
    finish_reason: Optional[str] = None
    usage: Optional[dict] = None
    latency_ms: float


class PredictWithLLMResponse(BaseModel):
    """
    Комбинированный ответ:
    1. детерминированный результат агроскоринга;
    2. текстовое объяснение, сформированное LLM.
    """

    prediction: PredictionResponse
    llm: LLMChatResponse
