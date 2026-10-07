from pydantic import BaseModel


class QueueStatusResponse(BaseModel):
    queue_size: int
    queue_max_size: int
    max_batch_size: int
    max_batch_wait_ms: int
    inference_timeout_seconds: float
