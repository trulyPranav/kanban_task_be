from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from models.task import TaskPriority, TaskStatus
from schemas.user import UserSummary


# ─── Request schemas ──────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    assigned_to_id: Optional[str] = None
    created_by_id: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    assigned_to_id: Optional[str] = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskFilters(BaseModel):
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assigned_to_id: Optional[str] = None
    created_by_id: Optional[str] = None
    search: Optional[str] = Field(None, max_length=100)


# ─── Response schema ──────────────────────────────────────────────────────────

class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    due_date: Optional[datetime]
    assigned_to_id: Optional[str]
    created_by_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    assignee: Optional[UserSummary] = None
    creator: Optional[UserSummary] = None
    # Computed in service – not a DB column
    comment_count: int = 0

    model_config = ConfigDict(from_attributes=True)
