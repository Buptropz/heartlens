import nanoid
from sqlalchemy import String, SmallInteger, Text, DateTime, func
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timedelta
from database import Base

def _new_id():
    return nanoid.generate(size=12)

class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=_new_id)
    input_type: Mapped[str] = mapped_column(String(10), nullable=False)
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="zh-CN")

    score_sincerity: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    score_engagement: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    score_respect: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    score_manipulation: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    score_communication: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    score_red_flags: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    cards: Mapped[dict] = mapped_column(JSONB, nullable=False)
    overall: Mapped[str] = mapped_column(Text, nullable=False)

    client_ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now() + timedelta(days=30),
    )
