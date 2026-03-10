from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.rate_limiter import limiter
from models.task import TaskPriority, TaskStatus
from schemas.common import PaginatedResponse
from schemas.task import (
    TaskCreate,
    TaskFilters,
    TaskResponse,
    TaskStatusUpdate,
    TaskUpdate,
)
from services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def _build_task_response(task, comment_count: int = 0) -> TaskResponse:
    t = TaskResponse.model_validate(task)
    t.comment_count = comment_count
    return t


@router.post("/", response_model=TaskResponse, status_code=201, summary="Create a task")
@limiter.limit("30/minute")
async def create_task(
    request: Request,
    body: TaskCreate,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    svc = TaskService(db)
    task = await svc.create(body)
    return _build_task_response(task)


@router.get("/", response_model=PaginatedResponse[TaskResponse], summary="List tasks (with filters)")
@limiter.limit("60/minute")
async def list_tasks(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by priority"),
    assigned_to_id: Optional[str] = Query(None, description="Filter by assignee user ID"),
    created_by_id: Optional[str] = Query(None, description="Filter by creator user ID"),
    search: Optional[str] = Query(None, max_length=100, description="Full-text search on title / description"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[TaskResponse]:
    svc = TaskService(db)
    filters = TaskFilters(
        status=status,
        priority=priority,
        assigned_to_id=assigned_to_id,
        created_by_id=created_by_id,
        search=search,
    )
    tasks, total, comment_counts = await svc.list(page, page_size, filters)
    items = [_build_task_response(t, comment_counts.get(t.id, 0)) for t in tasks]
    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.get("/{task_id}", response_model=TaskResponse, summary="Get a single task")
@limiter.limit("60/minute")
async def get_task(
    request: Request,
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    svc = TaskService(db)
    task, count = await svc.get_with_comment_count(task_id)
    return _build_task_response(task, count)


@router.put("/{task_id}", response_model=TaskResponse, summary="Update a task")
@limiter.limit("30/minute")
async def update_task(
    request: Request,
    task_id: str,
    body: TaskUpdate,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    svc = TaskService(db)
    task = await svc.update(task_id, body)
    count = await svc.get_comment_count(task_id)
    return _build_task_response(task, count)


@router.patch("/{task_id}/status", response_model=TaskResponse, summary="Update task status (Kanban drag-drop)")
@limiter.limit("60/minute")
async def update_task_status(
    request: Request,
    task_id: str,
    body: TaskStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    svc = TaskService(db)
    task = await svc.update_status(task_id, body)
    count = await svc.get_comment_count(task_id)
    return _build_task_response(task, count)


@router.delete("/{task_id}", status_code=204, summary="Delete a task")
@limiter.limit("20/minute")
async def delete_task(
    request: Request,
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = TaskService(db)
    await svc.delete(task_id)
