from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from schemas.user import UserSummary


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    user_id: Optional[str] = None


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class CommentResponse(BaseModel):
    id: str
    task_id: str
    user_id: Optional[str]
    content: str
    created_at: datetime
    updated_at: datetime
    author: Optional[UserSummary] = None

    model_config = ConfigDict(from_attributes=True)
