from pydantic import BaseModel

class FallbackResponse(BaseModel):
    message: str