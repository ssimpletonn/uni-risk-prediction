import logging

from fastapi import (
    FastAPI
)
from fastapi.responses import RedirectResponse
from middleware import add_process_time
from routers import predictions, model, health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Agro Scoring API",
    description=(
        "REST API для оценки риска "
        "сельскохозяйственных предприятий."
    ),
    version="1.0.0"
)

app.middleware("http")(add_process_time)
app.include_router(predictions.router)
app.include_router(health.router)
app.include_router(model.router)

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)