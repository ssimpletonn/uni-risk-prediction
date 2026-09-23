import time
from fastapi import Request

async def add_process_time(
    request: Request,
    call_next
):
    """
    Middleware выполняется для каждого HTTP-запроса.
    Добавляет в HTTP-ответ заголовок:

        X-Process-Time

    содержащий время обработки запроса.
    """

    start_time = time.perf_counter()

    response = await call_next(request)

    process_time = time.perf_counter() - start_time

    response.headers["X-Process-Time"] = str(
        round(process_time, 6)
    )

    return response