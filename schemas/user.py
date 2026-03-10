from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.\-]+$")
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.\-]+$")
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)


class UserSummary(BaseModel):
    """Lightweight user info embedded in task / comment responses."""

    id: str
    username: str
    full_name: str
    avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserResponse(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
