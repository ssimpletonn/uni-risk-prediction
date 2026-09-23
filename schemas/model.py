from pydantic import BaseModel

class ModelInfoResponse(BaseModel):
    model_name: str
    model_version: str
    model_type: str
    status: str