from datetime import datetime, timezone
from sqlalchemy import delete
from models.report import Report
from database import async_session


async def cleanup_expired_reports() -> int:
    async with async_session() as session:
        result = await session.execute(
            delete(Report).where(Report.expires_at < datetime.now(timezone.utc))
        )
        await session.commit()
        return result.rowcount
