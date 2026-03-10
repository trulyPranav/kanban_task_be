from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.comment import Comment
from models.task import Task, TaskPriority, TaskStatus
from repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Task, session)

    async def get_by_id_with_relations(self, task_id: str) -> Optional[Task]:
        result = await self.session.execute(
            select(Task)
            .options(selectinload(Task.assignee), selectinload(Task.creator))
            .where(Task.id == task_id)
        )
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        offset: int = 0,
        limit: int = 20,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        assigned_to_id: Optional[str] = None,
        created_by_id: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[list[Task], int]:
        predicates = []
        if status:
            predicates.append(Task.status == status)
        if priority:
            predicates.append(Task.priority == priority)
        if assigned_to_id:
            predicates.append(Task.assigned_to_id == assigned_to_id)
        if created_by_id:
            predicates.append(Task.created_by_id == created_by_id)
        if search:
            like = f"%{search}%"
            predicates.append(
                or_(Task.title.ilike(like), Task.description.ilike(like))
            )

        where_clause = and_(*predicates) if predicates else None

        count_q = select(func.count()).select_from(Task)
        base_q = select(Task).options(
            selectinload(Task.assignee), selectinload(Task.creator)
        )

        if where_clause is not None:
            count_q = count_q.where(where_clause)
            base_q = base_q.where(where_clause)

        total = (await self.session.execute(count_q)).scalar_one()
        rows = (
            await self.session.execute(
                base_q.order_by(Task.created_at.desc()).offset(offset).limit(limit)
            )
        ).scalars().all()

        return list(rows), total

    async def get_comment_counts(self, task_ids: list[str]) -> dict[str, int]:
        """Return a map of task_id -> comment count for the given task IDs."""
        if not task_ids:
            return {}
        result = await self.session.execute(
            select(Comment.task_id, func.count(Comment.id).label("cnt"))
            .where(Comment.task_id.in_(task_ids))
            .group_by(Comment.task_id)
        )
        return {row.task_id: row.cnt for row in result}
