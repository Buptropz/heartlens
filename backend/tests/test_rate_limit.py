import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from database import get_db

MOCK_ANALYSIS = {
    "radar": {
        "sincerity": {"score": 70, "label": "真诚度"},
        "engagement": {"score": 50, "label": "投入程度"},
        "respect": {"score": 80, "label": "尊重程度"},
        "manipulation": {"score": 20, "label": "操纵倾向"},
        "communication": {"score": 60, "label": "沟通健康度"},
        "red_flags": {"score": 30, "label": "红旗指数"},
    },
    "cards": [],
    "overall": "test",
}


async def _mock_get_db():
    """Override get_db to return a mock session that simulates real DB behavior."""
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

    async def _mock_commit():
        pass

    async def _mock_refresh(instance, attribute_names=None):
        # Populate server-default fields as a real DB would
        now = datetime.now(timezone.utc)
        if not instance.id:
            instance.id = "test" + str(id(instance))[-10:]
        if not instance.created_at:
            instance.created_at = now
        if not instance.expires_at:
            instance.expires_at = now + timedelta(days=30)

    session.commit = AsyncMock(side_effect=_mock_commit)
    session.refresh = AsyncMock(side_effect=_mock_refresh)
    yield session


@pytest.fixture(autouse=True)
def override_db():
    """Override the DB dependency for all tests in this module."""
    app.dependency_overrides[get_db] = _mock_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Clear rate limit state between tests."""
    from middleware import _window_requests
    _window_requests.clear()
    yield
    _window_requests.clear()


@pytest.mark.asyncio
async def test_rate_limit_returns_429_after_exceeded(client: AsyncClient):
    with patch("routers.analyze.analyze_chat", new=AsyncMock(return_value=MOCK_ANALYSIS)):
        # Send 11 requests (limit is 10/hour)
        for i in range(11):
            response = await client.post("/api/analyze", data={"text": f"test {i}"})
        last = response

    assert last.status_code == 429
    assert last.json()["error"] == "rate_limited"
