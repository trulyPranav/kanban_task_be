from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.comment import Comment
from repositories.base import BaseRepository


class CommentRepository(BaseRepository[Comment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Comment, session)

    async def list_by_task(
        self, task_id: str, offset: int = 0, limit: int = 20
    ) -> tuple[list[Comment], int]:
        count_q = (
            select(func.count())
            .select_from(Comment)
            .where(Comment.task_id == task_id)
        )
        total = (await self.session.execute(count_q)).scalar_one()

        rows = (
            await self.session.execute(
                select(Comment)
                .options(selectinload(Comment.author))
                .where(Comment.task_id == task_id)
                .order_by(Comment.created_at.asc())
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()

        return list(rows), total

    async def get_for_task(
        self, comment_id: str, task_id: str
    ) -> Optional[Comment]:
        result = await self.session.execute(
            select(Comment)
            .options(selectinload(Comment.author))
            .where(Comment.id == comment_id, Comment.task_id == task_id)
        )
        return result.scalar_one_or_none()
