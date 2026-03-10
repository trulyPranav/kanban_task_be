import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError
from models.comment import Comment
from repositories.comment_repo import CommentRepository
from repositories.task_repo import TaskRepository
from repositories.user_repo import UserRepository
from schemas.comment import CommentCreate, CommentUpdate


class CommentService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = CommentRepository(session)
        self.task_repo = TaskRepository(session)
        self.user_repo = UserRepository(session)

    async def add(self, task_id: str, data: CommentCreate) -> Comment:
        if not await self.task_repo.get_by_id(task_id):
            raise NotFoundError("Task", task_id)
        if data.user_id and not await self.user_repo.get_by_id(data.user_id):
            raise NotFoundError("User", data.user_id)

        comment = Comment(id=str(uuid.uuid4()), task_id=task_id, **data.model_dump())
        created = await self.repo.create(comment)
        # Re-fetch with author relation for the response
        return await self.repo.get_for_task(created.id, task_id)  # type: ignore[return-value]

    async def list(
        self, task_id: str, page: int, page_size: int
    ) -> tuple[list[Comment], int]:
        if not await self.task_repo.get_by_id(task_id):
            raise NotFoundError("Task", task_id)
        offset = (page - 1) * page_size
        return await self.repo.list_by_task(task_id, offset=offset, limit=page_size)

    async def update(self, task_id: str, comment_id: str, data: CommentUpdate) -> Comment:
        comment = await self.repo.get_for_task(comment_id, task_id)
        if not comment:
            raise NotFoundError("Comment", comment_id)
        comment.content = data.content
        comment.updated_at = datetime.now(timezone.utc)
        return comment

    async def delete(self, task_id: str, comment_id: str) -> None:
        comment = await self.repo.get_for_task(comment_id, task_id)
        if not comment:
            raise NotFoundError("Comment", comment_id)
        await self.repo.delete(comment_id)
