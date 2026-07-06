import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from main import app
from database import Base, engine, init_db, async_session
from models.report import Report
import models.report  # noqa


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _seed_report(**overrides):
    defaults = {
        "id": "test123",
        "input_type": "text",
        "locale": "zh-CN",
        "score_sincerity": 70, "score_engagement": 50,
        "score_respect": 80, "score_manipulation": 20,
        "score_communication": 60, "score_red_flags": 30,
        "cards": [],
        "overall": "test",
    }
    defaults.update(overrides)
    async with async_session() as session:
        report = Report(**defaults)
        session.add(report)
        await session.commit()


@pytest.mark.asyncio
async def test_get_existing_report_returns_200(client: AsyncClient):
    await _seed_report()
    response = await client.get("/api/report/test123")
    assert response.status_code == 200
    body = response.json()
    assert body["report_id"] == "test123"
    assert body["radar"]["sincerity"]["score"] == 70


@pytest.mark.asyncio
async def test_get_nonexistent_report_returns_404(client: AsyncClient):
    response = await client.get("/api/report/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_expired_report_returns_410(client: AsyncClient):
    await _seed_report(
        id="expired1",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    response = await client.get("/api/report/expired1")
    assert response.status_code == 410
    assert response.json()["error"] == "report_expired"
