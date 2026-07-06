import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from main import app
from database import Base, engine, init_db
import models.report  # noqa: ensure model registered


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await init_db()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


MOCK_ANALYSIS = {
    "radar": {
        "sincerity": {"score": 70, "label": "真诚度"},
        "engagement": {"score": 50, "label": "投入程度"},
        "respect": {"score": 80, "label": "尊重程度"},
        "manipulation": {"score": 20, "label": "操纵倾向"},
        "communication": {"score": 60, "label": "沟通健康度"},
        "red_flags": {"score": 30, "label": "红旗指数"},
    },
    "cards": [{"dimension": "sincerity", "title": "真诚度：较高 (70)", "summary": "...",
               "evidence": [{"quote": "...", "analysis": "..."}], "suggestion": "..."}],
    "overall": "test",
}


@pytest.mark.asyncio
async def test_post_text_analyze_returns_201(client: AsyncClient):
    with patch("routers.analyze.analyze_chat", new=AsyncMock(return_value=MOCK_ANALYSIS)):
        response = await client.post("/api/analyze", data={"text": "你好\n你好啊", "locale": "zh-CN"})
    assert response.status_code == 201
    body = response.json()
    assert "report_id" in body
    assert body["radar"]["sincerity"]["score"] == 70
    assert "share_url" in body


@pytest.mark.asyncio
async def test_post_empty_input_returns_400(client: AsyncClient):
    response = await client.post("/api/analyze", data={})
    assert response.status_code == 400
    assert response.json()["error"] == "empty_input"


@pytest.mark.asyncio
async def test_post_text_and_file_returns_400(client: AsyncClient):
    response = await client.post("/api/analyze", data={"text": "hi", "file": ("test.txt", b"hello")})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_post_text_dedup_returns_201(client: AsyncClient):
    with patch("routers.analyze.analyze_chat", new=AsyncMock(return_value=MOCK_ANALYSIS)):
        r1 = await client.post("/api/analyze", data={"text": "unique text for dedup test"})
        r2 = await client.post("/api/analyze", data={"text": "unique text for dedup test"})
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["report_id"] == r2.json()["report_id"]
