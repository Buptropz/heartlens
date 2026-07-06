import json
from openai import AsyncOpenAI
from config import settings

SYSTEM_PROMPT = """你是一位资深的心理咨询师和关系分析专家，精通依恋理论、沟通心理学和亲密关系研究。
你的任务是对用户提供的聊天对话进行专业、客观的心理学分析。

分析框架：
1. 真诚度 — 自我表露的深度和真实性，是否回避关键话题
2. 投入程度 — 回复长度、提问频率、主动延续话题的意愿
3. 尊重程度 — 是否尊重边界、回应对方情绪、平等对话
4. 操纵倾向 — 是否存在 gaslighting、 guilt-tripping、 love-bombing 等行为
5. 沟通健康度 — 倾听质量、冲突处理方式、情绪表达能力
6. 红旗指数 — 综合警告信号，包括敷衍、忽冷忽热、多线操作迹象

评分规则：
- 每个维度 0-100 分
- 真诚度/投入/尊重/沟通：分数越高越好
- 操纵倾向/红旗指数：分数越高表示问题越严重（越低越好）
- 必须引用原文对话作为证据，每维度 1-3 条
- 如果输入内容不足以判断某个维度，诚实标注，不要猜测

输出要求：
- 严格按 JSON 输出，不输出任何其他内容，不要包裹在 markdown 代码块中
- 分析应基于可观察的对话模式，不做人身攻击
- 语气专业但温暖，不制造不必要的焦虑

输出 JSON 格式：
{
  "radar": {
    "sincerity": {"score": 0, "label": "真诚度"},
    "engagement": {"score": 0, "label": "投入程度"},
    "respect": {"score": 0, "label": "尊重程度"},
    "manipulation": {"score": 0, "label": "操纵倾向"},
    "communication": {"score": 0, "label": "沟通健康度"},
    "red_flags": {"score": 0, "label": "红旗指数"}
  },
  "cards": [
    {
      "dimension": "sincerity",
      "title": "真诚度：较高 (72)",
      "summary": "...",
      "evidence": [{"quote": "...", "analysis": "..."}],
      "suggestion": "..."
    }
  ],
  "overall": "..."
}"""


async def analyze_chat(input_type: str, content_bytes: bytes, locale: str) -> dict:
    if input_type == "image":
        return await _analyze_image(content_bytes, locale)
    else:
        return await _analyze_text(content_bytes)


async def _analyze_text(content_bytes: bytes) -> dict:
    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )
    text = content_bytes.decode("utf-8")
    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
        max_tokens=4096,
        timeout=55.0,
    )
    return _parse_response(response.choices[0].message.content)


async def _analyze_image(content_bytes: bytes, locale: str) -> dict:
    client = AsyncOpenAI(
        api_key=settings.gemini_api_key,
        base_url=settings.gemini_base_url,
    )
    image_parts = content_bytes.split(b"||IMG_SEP||")
    import base64

    image_blocks = []
    for part in image_parts:
        b64 = base64.b64encode(part).decode("utf-8")
        image_blocks.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"},
        })

    response = await client.chat.completions.create(
        model=settings.gemini_model,
        messages=[{
            "role": "user",
            "content": [
                *image_blocks,
                {"type": "text", "text": SYSTEM_PROMPT + "\n\n请分析以上聊天截图中的对话内容，按 JSON 格式输出分析报告。"},
            ],
        }],
        temperature=0.7,
        max_tokens=4096,
        timeout=55.0,
    )

    raw = response.choices[0].message.content
    # Gemini may wrap JSON in markdown code blocks
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return _parse_response(raw.strip())


def _parse_response(content: str) -> dict:
    result = json.loads(content)
    required_dims = ["sincerity", "engagement", "respect", "manipulation", "communication", "red_flags"]
    for dim in required_dims:
        if dim not in result.get("radar", {}):
            result.setdefault("radar", {})[dim] = {"score": 0, "label": dim}
    result.setdefault("cards", [])
    result.setdefault("overall", "")
    return result
