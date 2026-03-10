from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.rate_limiter import limiter
from schemas.comment import CommentCreate, CommentResponse, CommentUpdate
from schemas.common import PaginatedResponse
from services.comment_service import CommentService

router = APIRouter(
    prefix="/tasks/{task_id}/comments",
    tags=["Comments"],
)


@router.post("/", response_model=CommentResponse, status_code=201, summary="Add a comment to a task")
@limiter.limit("30/minute")
async def add_comment(
    request: Request,
    task_id: str,
    body: CommentCreate,
    db: AsyncSession = Depends(get_db),
) -> CommentResponse:
    svc = CommentService(db)
    comment = await svc.add(task_id, body)
    return CommentResponse.model_validate(comment)


@router.get("/", response_model=PaginatedResponse[CommentResponse], summary="List comments for a task")
@limiter.limit("60/minute")
async def list_comments(
    request: Request,
    task_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[CommentResponse]:
    svc = CommentService(db)
    comments, total = await svc.list(task_id, page, page_size)
    return PaginatedResponse.create(
        items=[CommentResponse.model_validate(c) for c in comments],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.put("/{comment_id}", response_model=CommentResponse, summary="Update a comment")
@limiter.limit("20/minute")
async def update_comment(
    request: Request,
    task_id: str,
    comment_id: str,
    body: CommentUpdate,
    db: AsyncSession = Depends(get_db),
) -> CommentResponse:
    svc = CommentService(db)
    comment = await svc.update(task_id, comment_id, body)
    return CommentResponse.model_validate(comment)


@router.delete("/{comment_id}", status_code=204, summary="Delete a comment")
@limiter.limit("20/minute")
async def delete_comment(
    request: Request,
    task_id: str,
    comment_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = CommentService(db)
    await svc.delete(task_id, comment_id)
