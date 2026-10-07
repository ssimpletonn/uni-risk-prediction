import asyncio

from fastapi import APIRouter, HTTPException, Request, status

from config import (
    INFERENCE_TIMEOUT_SECONDS,
    LLM_DEFAULT_MAX_TOKENS,
    LLM_DEFAULT_TEMPERATURE,
    LLM_MODEL,
    MODEL_READY,
)
from db.predictions import save_prediction
from schemas import (
    FarmRequest,
    LLMChatRequest,
    LLMChatResponse,
    PredictWithLLMResponse,
)
from services.inference import model_predict_single
from services.llm import (
    build_scoring_explanation_prompt,
    call_vireonix_llm,
)
from services.scoring import (
    make_prediction_result,
    validate_business_rules,
)

router = APIRouter(tags=["llm"])


@router.post(
    "/llm/chat",
    response_model=LLMChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Прямой учебный запрос к Vireonix LLM",
    description=(
        "Отправляет prompt в OpenAI-совместимый Vireonix API. "
        "API-ключ и Authorization header не используются. "
        "Не передавайте реальные конфиденциальные данные."
    ),
)
async def llm_chat(
    data: LLMChatRequest,
    request: Request,
):
    request_id = (
        request.state.request_id
    )

    return await call_vireonix_llm(
        client=request.app.state.llm_client,
        prompt=data.prompt,
        request_id=request_id,
        model=data.model,
        temperature=data.temperature,
        max_tokens=data.max_tokens,
    )


@router.post(
    "/predict-with-llm",
    response_model=PredictWithLLMResponse,
    status_code=status.HTTP_200_OK,
    summary="Агроскоринг с текстовым объяснением LLM",
    description=(
        "Сначала выполняет детерминированный агроскоринг и сохраняет "
        "результат в SQLite. Затем Vireonix LLM формирует только "
        "текстовое объяснение результата. LLM не определяет risk_score."
    ),
)
async def predict_with_llm(
    data: FarmRequest,
    request: Request,
):
    """
    Архитектура:
        FarmRequest
            ↓
        scoring model
            ↓
        SQLite
            ↓
        Vireonix LLM
            ↓
        explanation

    Внешняя LLM не используется для расчета risk_score.
    """

    if not MODEL_READY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is unavailable",
        )

    validate_business_rules(
        data
    )

    request_id = (
        request.state.request_id
    )

    try:
        score = await asyncio.wait_for(
            model_predict_single(
                data
            ),
            timeout=INFERENCE_TIMEOUT_SECONDS,
        )

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Inference timeout",
        )

    prediction = make_prediction_result(
        data,
        score,
        request_id,
    )

    # Сначала сохраняем детерминированный prediction.
    await save_prediction(
        prediction,
        source="single+llm",
    )

    # В публичный LLM endpoint отправляем только уже рассчитанный
    # результат скоринга, без farm_id и исходных финансовых признаков.
    prompt = build_scoring_explanation_prompt(
        prediction
    )

    llm_result = await call_vireonix_llm(
        client=request.app.state.llm_client,
        prompt=prompt,
        request_id=request_id,
        model=LLM_MODEL,
        temperature=LLM_DEFAULT_TEMPERATURE,
        max_tokens=LLM_DEFAULT_MAX_TOKENS,
    )

    return PredictWithLLMResponse(
        prediction=prediction,
        llm=llm_result,
    )
