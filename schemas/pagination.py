from typing import List, Optional

from pydantic import BaseModel

from schemas.farm import PredictionResponse


class PaginationMeta(BaseModel):
    weekday: str
    current_page: int
    per_page: int
    total_pages: int
    total_items: int
    next_page: Optional[str]
    prev_page: Optional[str]


class PaginatedPredictionsResponse(BaseModel):
    data: List[PredictionResponse]
    meta: PaginationMeta
