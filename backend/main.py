import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from config import settings
from routers.analyze import router as analyze_router
from routers.report import router as report_router
from services.cleaner import cleanup_expired_reports

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(cleanup_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="HeartLens API", version="0.1.0", lifespan=lifespan)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

app.include_router(analyze_router)
app.include_router(report_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def cleanup_loop():
    try:
        await cleanup_expired_reports()
    except Exception:
        logger.exception("Cleanup job failed")
    while True:
        await asyncio.sleep(86400)  # 24 hours
        try:
            await cleanup_expired_reports()
        except Exception:
            logger.exception("Cleanup job failed")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
