import pytest
from datetime import datetime, timedelta, timezone
from services.cleaner import cleanup_expired_reports
from database import Base, engine, init_db, async_session
from models.report import Report
import models.report  # noqa


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _seed(id, expires_offset_hours):
    async with async_session() as session:
        report = Report(
            id=id, input_type="text", locale="zh-CN",
            score_sincerity=50, score_engagement=50,
            score_respect=50, score_manipulation=50,
            score_communication=50, score_red_flags=50,
            cards=[], overall="test",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_offset_hours),
        )
        session.add(report)
        await session.commit()


async def _count():
    async with async_session() as session:
        from sqlalchemy import select, func
        result = await session.execute(select(func.count(Report.id)))
        return result.scalar()


@pytest.mark.asyncio
async def test_cleanup_removes_expired_reports():
    await _seed("expired", -1)   # expired 1 hour ago
    await _seed("valid", 24)     # valid, expiring in 24 hours

    deleted = await cleanup_expired_reports()
    assert deleted == 1

    count = await _count()
    assert count == 1
