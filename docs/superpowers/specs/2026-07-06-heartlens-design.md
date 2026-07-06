# HeartLens Design Spec

## Overview

HeartLens is a free, login-free web app that analyzes chat conversations using AI to generate a psychology-framed relationship risk report. Users upload chat screenshots, paste text, or import chat export files. DeepSeek API performs the analysis and returns structured results displayed as an interactive radar chart and dimension cards.

### Elevator pitch

> 透过聊天，看见真心 — AI 驱动的恋爱关系深度分析，每个结论都有原文依据。

## Product

| Aspect | Decision |
|--------|----------|
| Name | HeartLens |
| Positioning | More professional/trustworthy than Love Radar, psychology-grounded |
| Input modes | Screenshots (up to 5), paste text (max 20k chars), file upload (.txt/.json, max 5MB) |
| Output | 6-dimension radar + 6 cards with scores, evidence quotes, and suggestions |
| AI | DeepSeek Chat/vision API with JSON structured output |
| Monetization | Free, no login required |
| Sharing | Shareable report link, 30-day auto-expiry |
| Visual style | Dark theme + CSS radar scan animation + @shabon/fx particle background |

## Architecture

```
React SPA (Vite)  →  FastAPI  →  DeepSeek API
                        ↕
                   PostgreSQL
```

### Data flow

1. User submits input (images/text/file) → `POST /api/analyze`
2. Backend validates input format, size, count
3. For text and file inputs: backend hashes content (SHA256), checks `input_hash` for dedup, returns existing report if found
4. Backend calls DeepSeek API: images sent as multiple `image_url` content blocks in a single Vision request; text sent as a single user message
5. DeepSeek returns structured JSON (radar scores + card array + overall assessment)
6. Backend stores to PostgreSQL (scores as columns, cards as JSONB), generates nanoid
7. Returns full report + share_url to frontend
8. `GET /api/report/:id` serves stored reports publicly
9. Daily cleanup job deletes reports older than 30 days

Note: Dedup via `input_hash` only applies to text and file inputs. Image dedup is skipped — image re-encoding variations make hashing unreliable.

## Tech Stack

| Layer | Choice |
|-------|--------|
| Frontend | React 18 + Vite + React Router v6 + Tailwind CSS |
| Backend | Python 3.12+ + FastAPI + Uvicorn |
| Database | PostgreSQL 16+ |
| AI | DeepSeek API (chat + vision) |
| Visual effects | @shabon/fx (particle background) + CSS conic-gradient radar scan |
| Testing | pytest (backend) + Vitest (frontend) |
| Deployment | TBD after code complete |

Frontend key dependencies: `react`, `react-dom`, `react-router-dom`, `@shabon/fx` (peer: `three`, `@react-three/fiber`, `@react-three/drei`), `tailwindcss`.

Backend key dependencies: `fastapi`, `uvicorn`, `sqlalchemy`, `asyncpg`, `httpx`, `python-multipart`.

### Project structure

```
/backend
  main.py              # FastAPI app entry
  config.py            # env vars, settings
  routers/
    analyze.py         # POST /api/analyze, GET /api/analyze/status/{id}
    report.py          # GET /api/report/{id}
  services/
    analyzer.py        # DeepSeek API call
    cleaner.py         # periodic cleanup job
  models/
    report.py          # SQLAlchemy model
  tests/
    ...

/frontend
  src/
    pages/
      HomePage.tsx
      UploadPage.tsx
      ReportPage.tsx
      ErrorPage.tsx
    components/
      RadarChart.tsx
      DimensionCard.tsx
      ...
    lib/
      api.ts           # fetch wrapper
    __tests__/
      ...
  vite.config.ts       # proxy /api → backend in dev
```

### Environment variables

| Variable | Purpose |
|----------|---------|
| `DEEPSEEK_API_KEY` | DeepSeek API key |
| `DEEPSEEK_BASE_URL` | API base URL (default: `https://api.deepseek.com`) |
| `DATABASE_URL` | PostgreSQL connection string |
| `REPORT_TTL_DAYS` | Auto-expiry days (default: 30) |
| `RATE_LIMIT_PER_HOUR` | Max requests per IP per hour (default: 10) |
| `CORS_ORIGINS` | Allowed origins (default: `http://localhost:5173`) |

### CORS

FastAPI configured with `CORSMiddleware`, origins from `CORS_ORIGINS` env var. In production, set to the frontend domain.

### SPA routing

Vite dev server proxies `/api/*` to FastAPI. All other routes fall back to `index.html` for SPA client-side routing. In production, Nginx or similar handles this.

## API Design

### `POST /api/analyze`

```
Content-Type: multipart/form-data

Fields (mutually exclusive, one of):
  images[] : file[] — up to 5 images, ≤10MB each, jpg/png/webp
  text     : string — max 20,000 characters
  file     : file   — chat export, ≤5MB, .txt/.json

Optional:
  locale   : string — "zh-CN" | "zh-TW" | "en", default "zh-CN"
```

Response 201:

```json
{
  "report_id": "abc123def",
  "share_url": "https://{domain}/report/abc123def",
  "created_at": "2026-07-06T12:00:00Z",
  "expires_at": "2026-08-05T12:00:00Z",
  "radar": {
    "sincerity":      { "score": 72, "label": "真诚度" },
    "engagement":     { "score": 45, "label": "投入程度" },
    "respect":        { "score": 80, "label": "尊重程度" },
    "manipulation":   { "score": 18, "label": "操纵倾向" },
    "communication":  { "score": 60, "label": "沟通健康度" },
    "red_flags":      { "score": 22, "label": "红旗指数" }
  },
  "cards": [
    {
      "dimension": "sincerity",
      "title": "真诚度：较高 (72)",
      "summary": "对方在对话中表现出较高的自我表露...",
      "evidence": [
        { "quote": "其实我最近也在想这个问题...", "analysis": "主动分享内心想法" }
      ],
      "suggestion": "真诚度较高的对象值得进一步了解..."
    }
  ],
  "overall": "从整体对话来看..."
}
```

### `GET /api/report/{report_id}`

Returns same JSON as above (without `share_url`). Cache: `public, max-age=3600`.

### Timeout handling

- Server timeout: 60s
- If no response by 55s → return `202` + `task_id`, frontend polls `GET /api/analyze/status/{task_id}`

### Rate limiting

- 10 requests per IP per hour
- Exceeded → `429 { "error": "rate_limited", "retry_after": 3600 }`

### Error responses

| Status | Error key | Scenario |
|--------|-----------|----------|
| 400 | `empty_input` | No input provided |
| 400 | `ambiguous_input` | Multiple input types provided |
| 413 | `file_too_large` | Image >10MB or file >5MB |
| 413 | `text_too_long` | Text >20,000 chars |
| 415 | `unsupported_format` | File format not supported |
| 429 | `rate_limited` | Rate limit exceeded |
| 502 | `ai_service_error` | DeepSeek unavailable |
| 504 | `ai_service_timeout` | Analysis timed out |
| 410 | `report_expired` | Requested report has passed its 30-day expiry |
| 404 | `not_found` | Report ID does not exist |

## Data Model

```sql
CREATE TABLE reports (
    id            VARCHAR(12) PRIMARY KEY,        -- nanoid
    input_type    VARCHAR(10) NOT NULL,            -- 'image' | 'text' | 'file'
    input_hash    VARCHAR(64),                     -- SHA256 for dedup
    locale        VARCHAR(10) NOT NULL DEFAULT 'zh-CN',

    score_sincerity       SMALLINT NOT NULL,
    score_engagement      SMALLINT NOT NULL,
    score_respect         SMALLINT NOT NULL,
    score_manipulation    SMALLINT NOT NULL,
    score_communication   SMALLINT NOT NULL,
    score_red_flags       SMALLINT NOT NULL,

    cards         JSONB NOT NULL,
    overall       TEXT NOT NULL,

    client_ip     INET,
    user_agent    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at    TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '30 days')
);

CREATE INDEX idx_reports_created_at ON reports(created_at);
CREATE INDEX idx_reports_expires_at ON reports(expires_at);
CREATE INDEX idx_reports_input_hash  ON reports(input_hash);
```

- Original chat content is NOT stored — only `evidence.quote` snippets in the JSONB cards
- Scores are separate columns for future statistical analysis
- `input_hash` enables idempotent re-uploads

## Frontend Design

### Routes

```
/             → Homepage (brand + CTA)
/upload       → Upload page (3 input mode tabs)
/report/:id   → Report display (radar + cards + share)
/error        → Generic error page
```

### Homepage

- Header: Logo + brand name + "专业分析" badge
- Hero: headline "透过聊天，看见真心" + subtitle + CTA button
- Background: @shabon/fx particle field (GalaxySpiral or ParticleField) + CSS radar scan animation overlay
- Dimension tags below CTA
- Footer: privacy statement + 30-day expiry notice

### Upload page

- Tab bar: [截图上传] [粘贴文本] [导入文件]
- Image tab: drag-and-drop zone, thumbnails with delete, max 5
- Text tab: textarea with character count (max 20,000)
- File tab: single file picker (.txt/.json)
- Locale selector dropdown
- "开始分析" button with loading state
- Client-side validation: file type, size, count

### Analysis waiting state

- Progress indicator with step list:
  - "正在提取对话内容..." ✓
  - "正在分析真诚度..." ⏳
  - "正在生成报告..."
- Inline on upload page (no page navigation)

### Report page

- Header: back button + "分享报告" button
- Radar chart: SVG polygon with 6 axes, center score label
- Overall assessment card
- 6 dimension cards (scrollable):
  - Score bar + title
  - Summary paragraph
  - Evidence quotes with analysis annotations
  - Suggestion paragraph
- Footer: creation date + expiry notice

### Component tree

```
App
├── HomePage
│   ├── Header
│   ├── HeroSection
│   ├── DimensionTags
│   └── Footer
├── UploadPage
│   ├── InputTabs
│   ├── ImageUploader
│   ├── TextPasteArea
│   ├── FileUploader
│   ├── LocaleSelect
│   └── AnalyzeButton
├── ReportPage
│   ├── ReportHeader
│   ├── RadarChart (SVG)
│   ├── OverallAssessment
│   ├── DimensionCard ×6
│   └── ReportFooter
└── Shared
    ├── Toast
    ├── LoadingSpinner
    ├── ErrorMessage
    └── CopyButton
```

### State management

Local `useState` + `useEffect` per page. No global state library needed.

### Share behavior

Click "分享报告" → `navigator.clipboard.writeText(shareUrl)` + Toast "链接已复制".

## AI Prompt Design

### System prompt

```
你是一位资深的心理咨询师和关系分析专家，精通依恋理论、沟通心理学和亲密关系研究。
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
- 严格按 JSON Schema 输出，不输出任何其他内容
- 分析应基于可观察的对话模式，不做人身攻击
- 语气专业但温暖，不制造不必要的焦虑
```

### Output schema

Uses DeepSeek JSON mode (`response_format: { type: "json_object" }`).

```json
{
  "radar": {
    "sincerity":      { "score": 0, "label": "真诚度" },
    "engagement":     { "score": 0, "label": "投入程度" },
    "respect":        { "score": 0, "label": "尊重程度" },
    "manipulation":   { "score": 0, "label": "操纵倾向" },
    "communication":  { "score": 0, "label": "沟通健康度" },
    "red_flags":      { "score": 0, "label": "红旗指数" }
  },
  "cards": [
    {
      "dimension": "string",
      "title": "string",
      "summary": "string",
      "evidence": [
        { "quote": "string", "analysis": "string" }
      ],
      "suggestion": "string"
    }
  ],
  "overall": "string"
}
```

## Testing Strategy

### Backend (pytest)

```
tests/
├── test_analyze.py
├── test_report.py
├── test_validation.py
└── conftest.py
```

Key cases: valid uploads (all 3 modes), empty/ambiguous input, file limits, rate limiting, DeepSeek mock (error/timeout), dedup via input_hash, 404/410 for report retrieval.

### Frontend (Vitest)

```
src/__tests__/
├── UploadPage.test.tsx
├── ReportPage.test.tsx
└── utils.test.ts
```

Key cases: tab switching, file count/type validation, character limit, loading states, successful render, error states, share copy behavior.

### Exclusions

- No E2E tests (MVP)
- No coverage targets
- No load testing pre-launch

## Out of Scope

- User accounts / authentication
- Paid tiers / payments
- Non-Chinese language support (structure supports it, but MVP is zh-CN only)
- Admin dashboard
- Analytics / telemetry
