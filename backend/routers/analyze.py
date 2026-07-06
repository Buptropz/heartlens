import logging
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.report import Report
from validation import validate_analyze_request, hash_content
from services.analyzer import analyze_chat
from config import settings
from middleware import rate_limit_dependency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.post("/analyze", status_code=201)
async def analyze(
    request: Request,
    images: list[UploadFile] | None = File(None),
    text: str | None = Form(None),
    file: UploadFile | None = File(None),
    locale: str = Form("zh-CN"),
    db: AsyncSession = Depends(get_db),
    _rate_check=Depends(rate_limit_dependency),
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
        logger.exception("DeepSeek API call failed")
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
