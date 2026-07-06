import pytest
from unittest.mock import AsyncMock, patch
from services.analyzer import analyze_chat, SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_analyze_text_returns_structured_result():
    mock_response = {
        "radar": {"sincerity": {"score": 70, "label": "真诚度"}, "engagement": {"score": 50, "label": "投入程度"},
                  "respect": {"score": 80, "label": "尊重程度"}, "manipulation": {"score": 20, "label": "操纵倾向"},
                  "communication": {"score": 60, "label": "沟通健康度"}, "red_flags": {"score": 30, "label": "红旗指数"}},
        "cards": [{"dimension": "sincerity", "title": "真诚度：较高 (70)", "summary": "test",
                   "evidence": [{"quote": "test quote", "analysis": "test analysis"}], "suggestion": "test suggestion"}],
        "overall": "test overall"
    }

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = AsyncMock(
        choices=[AsyncMock(message=AsyncMock(content=str(mock_response).replace("'", '"')))]
    )

    with patch("services.analyzer.AsyncOpenAI", return_value=mock_client):
        result = await analyze_chat("text", "你好\n你好啊".encode("utf-8"), "zh-CN")

    assert result["radar"]["sincerity"]["score"] == 70
    assert result["radar"]["sincerity"]["label"] == "真诚度"
    assert len(result["cards"]) == 1
    assert result["overall"] == "test overall"


@pytest.mark.asyncio
async def test_analyze_raises_on_api_error():
    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = Exception("API down")

    with patch("services.analyzer.AsyncOpenAI", return_value=mock_client):
        with pytest.raises(Exception):
            await analyze_chat("text", "hello".encode("utf-8"), "zh-CN")


def test_system_prompt_is_not_empty():
    assert len(SYSTEM_PROMPT) > 100
    assert "心理咨询师" in SYSTEM_PROMPT or "psychologist" in SYSTEM_PROMPT.lower()
    assert "json" in SYSTEM_PROMPT.lower()
