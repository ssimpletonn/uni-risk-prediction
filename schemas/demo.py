from pydantic import BaseModel


class SeedResponse(BaseModel):
    status: str
    created: int
    message: str
