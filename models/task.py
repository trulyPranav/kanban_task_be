import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .comment import Comment
    from .user import User


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_status_priority", "status", "priority"),
        Index("ix_tasks_created_at", "created_at"),
        Index("ix_tasks_assigned_created", "assigned_to_id", "created_by_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus), nullable=False, default=TaskStatus.TODO, index=True
    )
    priority: Mapped[TaskPriority] = mapped_column(
        SAEnum(TaskPriority), nullable=False, default=TaskPriority.MEDIUM, index=True
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    assigned_to_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    assignee: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[assigned_to_id],
        back_populates="assigned_tasks",
    )
    creator: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[created_by_id],
        back_populates="created_tasks",
    )
    comments: Mapped[list["Comment"]] = relationship(
        "Comment",
        back_populates="task",
        cascade="all, delete-orphan",
    )
