import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError
from models.task import Task
from repositories.task_repo import TaskRepository
from repositories.user_repo import UserRepository
from schemas.task import TaskCreate, TaskFilters, TaskStatusUpdate, TaskUpdate


class TaskService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = TaskRepository(session)
        self.user_repo = UserRepository(session)

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _assert_user_exists(self, label: str, user_id: Optional[str]) -> None:
        if user_id and not await self.user_repo.get_by_id(user_id):
            raise NotFoundError(label, user_id)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def create(self, data: TaskCreate) -> Task:
        await self._assert_user_exists("Assignee user", data.assigned_to_id)
        await self._assert_user_exists("Creator user", data.created_by_id)

        task = Task(id=str(uuid.uuid4()), **data.model_dump())
        return await self.repo.create(task)

    async def get(self, task_id: str) -> Task:
        task = await self.repo.get_by_id_with_relations(task_id)
        if not task:
            raise NotFoundError("Task", task_id)
        return task

    async def get_with_comment_count(self, task_id: str) -> tuple[Task, int]:
        task = await self.get(task_id)
        counts = await self.repo.get_comment_counts([task_id])
        return task, counts.get(task_id, 0)

    async def get_comment_count(self, task_id: str) -> int:
        counts = await self.repo.get_comment_counts([task_id])
        return counts.get(task_id, 0)

    async def list(
        self,
        page: int,
        page_size: int,
        filters: TaskFilters,
    ) -> tuple[list[Task], int, dict[str, int]]:
        offset = (page - 1) * page_size
        tasks, total = await self.repo.list_paginated(
            offset=offset,
            limit=page_size,
            status=filters.status,
            priority=filters.priority,
            assigned_to_id=filters.assigned_to_id,
            created_by_id=filters.created_by_id,
            search=filters.search,
        )
        comment_counts = await self.repo.get_comment_counts([t.id for t in tasks])
        return tasks, total, comment_counts

    async def update(self, task_id: str, data: TaskUpdate) -> Task:
        task = await self.get(task_id)

        update_data = data.model_dump(exclude_unset=True)
        if "assigned_to_id" in update_data:
            await self._assert_user_exists("Assignee user", update_data["assigned_to_id"])

        for field, value in update_data.items():
            setattr(task, field, value)
        task.updated_at = datetime.now(timezone.utc)
        return task

    async def update_status(self, task_id: str, data: TaskStatusUpdate) -> Task:
        task = await self.get(task_id)
        task.status = data.status
        task.updated_at = datetime.now(timezone.utc)
        return task

    async def delete(self, task_id: str) -> None:
        if not await self.repo.delete(task_id):
            raise NotFoundError("Task", task_id)
