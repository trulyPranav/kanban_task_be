import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ConflictError, NotFoundError
from models.user import User
from repositories.user_repo import UserRepository
from schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = UserRepository(session)

    async def create(self, data: UserCreate) -> User:
        if await self.repo.get_by_email(data.email):
            raise ConflictError(f"Email '{data.email}' is already registered.")
        if await self.repo.get_by_username(data.username):
            raise ConflictError(f"Username '{data.username}' is already taken.")

        user = User(id=str(uuid.uuid4()), **data.model_dump())
        return await self.repo.create(user)

    async def get(self, user_id: str) -> User:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        return user

    async def list(
        self, page: int, page_size: int, search: Optional[str] = None
    ) -> tuple[list[User], int]:
        offset = (page - 1) * page_size
        return await self.repo.list_paginated(offset=offset, limit=page_size, search=search)

    async def update(self, user_id: str, data: UserUpdate) -> User:
        user = await self.get(user_id)

        if data.email and data.email != user.email:
            if await self.repo.get_by_email(data.email):
                raise ConflictError(f"Email '{data.email}' is already registered.")
        if data.username and data.username != user.username:
            if await self.repo.get_by_username(data.username):
                raise ConflictError(f"Username '{data.username}' is already taken.")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        user.updated_at = datetime.now(timezone.utc)
        return user

    async def delete(self, user_id: str) -> None:
        if not await self.repo.delete(user_id):
            raise NotFoundError("User", user_id)
