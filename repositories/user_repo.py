from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        offset: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
    ) -> tuple[list[User], int]:
        base_q = select(User)
        count_q = select(func.count()).select_from(User)

        if search:
            like = f"%{search}%"
            predicate = or_(
                User.username.ilike(like),
                User.full_name.ilike(like),
                User.email.ilike(like),
            )
            base_q = base_q.where(predicate)
            count_q = count_q.where(predicate)

        total = (await self.session.execute(count_q)).scalar_one()
        rows = (
            await self.session.execute(
                base_q.order_by(User.created_at.desc()).offset(offset).limit(limit)
            )
        ).scalars().all()

        return list(rows), total
