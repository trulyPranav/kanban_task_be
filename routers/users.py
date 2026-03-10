from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.rate_limiter import limiter
from schemas.common import PaginatedResponse
from schemas.user import UserCreate, UserResponse, UserUpdate
from services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse, status_code=201, summary="Create a user")
@limiter.limit("20/minute")
async def create_user(
    request: Request,
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    svc = UserService(db)
    return UserResponse.model_validate(await svc.create(body))


@router.get("/", response_model=PaginatedResponse[UserResponse], summary="List users")
@limiter.limit("60/minute")
async def list_users(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, max_length=100, description="Search by name / email / username"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[UserResponse]:
    svc = UserService(db)
    users, total = await svc.list(page, page_size, search)
    return PaginatedResponse.create(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", response_model=UserResponse, summary="Get a user")
@limiter.limit("60/minute")
async def get_user(
    request: Request,
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    svc = UserService(db)
    return UserResponse.model_validate(await svc.get(user_id))


@router.put("/{user_id}", response_model=UserResponse, summary="Update a user")
@limiter.limit("20/minute")
async def update_user(
    request: Request,
    user_id: str,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    svc = UserService(db)
    return UserResponse.model_validate(await svc.update(user_id, body))


@router.delete("/{user_id}", status_code=204, summary="Delete a user")
@limiter.limit("10/minute")
async def delete_user(
    request: Request,
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = UserService(db)
    await svc.delete(user_id)
