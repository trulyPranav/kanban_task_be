"""
Faker-based seeder — inserts 50 users, 10 000 tasks and ~25 000 comments.

Run from the `be/` directory:
    python -m seed.seeder
"""

import asyncio
import os
import random
import sys
import uuid
from datetime import datetime, timezone

from faker import Faker
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Allow `be/` to be the root import path when running directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings  # noqa: E402 – path manipulation above
from models.base import Base  # noqa: E402
from models.comment import Comment  # noqa: E402
from models.task import Task, TaskPriority, TaskStatus  # noqa: E402
from models.user import User  # noqa: E402

fake = Faker()
Faker.seed(42)
random.seed(42)

# ─── Configuration ────────────────────────────────────────────────────────────
NUM_USERS = 50
NUM_TASKS = 10_000
COMMENTS_PER_TASK = (0, 5)   # random range per task
BATCH_SIZE = 500              # rows per flush – tune for memory vs speed


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _past(start: str = "-6M") -> datetime:
    return fake.date_time_between(start_date=start, end_date="now", tzinfo=timezone.utc)


def _future(end: str = "+3M") -> datetime:
    return fake.date_time_between(start_date="now", end_date=end, tzinfo=timezone.utc)


# ─── Seeder ───────────────────────────────────────────────────────────────────

async def seed() -> None:
    import ssl as _ssl
    _ssl_ctx = _ssl.create_default_context()
    _ssl_ctx.check_hostname = False
    _ssl_ctx.verify_mode = _ssl.CERT_NONE
    _connect_args: dict = {"statement_cache_size": 0}
    if "postgresql" in settings.DATABASE_URL:
        _connect_args["ssl"] = _ssl_ctx
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        connect_args=_connect_args,
    )

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        # ── Guard: skip if data already present ───────────────────────────────
        existing = (await session.execute(text("SELECT COUNT(*) FROM users"))).scalar_one()
        if existing > 0:
            print(f"[seeder] Database already contains {existing} user(s). Skipping.")
            await engine.dispose()
            return

        # ── 1. Users ──────────────────────────────────────────────────────────
        print(f"[seeder] Creating {NUM_USERS} users …")
        users: list[User] = []
        used_usernames: set[str] = set()
        used_emails: set[str] = set()

        while len(users) < NUM_USERS:
            uname = fake.user_name()[:50]
            email = fake.email()
            if uname in used_usernames or email in used_emails:
                continue
            used_usernames.add(uname)
            used_emails.add(email)
            created = _past("-1y")
            users.append(
                User(
                    id=str(uuid.uuid4()),
                    username=uname,
                    email=email,
                    full_name=fake.name(),
                    avatar_url=f"https://api.dicebear.com/8.x/avataaars/svg?seed={uname}",
                    created_at=created,
                    updated_at=created,
                )
            )

        session.add_all(users)
        await session.flush()
        user_ids = [u.id for u in users]
        print(f"[seeder]  ✓ {len(users)} users inserted.")

        # ── 2. Tasks (batched) ────────────────────────────────────────────────
        print(f"[seeder] Creating {NUM_TASKS} tasks in batches of {BATCH_SIZE} …")
        task_ids: list[str] = []
        statuses = list(TaskStatus)
        priorities = list(TaskPriority)

        for batch_start in range(0, NUM_TASKS, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, NUM_TASKS)
            batch: list[Task] = []
            for _ in range(batch_end - batch_start):
                created = _past("-6M")
                batch.append(
                    Task(
                        id=str(uuid.uuid4()),
                        title=fake.sentence(nb_words=random.randint(4, 10)).rstrip("."),
                        description=(
                            fake.paragraph(nb_sentences=random.randint(1, 5))
                            if random.random() > 0.15
                            else None
                        ),
                        status=random.choice(statuses),
                        priority=random.choice(priorities),
                        due_date=_future() if random.random() > 0.35 else None,
                        assigned_to_id=random.choice(user_ids) if random.random() > 0.20 else None,
                        created_by_id=random.choice(user_ids),
                        created_at=created,
                        updated_at=created,
                    )
                )
            session.add_all(batch)
            await session.flush()
            task_ids.extend(t.id for t in batch)
            print(f"[seeder]   tasks {batch_start + 1}–{batch_end} …")

        print(f"[seeder]  ✓ {NUM_TASKS} tasks inserted.")

        # ── 3. Comments (batched over task chunks) ────────────────────────────
        print("[seeder] Creating comments …")
        total_comments = 0

        for chunk_start in range(0, len(task_ids), BATCH_SIZE):
            chunk = task_ids[chunk_start : chunk_start + BATCH_SIZE]
            comment_batch: list[Comment] = []
            for tid in chunk:
                for _ in range(random.randint(*COMMENTS_PER_TASK)):
                    created = _past("-6M")
                    comment_batch.append(
                        Comment(
                            id=str(uuid.uuid4()),
                            content=fake.paragraph(nb_sentences=random.randint(1, 3)),
                            task_id=tid,
                            user_id=random.choice(user_ids) if random.random() > 0.10 else None,
                            created_at=created,
                            updated_at=created,
                        )
                    )
            if comment_batch:
                session.add_all(comment_batch)
                await session.flush()
                total_comments += len(comment_batch)

        # ── Commit everything ─────────────────────────────────────────────────
        await session.commit()

    print(
        f"\n[seeder] ✅  Seed complete!\n"
        f"           Users    : {NUM_USERS}\n"
        f"           Tasks    : {NUM_TASKS}\n"
        f"           Comments : {total_comments}\n"
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
