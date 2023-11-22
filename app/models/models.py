from pydantic import BaseModel
from typing import Union


class LLMRequest(BaseModel):
    query: str
    conversation_id: Union[str, None] = None
    response: Union[str, None] = None


class FeedbackRequest(BaseModel):
    conversation_id: int  # required
    feedback_object: str  # a json blob
