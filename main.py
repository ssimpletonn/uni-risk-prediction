# ============================================================
# ЛАБОРАТОРНАЯ РАБОТА №2
# ============================================================

import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from config import LLM_TIMEOUT_SECONDS
from db.connection import init_db
from exceptions import register_exception_handlers
from middleware import request_context_middleware
from routers import (
    demo,
    health,
    inference,
    llm,
    model,
    predictions,
)
from services.inference import batch_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    """
    При старте:
    1. Инициализируем SQLite.
    2. Создаем HTTP-клиент для LLM.
    3. Запускаем batch worker.

    При остановке:
    корректно завершаем worker и закрываем клиент.
    """

    await init_db()

    # Один переиспользуемый HTTP-клиент для внешнего LLM API.
    # Это позволяет использовать connection pooling и не создавать
    # новое TCP-соединение на каждый запрос.
    app.state.llm_client = httpx.AsyncClient(
        timeout=httpx.Timeout(
            LLM_TIMEOUT_SECONDS
        ),
    )

    worker = asyncio.create_task(
        batch_worker()
    )

    app.state.batch_worker = worker

    yield

    worker.cancel()

    try:
        await worker
    except asyncio.CancelledError:
        pass

    await app.state.llm_client.aclose()


app = FastAPI(
    title="Agro Scoring API",
    description=(
        "Agro Scoring API: request_id, SQLite/aiosqlite, "
        "single inference, batching и интеграция с Vireonix LLM."
    ),
    version="4.0.0",
    lifespan=lifespan,
)

app.middleware("http")(request_context_middleware)
register_exception_handlers(app)

app.include_router(health.router)
app.include_router(model.router)
app.include_router(llm.router)
app.include_router(inference.router)
app.include_router(predictions.router)
app.include_router(demo.router)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "Agro Scoring API is running",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
