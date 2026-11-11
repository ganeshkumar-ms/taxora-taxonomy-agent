from pydantic import BaseModel
from typing import Optional, List


class ClassifyResponse(BaseModel):
    primary: dict
    alternatives: List[dict]
    status: dict
    summary: str
    follow_up_suggestions: List[str]
    document_metadata: Optional[dict] = None


class FeedbackRequest(BaseModel):
    action: str  # approve | edit | reject
    edited_path: Optional[List[str]] = None


class FeedbackResponse(BaseModel):
    message: str
