# HeartLens Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build HeartLens — a free, login-free web app that analyzes chat conversations via DeepSeek AI and generates psychology-framed relationship risk reports with radar charts and evidence-backed dimension cards.

**Architecture:** React SPA (Vite + Tailwind) communicates with FastAPI backend over REST. Backend validates input, calls DeepSeek API with structured JSON output, stores reports in PostgreSQL, and returns results to frontend. A background cleanup job deletes expired reports daily.

**Tech Stack:** React 18 + Vite + Tailwind CSS + React Router v6, FastAPI + SQLAlchemy 2.0 (async) + asyncpg + PostgreSQL, DeepSeek API, @shabon/fx + CSS conic-gradient for visual effects.

## Global Constraints

- All error responses use `{ "error": "<key>", "detail": "..." }` format
- No raw chat content stored — only `evidence.quote` snippets from AI output
- Rate limit: 10 req/IP/hour
- Reports auto-expire after 30 days (configurable via `REPORT_TTL_DAYS`)
- No user accounts, no login, no payments
- zh-CN locale default; `locale` param supported but not validated beyond format
- Backend runs on port 8000; frontend dev server on port 5173 with `/api` proxy
- All Python code async where I/O is involved; TypeScript strict mode

---

### Task 1: Backend scaffolding

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/config.py`
- Create: `backend/main.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

**Interfaces:**
- Produces: `Settings` class (config.py), FastAPI `app` instance (main.py), `test_client` fixture (conftest.py)

- [ ] **Step 1: Write requirements.txt**

```txt
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy[asyncio]==2.0.35
asyncpg==0.30.0
httpx==0.27.0
python-multipart==0.0.12
pydantic-settings==2.5.0
pytest==8.3.0
pytest-asyncio==0.24.0
```

- [ ] **Step 2: Install dependencies**

Run: `cd backend && pip install -r requirements.txt`

- [ ] **Step 3: Write config.py**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/heartlens"
    report_ttl_days: int = 30
    rate_limit_per_hour: int = 10
    cors_origins: str = "http://localhost:5173"
    share_domain: str = "http://localhost:5173"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()
```

- [ ] **Step 4: Write main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings

app = FastAPI(title="HeartLens API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Write conftest.py**

```python
import pytest
from httpx import ASGITransport, AsyncClient
from main import app

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

- [ ] **Step 6: Run health check test**

Run: `cd backend && python -m pytest tests/ -v -k "not implemented"`
Expected: PASS (0 tests collected, or 1 test if you write a quick health test)

- [ ] **Step 7: Commit**

```bash
git add backend/requirements.txt backend/config.py backend/main.py backend/tests/
git commit -m "feat: scaffold FastAPI backend with config and health endpoint"
```

---

### Task 2: Database model and connection

**Files:**
- Create: `backend/database.py`
- Create: `backend/models/__init__.py`
- Create: `backend/models/report.py`

**Interfaces:**
- Consumes: `settings` from config.py
- Produces: `get_db()` async generator, `Report` SQLAlchemy model, `init_db()` async function

- [ ] **Step 1: Write a failing import test**

Create `backend/tests/test_models.py`:

```python
import pytest

def test_can_import_report_model():
    from models.report import Report
    assert Report.__tablename__ == "reports"
```

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: FAIL (module not found / import error)

- [ ] **Step 2: Write database.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with async_session() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 3: Write models/report.py**

```python
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
```

- [ ] **Step 4: Install nanoid, update requirements.txt**

```bash
cd backend && pip install nanoid && echo "nanoid==2.0.0" >> requirements.txt
```

- [ ] **Step 5: Run model import test**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/database.py backend/models/ backend/requirements.txt backend/tests/test_models.py
git commit -m "feat: add Report model and async database connection"
```

---

### Task 3: Input validation

**Files:**
- Create: `backend/validation.py`
- Create: `backend/tests/test_validation.py`

**Interfaces:**
- Consumes: FastAPI `UploadFile` objects, `Form` string fields
- Produces: `validate_analyze_request()` — raises `HTTPException` or returns `(input_type, content_bytes, locale)`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_validation.py`:

```python
import pytest
import io
from fastapi import HTTPException, UploadFile
from validation import validate_analyze_request

class FakeUploadFile:
    def __init__(self, filename, content, content_type="text/plain"):
        self.filename = filename
        self.file = io.BytesIO(content.encode() if isinstance(content, str) else content)
        self.content_type = content_type
        self.size = len(content) if isinstance(content, bytes) else len(content.encode())

async def test_empty_input_raises():
    with pytest.raises(HTTPException) as exc:
        await validate_analyze_request(None, "", None)
    assert exc.value.status_code == 400
    assert "empty_input" in exc.value.detail

async def test_ambiguous_input_raises():
    img = FakeUploadFile("chat.png", b"fakeimage", "image/png")
    with pytest.raises(HTTPException) as exc:
        await validate_analyze_request([img], "also text", None)
    assert exc.value.status_code == 400
    assert "ambiguous_input" in exc.value.detail

async def test_text_too_long_raises():
    long_text = "哈" * 20001
    with pytest.raises(HTTPException) as exc:
        await validate_analyze_request(None, long_text, None)
    assert exc.value.status_code == 413
    assert "text_too_long" in exc.value.detail

async def test_image_count_too_many_raises():
    imgs = [FakeUploadFile(f"chat{i}.png", b"fake", "image/png") for i in range(6)]
    with pytest.raises(HTTPException) as exc:
        await validate_analyze_request(imgs, "", None)
    assert exc.value.status_code == 400

async def test_unsupported_image_format_raises():
    img = FakeUploadFile("chat.bmp", b"fake", "image/bmp")
    with pytest.raises(HTTPException) as exc:
        await validate_analyze_request([img], "", None)
    assert exc.value.status_code == 415

async def test_valid_text_returns_parsed():
    input_type, content, locale = await validate_analyze_request(None, "你好，最近怎么样？", None)
    assert input_type == "text"
    assert b"你好" in content
    assert locale == "zh-CN"

async def test_valid_images_return_parsed():
    img = FakeUploadFile("chat.png", b"fakeimage", "image/png")
    input_type, content, locale = await validate_analyze_request([img], "", None)
    assert input_type == "image"
    assert locale == "zh-CN"

async def test_file_unsupported_format_raises():
    f = FakeUploadFile("chat.pdf", b"pdfcontent", "application/pdf")
    with pytest.raises(HTTPException) as exc:
        await validate_analyze_request(None, "", f)
    assert exc.value.status_code == 415

async def test_valid_file_returns_parsed():
    f = FakeUploadFile("chat.txt", b"user1: hello\nuser2: hi")
    input_type, content, locale = await validate_analyze_request(None, "", f)
    assert input_type == "file"
```

Run: `cd backend && python -m pytest tests/test_validation.py -v`
Expected: FAIL (module not found)

- [ ] **Step 2: Write validation.py**

```python
import hashlib
from fastapi import HTTPException, UploadFile

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_FILE_EXTS = {".txt", ".json"}
MAX_IMAGES = 5
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_FILE_SIZE = 5 * 1024 * 1024    # 5 MB
MAX_TEXT_LENGTH = 20000
VALID_LOCALES = {"zh-CN", "zh-TW", "en"}

async def validate_analyze_request(
    images: list[UploadFile] | None,
    text: str | None,
    file: UploadFile | None,
    locale: str = "zh-CN",
) -> tuple[str, bytes, str]:
    provided = sum(1 for x in [
        images is not None and len(images) > 0,
        text is not None and text.strip() != "",
        file is not None,
    ] if x)

    if provided == 0:
        raise HTTPException(400, detail={"error": "empty_input", "detail": "请提供聊天截图、文本或文件"})
    if provided > 1:
        raise HTTPException(400, detail={"error": "ambiguous_input", "detail": "请只选择一种输入方式"})

    if locale not in VALID_LOCALES:
        locale = "zh-CN"

    if images is not None and len(images) > 0:
        if len(images) > MAX_IMAGES:
            raise HTTPException(400, detail={"error": "too_many_images", "detail": f"最多上传 {MAX_IMAGES} 张图片"})
        contents = []
        for img in images:
            if img.content_type not in ALLOWED_IMAGE_TYPES:
                raise HTTPException(415, detail={"error": "unsupported_format", "detail": f"不支持的图片格式: {img.content_type}"})
            data = await img.read()
            if len(data) > MAX_IMAGE_SIZE:
                raise HTTPException(413, detail={"error": "file_too_large", "detail": "单张图片不超过 10MB"})
            contents.append(data)
        return ("image", b"||IMG_SEP||".join(contents), locale)

    if text is not None and text.strip():
        if len(text) > MAX_TEXT_LENGTH:
            raise HTTPException(413, detail={"error": "text_too_long", "detail": f"文本不超过 {MAX_TEXT_LENGTH} 字符"})
        return ("text", text.encode("utf-8"), locale)

    if file is not None:
        filename = file.filename or ""
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_FILE_EXTS:
            raise HTTPException(415, detail={"error": "unsupported_format", "detail": f"不支持的文件格式: {ext}"})
        data = await file.read()
        if len(data) > MAX_FILE_SIZE:
            raise HTTPException(413, detail={"error": "file_too_large", "detail": "文件不超过 5MB"})
        return ("file", data, locale)

    raise HTTPException(400, detail={"error": "empty_input", "detail": "请提供有效的聊天内容"})


def hash_content(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
```

- [ ] **Step 3: Run tests**

Run: `cd backend && python -m pytest tests/test_validation.py -v`
Expected: PASS (all 9 tests)

- [ ] **Step 4: Commit**

```bash
git add backend/validation.py backend/tests/test_validation.py
git commit -m "feat: add input validation with error mapping"
```

---

### Task 4: DeepSeek analyzer service

**Files:**
- Create: `backend/services/__init__.py`
- Create: `backend/services/analyzer.py`
- Create: `backend/tests/test_analyzer.py`

**Interfaces:**
- Consumes: `settings` from config.py
- Produces: `AnalysisResult` TypedDict, `analyze_chat(input_type, content_bytes, locale) -> AnalysisResult`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_analyzer.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from services.analyzer import analyze_chat, SYSTEM_PROMPT

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
```

Run: `cd backend && python -m pytest tests/test_analyzer.py -v`
Expected: FAIL (module not found)

- [ ] **Step 2: Install openai, write analyzer.py**

```bash
cd backend && pip install openai && echo "openai>=1.50.0" >> requirements.txt
```

Create `backend/services/analyzer.py`:

```python
import json
from openai import AsyncOpenAI
from config import settings

client = AsyncOpenAI(
    api_key=settings.deepseek_api_key,
    base_url=settings.deepseek_base_url,
)

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
        image_parts = content_bytes.split(b"||IMG_SEP||")
        image_contents = []
        for part in image_parts:
            import base64
            b64 = base64.b64encode(part).decode("utf-8")
            image_contents.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"}
            })
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                *image_contents,
                {"type": "text", "text": "请分析以上聊天截图中的对话内容，按 JSON 格式输出分析报告。"}
            ]}
        ]
    else:
        text = content_bytes.decode("utf-8")
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ]

    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.7,
        max_tokens=4096,
        timeout=55.0,
    )

    content = response.choices[0].message.content
    result = json.loads(content)

    # Validate required fields
    required_dims = ["sincerity", "engagement", "respect", "manipulation", "communication", "red_flags"]
    for dim in required_dims:
        if dim not in result.get("radar", {}):
            result.setdefault("radar", {})[dim] = {"score": 0, "label": dim}

    result.setdefault("cards", [])
    result.setdefault("overall", "")

    return result
```

- [ ] **Step 3: Run tests**

Run: `cd backend && python -m pytest tests/test_analyzer.py -v`
Expected: PASS (2 tests)

- [ ] **Step 4: Commit**

```bash
git add backend/services/ backend/tests/test_analyzer.py backend/requirements.txt
git commit -m "feat: add DeepSeek analyzer service with system prompt"
```

---

### Task 5: Analyze endpoint (POST /api/analyze)

**Files:**
- Create: `backend/routers/__init__.py`
- Create: `backend/routers/analyze.py`
- Create: `backend/tests/test_analyze_endpoint.py`

**Interfaces:**
- Consumes: `validate_analyze_request` from validation.py, `analyze_chat` from services/analyzer.py, `get_db` from database.py, `Report` model, `hash_content` from validation.py
- Produces: FastAPI router with `POST /api/analyze`

- [ ] **Step 1: Write failing endpoint tests**

Create `backend/tests/test_analyze_endpoint.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from main import app
from database import Base, engine, init_db
import models.report  # noqa: ensure model registered

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
```

Run: `cd backend && python -m pytest tests/test_analyze_endpoint.py -v`
Expected: FAIL (module not found, or import errors)

- [ ] **Step 2: Register router in main.py**

Edit `backend/main.py` — add after app creation and before health endpoint:

```python
from routers.analyze import router as analyze_router
app.include_router(analyze_router)
```

- [ ] **Step 3: Write routers/analyze.py**

```python
import nanoid
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.report import Report
from validation import validate_analyze_request, hash_content
from services.analyzer import analyze_chat
from config import settings

router = APIRouter(prefix="/api")


@router.post("/analyze", status_code=201)
async def analyze(
    request: Request,
    images: list[UploadFile] | None = File(None),
    text: str | None = Form(None),
    file: UploadFile | None = File(None),
    locale: str = Form("zh-CN"),
    db: AsyncSession = Depends(get_db),
):
    input_type, content_bytes, locale = await validate_analyze_request(images, text, file, locale)

    # Dedup for text and file inputs
    existing = None
    if input_type in ("text", "file"):
        h = hash_content(content_bytes)
        result = await db.execute(select(Report).where(Report.input_hash == h))
        existing = result.scalar_one_or_none()

    if existing:
        report_data = _report_to_response(existing)
        return report_data

    # Call AI
    try:
        analysis = await analyze_chat(input_type, content_bytes, locale)
    except Exception as e:
        raise HTTPException(502, detail={"error": "ai_service_error", "detail": "分析服务暂时不可用"})

    # Store
    input_hash = hash_content(content_bytes) if input_type in ("text", "file") else None
    report = Report(
        input_type=input_type,
        input_hash=input_hash,
        locale=locale,
        score_sincerity=analysis["radar"]["sincerity"]["score"],
        score_engagement=analysis["radar"]["engagement"]["score"],
        score_respect=analysis["radar"]["respect"]["score"],
        score_manipulation=analysis["radar"]["manipulation"]["score"],
        score_communication=analysis["radar"]["communication"]["score"],
        score_red_flags=analysis["radar"]["red_flags"]["score"],
        cards=analysis["cards"],
        overall=analysis["overall"],
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return _report_to_response(report)


def _report_to_response(report: Report) -> dict:
    return {
        "report_id": report.id,
        "share_url": f"{settings.share_domain}/report/{report.id}",
        "created_at": report.created_at.isoformat(),
        "expires_at": report.expires_at.isoformat(),
        "radar": {
            "sincerity":      {"score": report.score_sincerity, "label": "真诚度"},
            "engagement":     {"score": report.score_engagement, "label": "投入程度"},
            "respect":        {"score": report.score_respect, "label": "尊重程度"},
            "manipulation":   {"score": report.score_manipulation, "label": "操纵倾向"},
            "communication":  {"score": report.score_communication, "label": "沟通健康度"},
            "red_flags":      {"score": report.score_red_flags, "label": "红旗指数"},
        },
        "cards": report.cards,
        "overall": report.overall,
    }
```

- [ ] **Step 4: Run endpoint tests**

Run: `cd backend && python -m pytest tests/test_analyze_endpoint.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/routers/ backend/main.py backend/tests/test_analyze_endpoint.py
git commit -m "feat: add POST /api/analyze endpoint with dedup and AI integration"
```

---

### Task 6: Report retrieval endpoint

**Files:**
- Create: `backend/routers/report.py`
- Create: `backend/tests/test_report_endpoint.py`

**Interfaces:**
- Consumes: `get_db`, `Report` model
- Produces: FastAPI router with `GET /api/report/{report_id}`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_report_endpoint.py`:

```python
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
```

Run: `cd backend && python -m pytest tests/test_report_endpoint.py -v`
Expected: FAIL (module not found)

- [ ] **Step 2: Write routers/report.py**

```python
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.report import Report

router = APIRouter(prefix="/api")


@router.get("/report/{report_id}")
async def get_report(report_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()

    if report is None:
        raise HTTPException(404, detail={"error": "not_found", "detail": "报告不存在"})

    if report.expires_at < datetime.now(timezone.utc):
        raise HTTPException(410, detail={"error": "report_expired", "detail": "报告已过期"})

    return JSONResponse(
        content={
            "report_id": report.id,
            "created_at": report.created_at.isoformat(),
            "expires_at": report.expires_at.isoformat(),
            "radar": {
                "sincerity":      {"score": report.score_sincerity, "label": "真诚度"},
                "engagement":     {"score": report.score_engagement, "label": "投入程度"},
                "respect":        {"score": report.score_respect, "label": "尊重程度"},
                "manipulation":   {"score": report.score_manipulation, "label": "操纵倾向"},
                "communication":  {"score": report.score_communication, "label": "沟通健康度"},
                "red_flags":      {"score": report.score_red_flags, "label": "红旗指数"},
            },
            "cards": report.cards,
            "overall": report.overall,
        },
        headers={"Cache-Control": "public, max-age=3600"},
    )
```

- [ ] **Step 3: Register router in main.py**

Edit `backend/main.py` — add:

```python
from routers.report import router as report_router
app.include_router(report_router)
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_report_endpoint.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/routers/report.py backend/main.py backend/tests/test_report_endpoint.py
git commit -m "feat: add GET /api/report/{id} with 404/410 handling"
```

---

### Task 7: Rate limiting

**Files:**
- Create: `backend/middleware.py`
- Create: `backend/tests/test_rate_limit.py`

**Interfaces:**
- Consumes: `settings.rate_limit_per_hour`
- Produces: `RateLimitMiddleware` class (or dependency)

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_rate_limit.py`:

```python
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from main import app

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

@pytest.fixture
async def client():
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_rate_limit_returns_429_after_exceeded(client: AsyncClient):
    with patch("routers.analyze.analyze_chat", new=AsyncMock(return_value=MOCK_ANALYSIS)):
        # Send 11 requests (limit is 10/hour)
        for i in range(11):
            response = await client.post("/api/analyze", data={"text": f"test {i}"})
        last = response

    assert last.status_code == 429
    assert last.json()["error"] == "rate_limited"
```

Run: `cd backend && python -m pytest tests/test_rate_limit.py -v`
Expected: FAIL (no rate limiting in place — all 201s or last would be 201)

- [ ] **Step 2: Write middleware.py**

```python
import time
from collections import defaultdict
from fastapi import Request, HTTPException
from config import settings

_window_requests: dict[str, list[float]] = defaultdict(list)

async def rate_limit_dependency(request: Request):
    """FastAPI dependency for rate limiting by client IP."""
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - 3600  # 1 hour

    # Remove old entries
    _window_requests[ip] = [t for t in _window_requests[ip] if t > window_start]

    if len(_window_requests[ip]) >= settings.rate_limit_per_hour:
        raise HTTPException(
            429,
            detail={"error": "rate_limited", "retry_after": 3600},
        )

    _window_requests[ip].append(now)
```

- [ ] **Step 3: Apply rate limit to analyze endpoint**

In `backend/routers/analyze.py`, add import:

```python
from middleware import rate_limit_dependency
```

And add the dependency to the analyze function signature:

```python
async def analyze(
    request: Request,
    images: list[UploadFile] | None = File(None),
    text: str | None = Form(None),
    file: UploadFile | None = File(None),
    locale: str = Form("zh-CN"),
    db: AsyncSession = Depends(get_db),
    _rate_check=Depends(rate_limit_dependency),
):
```

- [ ] **Step 4: Run rate limit test**

Run: `cd backend && python -m pytest tests/test_rate_limit.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/middleware.py backend/routers/analyze.py backend/tests/test_rate_limit.py
git commit -m "feat: add in-memory rate limiting (10 req/IP/hour)"
```

---

### Task 8: Cleanup background job

**Files:**
- Create: `backend/services/cleaner.py`
- Create: `backend/tests/test_cleaner.py`

**Interfaces:**
- Consumes: `settings.report_ttl_days`, database session
- Produces: `cleanup_expired_reports()` async function

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_cleaner.py`:

```python
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
```

- [ ] **Step 2: Write services/cleaner.py**

```python
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
```

- [ ] **Step 3: Run tests**

Run: `cd backend && python -m pytest tests/test_cleaner.py -v`
Expected: PASS

- [ ] **Step 4: Wire cleanup into main.py startup**

Edit `backend/main.py`, add to the end:

```python
from contextlib import asynccontextmanager
from services.cleaner import cleanup_expired_reports
import asyncio

async def cleanup_loop():
    while True:
        await asyncio.sleep(86400)  # 24 hours
        try:
            await cleanup_expired_reports()
        except Exception:
            pass

@app.on_event("startup")
async def start_cleanup():
    asyncio.create_task(cleanup_loop())
```

- [ ] **Step 5: Commit**

```bash
git add backend/services/cleaner.py backend/tests/test_cleaner.py backend/main.py
git commit -m "feat: add daily cleanup job for expired reports"
```

---

### Task 9: Frontend scaffolding

**Files:**
- Create: `frontend/` (via `npm create vite`)

**Interfaces:**
- Produces: Working dev server on port 5173, Tailwind CSS configured, React Router set up, proxy to backend

- [ ] **Step 1: Create Vite + React + TypeScript project**

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
```

- [ ] **Step 2: Install dependencies**

```bash
cd frontend
npm install react-router-dom
npm install -D tailwindcss @tailwindcss/vite
```

- [ ] **Step 3: Configure Tailwind**

Edit `frontend/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

Replace `frontend/src/index.css`:

```css
@import "tailwindcss";

@theme {
  --color-primary: #8b7cf0;
  --color-primary-light: #a78bfa;
  --color-primary-dark: #6d5fd4;
  --color-bg: #0f0d1a;
  --color-bg-card: rgba(255, 255, 255, 0.04);
  --color-border: rgba(255, 255, 255, 0.08);
  --color-text: #f0ecfc;
  --color-text-muted: #a497c8;
  --color-accent: #fcd34d;
  --color-danger: #fda4af;
}

body {
  background-color: var(--color-bg);
  color: var(--color-text);
  font-family: system-ui, -apple-system, sans-serif;
}
```

- [ ] **Step 4: Set up React Router**

Replace `frontend/src/App.tsx`:

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import UploadPage from './pages/UploadPage'
import ReportPage from './pages/ReportPage'
import ErrorPage from './pages/ErrorPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/report/:id" element={<ReportPage />} />
        <Route path="/error" element={<ErrorPage />} />
      </Routes>
    </BrowserRouter>
  )
}
```

- [ ] **Step 5: Create page stubs**

Create `frontend/src/pages/HomePage.tsx`:

```tsx
export default function HomePage() {
  return <div className="min-h-svh flex items-center justify-center"><p>HomePage</p></div>
}
```

Create `frontend/src/pages/UploadPage.tsx`, `frontend/src/pages/ReportPage.tsx`, `frontend/src/pages/ErrorPage.tsx` similarly.

- [ ] **Step 6: Verify dev server starts**

Run: `cd frontend && npx vite --host 0.0.0.0`
Expected: Vite dev server starts on port 5173, open browser → see "HomePage"

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold React + Vite + Tailwind + React Router frontend"
```

---

### Task 10: API client and shared types

**Files:**
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/types.ts`

**Interfaces:**
- Produces: `AnalyzeResponse`, `RadarData`, `DimensionCard` types, `api.analyze(data)`, `api.getReport(id)` functions

- [ ] **Step 1: Write types**

Create `frontend/src/lib/types.ts`:

```typescript
export interface RadarScore {
  score: number;
  label: string;
}

export interface RadarData {
  sincerity: RadarScore;
  engagement: RadarScore;
  respect: RadarScore;
  manipulation: RadarScore;
  communication: RadarScore;
  red_flags: RadarScore;
}

export interface EvidenceItem {
  quote: string;
  analysis: string;
}

export interface DimensionCard {
  dimension: string;
  title: string;
  summary: string;
  evidence: EvidenceItem[];
  suggestion: string;
}

export interface AnalyzeResponse {
  report_id: string;
  share_url: string;
  created_at: string;
  expires_at: string;
  radar: RadarData;
  cards: DimensionCard[];
  overall: string;
}

export interface ApiError {
  error: string;
  detail: string;
}
```

- [ ] **Step 2: Write API client**

Create `frontend/src/lib/api.ts`:

```typescript
import type { AnalyzeResponse } from './types';

const BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: 'unknown', detail: 'Unknown error' }));
    throw body;
  }
  return res.json();
}

export async function analyze(formData: FormData): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>('/analyze', {
    method: 'POST',
    body: formData,
  });
}

export async function getReport(id: string): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>(`/report/${id}`);
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/
git commit -m "feat: add API client and TypeScript types"
```

---

### Task 11: Shared UI components

**Files:**
- Create: `frontend/src/components/Header.tsx`
- Create: `frontend/src/components/Footer.tsx`
- Create: `frontend/src/components/Toast.tsx`
- Create: `frontend/src/components/LoadingSpinner.tsx`
- Create: `frontend/src/components/ErrorMessage.tsx`
- Create: `frontend/src/components/CopyButton.tsx`

**Interfaces:**
- Produces: `<Header />`, `<Footer />`, `<Toast message onClose />`, `<LoadingSpinner />`, `<ErrorMessage message />`, `<CopyButton text />`

- [ ] **Step 1: Write all components**

Create `frontend/src/components/Header.tsx`:

```tsx
import { Link } from 'react-router-dom'

export default function Header() {
  return (
    <header className="flex items-center justify-between">
      <Link to="/" className="flex items-center gap-2 text-sm font-medium no-underline text-text">
        <span className="flex h-8 w-8 items-center justify-center rounded-md border border-primary/40 bg-primary/15 text-primary">
          ♡
        </span>
        HeartLens
      </Link>
      <span className="inline-flex items-center rounded-full border border-border bg-bg-card px-2.5 py-1 text-xs text-text-muted">
        专业分析
      </span>
    </header>
  )
}
```

Create `frontend/src/components/Footer.tsx`:

```tsx
export default function Footer() {
  return (
    <footer className="text-center text-xs text-text-muted py-6">
      <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full border border-border bg-bg-card">
        🔒 不保存聊天原文 · 报告 30 天自动过期
      </span>
    </footer>
  )
}
```

Create `frontend/src/components/Toast.tsx`:

```tsx
import { useEffect, useState } from 'react'

export default function Toast({ message, onClose }: { message: string; onClose: () => void }) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    setVisible(true)
    const timer = setTimeout(() => { setVisible(false); setTimeout(onClose, 300) }, 2500)
    return () => clearTimeout(timer)
  }, [onClose])

  return (
    <div className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-50 transition-all duration-300 ${
      visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
    }`}>
      <div className="bg-primary/90 text-white px-4 py-2 rounded-lg text-sm shadow-lg">
        {message}
      </div>
    </div>
  )
}
```

Create `frontend/src/components/LoadingSpinner.tsx`:

```tsx
export default function LoadingSpinner({ text = '加载中...' }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16">
      <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
      <p className="text-sm text-text-muted">{text}</p>
    </div>
  )
}
```

Create `frontend/src/components/ErrorMessage.tsx`:

```tsx
export default function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16">
      <div className="w-12 h-12 rounded-full bg-danger/10 flex items-center justify-center text-2xl">!</div>
      <p className="text-sm text-danger">{message}</p>
    </div>
  )
}
```

Create `frontend/src/components/CopyButton.tsx`:

```tsx
import { useState } from 'react'

export default function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button
      onClick={handleCopy}
      className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-bg-card px-3 py-1.5 text-xs text-text-muted hover:text-text transition"
    >
      {copied ? '已复制 ✓' : '分享报告 🔗'}
    </button>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/
git commit -m "feat: add shared UI components (Header, Footer, Toast, LoadingSpinner, ErrorMessage, CopyButton)"
```

---

### Task 12: HomePage

**Files:**
- Create: `frontend/src/pages/HomePage.tsx` (replace stub)
- Create: `frontend/src/components/RadarScanBg.tsx`
- Create: `frontend/src/components/ParticleBg.tsx`

**Interfaces:**
- Produces: Full homepage with radar scan animation overlay + particle background + hero content

- [ ] **Step 1: Write RadarScanBg component**

Create `frontend/src/components/RadarScanBg.tsx`:

```tsx
export default function RadarScanBg() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {/* Concentric rings */}
      <div className="absolute top-1/2 left-[8%] -translate-y-1/2 w-[300px] h-[300px]">
        <div className="absolute inset-0 rounded-full border border-primary/10" />
        <div className="absolute inset-8 rounded-full border border-primary/8" />
        <div className="absolute inset-16 rounded-full border border-primary/5" />
        {/* Scan arm */}
        <div className="absolute inset-0 rounded-full overflow-hidden">
          <div
            className="absolute top-0 left-1/2 w-1/2 h-full origin-left animate-[spin_4s_linear_infinite]"
            style={{
              background: 'conic-gradient(from 0deg, transparent 0deg, rgba(139,124,240,0.15) 15deg, transparent 30deg)',
            }}
          />
        </div>
        {/* Center dot */}
        <div className="absolute top-1/2 left-1/2 w-2 h-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary shadow-[0_0_16px_#8b7cf0]" />
        {/* Pulse rings */}
        <div className="absolute -inset-4 rounded-full border border-primary/10 animate-[pulse-ring_2s_ease-out_infinite]" />
        <div className="absolute -inset-4 rounded-full border border-primary/8 animate-[pulse-ring_2s_ease-out_0.7s_infinite]" />
        {/* Floating labels */}
        <span className="absolute top-[12%] left-[78%] text-[10px] text-primary-light whitespace-nowrap">真诚度</span>
        <span className="absolute top-[52%] left-[90%] text-[10px] text-primary whitespace-nowrap">投入</span>
        <span className="absolute top-[82%] left-[52%] text-[10px] text-accent whitespace-nowrap">红旗</span>
        <span className="absolute top-[28%] left-[52%] text-[10px] text-primary whitespace-nowrap">尊重</span>
        <span className="absolute top-[62%] left-[20%] text-[10px] text-danger whitespace-nowrap">冷暴力</span>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Add CSS keyframes to index.css**

Append to `frontend/src/index.css`:

```css
@keyframes pulse-ring {
  0% { transform: scale(0.85); opacity: 1; }
  100% { transform: scale(1.15); opacity: 0; }
}
```

- [ ] **Step 3: Write ParticleBg component**

Create `frontend/src/components/ParticleBg.tsx`:

```tsx
import { useEffect, useRef } from 'react'

export default function ParticleBg() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animationId: number
    const particles: { x: number; y: number; r: number; vx: number; vy: number; opacity: number }[] = []

    const resize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }
    resize()
    window.addEventListener('resize', resize)

    for (let i = 0; i < 60; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        r: Math.random() * 2 + 0.5,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        opacity: Math.random() * 0.4 + 0.1,
      })
    }

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      particles.forEach(p => {
        p.x += p.vx
        p.y += p.vy
        if (p.x < 0) p.x = canvas.width
        if (p.x > canvas.width) p.x = 0
        if (p.y < 0) p.y = canvas.height
        if (p.y > canvas.height) p.y = 0
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(167, 139, 250, ${p.opacity})`
        ctx.fill()
      })
      animationId = requestAnimationFrame(animate)
    }
    animate()

    return () => {
      cancelAnimationFrame(animationId)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return <canvas ref={canvasRef} className="pointer-events-none fixed inset-0 z-0" />
}
```

- [ ] **Step 4: Write full HomePage**

Replace `frontend/src/pages/HomePage.tsx`:

```tsx
import { Link } from 'react-router-dom'
import Header from '../components/Header'
import Footer from '../components/Footer'
import RadarScanBg from '../components/RadarScanBg'
import ParticleBg from '../components/ParticleBg'

const DIMS = ['真诚度', '投入程度', '尊重程度', '操纵倾向', '沟通健康度', '红旗指数']

export default function HomePage() {
  return (
    <main className="relative min-h-svh overflow-hidden px-5 py-6">
      <ParticleBg />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-24 bg-primary/10 blur-3xl" />

      <section className="relative z-10 mx-auto flex min-h-[calc(100svh-3rem)] w-full max-w-5xl flex-col justify-between">
        <Header />

        <div className="grid gap-10 pb-8 pt-12 md:grid-cols-[1.05fr_0.95fr] md:items-center">
          <div>
            <div className="mb-5 flex flex-wrap gap-2">
              {DIMS.map(d => (
                <span key={d} className="inline-flex items-center rounded-full border border-primary/20 bg-primary/8 px-2.5 py-1 text-xs text-primary-light">
                  {d}
                </span>
              ))}
            </div>

            <h1 className="text-balance text-6xl font-semibold leading-[0.92] sm:text-7xl md:text-8xl">
              透过聊天<br/>看见真心
            </h1>

            <p className="mt-6 max-w-xl text-pretty text-lg leading-8 text-text-muted">
              基于心理学框架的 AI 关系洞察<br />
              每一个结论，都有对话中的原文依据
            </p>

            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <Link
                to="/upload"
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary hover:bg-primary-dark transition text-white px-6 py-3 text-sm font-medium shadow-[0_0_28px_rgba(139,124,240,0.22)]"
              >
                开始分析
                <span className="text-lg">→</span>
              </Link>
            </div>
          </div>

          <div className="relative mx-auto aspect-square w-full max-w-sm">
            <RadarScanBg />
          </div>
        </div>

        <Footer />
      </section>
    </main>
  )
}
```

- [ ] **Step 5: Remove unused App.css**

```bash
rm frontend/src/App.css
```

Edit `frontend/src/main.tsx` to remove App.css import if present.

- [ ] **Step 6: Verify homepage renders**

Run: `cd frontend && npx vite`
Expected: Open browser → see homepage with radar animation + particles + hero text

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/HomePage.tsx frontend/src/components/RadarScanBg.tsx frontend/src/components/ParticleBg.tsx frontend/src/index.css frontend/src/main.tsx
git commit -m "feat: add HomePage with radar scan animation and particle background"
```

---

### Task 13: UploadPage

**Files:**
- Replace: `frontend/src/pages/UploadPage.tsx`

**Interfaces:**
- Consumes: `api.analyze()` from lib/api, types from lib/types
- Produces: Upload page with 3 input tabs, validation, loading state, navigation to report page

- [ ] **Step 1: Write UploadPage**

```tsx
import { useState, useRef, type FormEvent, type DragEvent, type ChangeEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import Footer from '../components/Footer'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import { analyze } from '../lib/api'

type InputTab = 'image' | 'text' | 'file'

export default function UploadPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState<InputTab>('image')
  const [images, setImages] = useState<File[]>([])
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [progress, setProgress] = useState(0)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const imageInputRef = useRef<HTMLInputElement>(null)

  const handleDrop = (e: DragEvent) => {
    e.preventDefault()
    const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/'))
    setImages(prev => [...prev, ...files].slice(0, 5))
  }

  const handleImageSelect = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setImages(prev => [...prev, ...Array.from(e.target.files!)].slice(0, 5))
    }
  }

  const removeImage = (i: number) => setImages(prev => prev.filter((_, idx) => idx !== i))

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    setProgress(10)

    const fd = new FormData()
    if (tab === 'image') {
      images.forEach(img => fd.append('images', img))
    } else if (tab === 'text') {
      fd.append('text', text)
    } else if (file) {
      fd.append('file', file)
    }
    fd.append('locale', 'zh-CN')

    try {
      setProgress(30)
      const result = await analyze(fd)
      setProgress(90)
      navigate(`/report/${result.report_id}`)
    } catch (err: any) {
      setError(err?.detail || '分析失败，请重试')
    } finally {
      setLoading(false)
      setProgress(0)
    }
  }

  return (
    <main className="relative min-h-svh overflow-hidden px-5 py-6">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-24 bg-primary/10 blur-3xl" />

      <section className="relative z-10 mx-auto min-h-[calc(100svh-3rem)] w-full max-w-2xl flex flex-col">
        <Header />

        <div className="flex-1 py-12">
          <h2 className="text-2xl font-semibold mb-8">开始分析</h2>

          {/* Tabs */}
          <div className="flex border-b border-border mb-6">
            {(['image', 'text', 'file'] as InputTab[]).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-4 py-2 text-sm border-b-2 transition ${
                  tab === t ? 'border-primary text-primary' : 'border-transparent text-text-muted'
                }`}
              >
                {t === 'image' ? '截图上传' : t === 'text' ? '粘贴文本' : '导入文件'}
              </button>
            ))}
          </div>

          {error && <ErrorMessage message={error} />}

          {loading ? (
            <div className="flex flex-col items-center gap-4 py-16">
              <LoadingSpinner text="正在分析中..." />
              <div className="w-full max-w-xs bg-border rounded-full h-2">
                <div className="bg-primary h-2 rounded-full transition-all duration-500" style={{ width: `${progress}%` }} />
              </div>
              <div className="text-xs text-text-muted space-y-1">
                <p className={progress >= 20 ? 'text-primary-light' : ''}>✓ 正在提取对话内容...</p>
                <p className={progress >= 50 ? 'text-primary-light' : ''}>⏳ 正在多维度分析...</p>
                <p className={progress >= 80 ? 'text-primary-light' : ''}>⏳ 正在生成报告...</p>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              {tab === 'image' && (
                <div
                  onDrop={handleDrop}
                  onDragOver={e => e.preventDefault()}
                  className="border-2 border-dashed border-border rounded-xl p-8 text-center hover:border-primary/40 transition cursor-pointer"
                  onClick={() => imageInputRef.current?.click()}
                >
                  <p className="text-3xl mb-2">📷</p>
                  <p className="text-sm text-text-muted mb-1">拖拽或点击上传聊天截图</p>
                  <p className="text-xs text-text-muted">支持 jpg/png/webp，最多 5 张</p>
                  <input ref={imageInputRef} type="file" accept="image/jpeg,image/png,image/webp" multiple hidden onChange={handleImageSelect} />

                  {images.length > 0 && (
                    <div className="flex gap-2 mt-4 flex-wrap justify-center">
                      {images.map((img, i) => (
                        <div key={i} className="relative w-16 h-16 rounded-lg overflow-hidden border border-border">
                          <img src={URL.createObjectURL(img)} alt="" className="w-full h-full object-cover" />
                          <button type="button" onClick={(e) => { e.stopPropagation(); removeImage(i) }}
                            className="absolute top-0 right-0 w-5 h-5 bg-danger text-white text-xs rounded-bl-lg">×</button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {tab === 'text' && (
                <div>
                  <textarea
                    value={text}
                    onChange={e => setText(e.target.value)}
                    placeholder="在此粘贴聊天文本内容..."
                    maxLength={20000}
                    className="w-full h-64 p-4 rounded-xl border border-border bg-bg-card text-text placeholder:text-text-muted/50 resize-none text-sm focus:outline-none focus:border-primary/50"
                  />
                  <p className={`text-xs mt-2 ${text.length > 20000 ? 'text-danger' : 'text-text-muted'}`}>
                    {text.length} / 20000
                  </p>
                </div>
              )}

              {tab === 'file' && (
                <div
                  className="border-2 border-dashed border-border rounded-xl p-8 text-center hover:border-primary/40 transition cursor-pointer"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <p className="text-3xl mb-2">📄</p>
                  <p className="text-sm text-text-muted">点击选择聊天记录文件</p>
                  <p className="text-xs text-text-muted">支持 .txt / .json，最大 5MB</p>
                  <input ref={fileInputRef} type="file" accept=".txt,.json" hidden
                    onChange={e => setFile(e.target.files?.[0] || null)} />
                  {file && (
                    <p className="mt-3 text-sm text-primary-light">{file.name} ✓</p>
                  )}
                </div>
              )}

              <button
                type="submit"
                disabled={
                  (tab === 'image' && images.length === 0) ||
                  (tab === 'text' && !text.trim()) ||
                  (tab === 'file' && !file)
                }
                className="mt-6 w-full inline-flex items-center justify-center gap-2 rounded-lg bg-primary hover:bg-primary-dark disabled:opacity-40 disabled:cursor-not-allowed transition text-white px-6 py-3 text-sm font-medium"
              >
                开始分析 →
              </button>
            </form>
          )}
        </div>

        <Footer />
      </section>
    </main>
  )
}
```

- [ ] **Step 2: Verify upload page works**

Run: `cd frontend && npx vite`
Expected: Click "开始分析" from homepage → navigate to /upload → see 3 tabs → can switch between them

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/UploadPage.tsx
git commit -m "feat: add UploadPage with 3 input modes and loading state"
```

---

### Task 14: RadarChart + DimensionCard components

**Files:**
- Create: `frontend/src/components/RadarChart.tsx`
- Create: `frontend/src/components/DimensionCard.tsx`

**Interfaces:**
- Consumes: `RadarData` type, `DimensionCard` type
- Produces: `<RadarChart data={RadarData} />`, `<DimensionCard card={DimensionCard} />`

- [ ] **Step 1: Write RadarChart component**

Create `frontend/src/components/RadarChart.tsx`:

```tsx
import type { RadarData } from '../lib/types'

const DIMS = [
  { key: 'sincerity' as const, angle: -90, color: '#8b7cf0' },
  { key: 'engagement' as const, angle: -30, color: '#a78bfa' },
  { key: 'respect' as const, angle: 30, color: '#fcd34d' },
  { key: 'manipulation' as const, angle: 90, color: '#fda4af' },
  { key: 'communication' as const, angle: 150, color: '#67e8f9' },
  { key: 'red_flags' as const, angle: 210, color: '#fb7185' },
]

export default function RadarChart({ data }: { data: RadarData }) {
  const size = 280
  const cx = size / 2
  const cy = size / 2
  const maxR = 110

  const toXY = (angleDeg: number, value: number) => {
    const rad = (angleDeg * Math.PI) / 180
    const r = (value / 100) * maxR
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
  }

  const points = DIMS.map(d => toXY(d.angle, data[d.key].score))
  const polygonPoints = points.map(p => `${p.x},${p.y}`).join(' ')

  return (
    <div className="flex justify-center">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Grid rings */}
        {[0.25, 0.5, 0.75, 1].map(scale => (
          <polygon
            key={scale}
            points={DIMS.map(d => {
              const p = toXY(d.angle, scale * 100)
              return `${p.x},${p.y}`
            }).join(' ')}
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth="1"
          />
        ))}
        {/* Axis lines */}
        {DIMS.map(d => {
          const p = toXY(d.angle, 100)
          return <line key={d.key} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
        })}
        {/* Data polygon */}
        <polygon points={polygonPoints} fill="rgba(139,124,240,0.15)" stroke="#8b7cf0" strokeWidth="1.5" />
        {/* Data points */}
        {points.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r="3" fill={DIMS[i].color} />
        ))}
        {/* Labels */}
        {DIMS.map(d => {
          const labelR = maxR + 24
          const rad = (d.angle * Math.PI) / 180
          const lx = cx + labelR * Math.cos(rad)
          const ly = cy + labelR * Math.sin(rad)
          return (
            <text key={d.key} x={lx} y={ly} textAnchor="middle" dominantBaseline="middle"
              fill={d.color} fontSize="11" fontWeight="500" fontFamily="system-ui, sans-serif">
              {data[d.key].label}
            </text>
          )
        })}
        {/* Center score */}
        <text x={cx} y={cy - 4} textAnchor="middle" fill="white" fontSize="14" fontWeight="600" fontFamily="system-ui, sans-serif">
          综合
        </text>
      </svg>
    </div>
  )
}
```

- [ ] **Step 2: Write DimensionCard component**

Create `frontend/src/components/DimensionCard.tsx`:

```tsx
import type { DimensionCard as DC } from '../lib/types'

const DIM_COLORS: Record<string, string> = {
  sincerity: '#8b7cf0',
  engagement: '#a78bfa',
  respect: '#fcd34d',
  manipulation: '#fda4af',
  communication: '#67e8f9',
  red_flags: '#fb7185',
}

export default function DimensionCard({ card }: { card: DC }) {
  const color = DIM_COLORS[card.dimension] || '#8b7cf0'

  return (
    <div className="rounded-xl border border-border bg-bg-card p-5">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs px-2 py-0.5 rounded-full" style={{ backgroundColor: color + '20', color }}>
          {card.title.split('：')[0]}
        </span>
      </div>
      <h3 className="text-base font-semibold mb-2">{card.title}</h3>
      <p className="text-sm text-text-muted leading-relaxed mb-3">{card.summary}</p>

      {card.evidence.map((ev, i) => (
        <div key={i} className="mb-2 pl-3 border-l-2" style={{ borderColor: color + '60' }}>
          <p className="text-sm text-text italic">"{ev.quote}"</p>
          <p className="text-xs text-text-muted mt-0.5">↗ {ev.analysis}</p>
        </div>
      ))}

      <div className="mt-3 pt-3 border-t border-border">
        <p className="text-xs text-text-muted leading-relaxed">
          <span className="font-medium text-text">💡 </span>
          {card.suggestion}
        </p>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/RadarChart.tsx frontend/src/components/DimensionCard.tsx
git commit -m "feat: add RadarChart SVG and DimensionCard components"
```

---

### Task 15: ReportPage + ErrorPage

**Files:**
- Replace: `frontend/src/pages/ReportPage.tsx`
- Replace: `frontend/src/pages/ErrorPage.tsx`

**Interfaces:**
- Consumes: `api.getReport()` from lib/api, `RadarChart`, `DimensionCard`, shared components
- Produces: Report display page and error page

- [ ] **Step 1: Write ReportPage**

Replace `frontend/src/pages/ReportPage.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import Header from '../components/Header'
import Footer from '../components/Footer'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import CopyButton from '../components/CopyButton'
import Toast from '../components/Toast'
import RadarChart from '../components/RadarChart'
import DimensionCard from '../components/DimensionCard'
import { getReport } from '../lib/api'
import type { AnalyzeResponse } from '../lib/types'

export default function ReportPage() {
  const { id } = useParams<{ id: string }>()
  const [report, setReport] = useState<AnalyzeResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [toast, setToast] = useState('')

  useEffect(() => {
    if (!id) return
    getReport(id)
      .then(setReport)
      .catch(err => setError(err?.detail || '加载报告失败'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <main className="min-h-svh px-5 py-6"><LoadingSpinner text="加载报告中..." /></main>
  if (error) return <main className="min-h-svh px-5 py-6"><ErrorMessage message={error} /></main>
  if (!report) return null

  const shareUrl = `${window.location.origin}/report/${report.report_id}`

  return (
    <main className="relative min-h-svh overflow-hidden px-5 py-6">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-24 bg-primary/10 blur-3xl" />

      <section className="relative z-10 mx-auto min-h-[calc(100svh-3rem)] w-full max-w-2xl flex flex-col">
        <div className="flex items-center justify-between mb-8">
          <Link to="/" className="text-sm text-text-muted hover:text-text transition">← 重新分析</Link>
          <CopyButton text={shareUrl} />
        </div>

        <Header />

        <div className="flex-1 py-8 space-y-6">
          {/* Radar chart */}
          <RadarChart data={report.radar} />

          {/* Overall assessment */}
          <div className="rounded-xl border border-border bg-bg-card p-5">
            <h3 className="text-sm font-semibold mb-2">综合评估</h3>
            <p className="text-sm text-text-muted leading-relaxed">{report.overall}</p>
          </div>

          {/* Dimension cards */}
          {report.cards.map((card, i) => (
            <DimensionCard key={card.dimension || i} card={card} />
          ))}
        </div>

        <Footer />
      </section>

      {toast && <Toast message={toast} onClose={() => setToast('')} />}
    </main>
  )
}
```

- [ ] **Step 2: Write ErrorPage**

Replace `frontend/src/pages/ErrorPage.tsx`:

```tsx
import { Link } from 'react-router-dom'
import Header from '../components/Header'

export default function ErrorPage() {
  return (
    <main className="min-h-svh px-5 py-6">
      <section className="mx-auto max-w-2xl">
        <Header />
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <p className="text-5xl">😕</p>
          <h2 className="text-xl font-semibold">页面出错了</h2>
          <p className="text-sm text-text-muted">请返回首页重试</p>
          <Link to="/" className="inline-flex items-center gap-2 rounded-lg bg-primary hover:bg-primary-dark transition text-white px-5 py-2 text-sm">
            返回首页
          </Link>
        </div>
      </section>
    </main>
  )
}
```

- [ ] **Step 3: Verify full flow**

Start backend: `cd backend && uvicorn main:app --reload --port 8000`
Start frontend: `cd frontend && npx vite`

Test: Homepage → Upload → submit text → see loading → navigate to report → see radar + cards

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/ReportPage.tsx frontend/src/pages/ErrorPage.tsx
git commit -m "feat: add ReportPage with radar chart and dimension cards, ErrorPage"
```

---

### Task 16: Final integration and cleanup

**Files:**
- Create: `.gitignore`
- Create: `backend/.env.example`
- Modify: `backend/database.py` — fix Report model's `expires_at` default
- Read: all files for unused imports, dead code

**Interfaces:** None new — this task ties up loose ends.

- [ ] **Step 1: Fix expires_at default in model**

The SQLAlchemy `server_default` with `timedelta` doesn't work correctly as written. In `backend/models/report.py`, change:

```python
from datetime import datetime, timedelta, timezone

# Replace:
# expires_at: Mapped[datetime] = mapped_column(
#     DateTime(timezone=True),
#     server_default=func.now() + timedelta(days=30),
# )

# With:
expires_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    default=lambda: datetime.now(timezone.utc) + timedelta(days=30),
)
```

- [ ] **Step 2: Create .env.example**

```bash
DEEPSEEK_API_KEY=your-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/heartlens
REPORT_TTL_DAYS=30
RATE_LIMIT_PER_HOUR=10
CORS_ORIGINS=http://localhost:5173
SHARE_DOMAIN=http://localhost:5173
```

- [ ] **Step 3: Create .gitignore**

```gitignore
node_modules/
dist/
.env
__pycache__/
*.pyc
.venv/
.pytest_cache/
.superpowers/
```

- [ ] **Step 4: Create database**

```sql
CREATE DATABASE heartlens;
```

- [ ] **Step 5: Full integration test**

Start PostgreSQL, backend, and frontend. Go through: Homepage → Upload text → Analyze → View report → Share link → Open share link in new tab.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: final integration, .gitignore, .env.example, fix expires_at default"
```
