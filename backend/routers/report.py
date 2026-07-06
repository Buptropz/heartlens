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
