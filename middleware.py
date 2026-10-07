import logging
import time
import uuid

from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def request_context_middleware(
    request: Request,
    call_next,
):
    """
    request_id:
    - принимается из X-Request-ID;
    - если отсутствует, сервер создает UUID;
    - сохраняется в request.state;
    - возвращается клиенту в X-Request-ID.

    Также измеряется полное время HTTP-запроса.
    """

    start_time = time.perf_counter()

    request_id = request.headers.get(
        "X-Request-ID"
    )

    if not request_id:
        request_id = str(
            uuid.uuid4()
        )

    request.state.request_id = request_id

    logger.info(
        "Request started | "
        "request_id=%s | method=%s | path=%s",
        request_id,
        request.method,
        request.url.path,
    )

    try:
        response = await call_next(
            request
        )

    except Exception:
        logger.exception(
            "Unhandled error | request_id=%s",
            request_id,
        )

        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "request_id": request_id,
            },
        )

    process_time = (
        time.perf_counter()
        - start_time
    )

    response.headers[
        "X-Request-ID"
    ] = request_id

    response.headers[
        "X-Process-Time"
    ] = str(
        round(
            process_time,
            6,
        )
    )

    logger.info(
        "Request completed | "
        "request_id=%s | status=%s | time=%.4f",
        request_id,
        response.status_code,
        process_time,
    )

    return response
