from __future__ import annotations

from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from time import time
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .db import init_db, SessionLocal
from .data.companies import DEFAULT_COMPANIES
from .models import Company
from .scheduler.jobs import start_scheduler
from .config import settings
from .logging import configure_logging
from .routers import jobs, search, export, companies, health, stats, metrics
from .services.ollama import ensure_ollama_running
from .metrics import REQUEST_COUNT, REQUEST_LATENCY, REQUEST_IN_PROGRESS
from starlette.middleware.base import BaseHTTPMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _seed_companies()
    await ensure_ollama_running()
    scheduler = None
    if not settings.DISABLE_SCHEDULER:
        scheduler = start_scheduler()
    yield
    if scheduler:
        scheduler.shutdown()


class RateLimitMiddleware:
    """Simple in-memory sliding window rate limiter.

    Note: For production with multiple instances, use Redis-based rate limiting.
    This in-memory solution works for single-instance deployment.
    """

    def __init__(self, app, requests_per_minute: int = 60):
        self.app = app
        self.requests_per_minute = requests_per_minute
        self.requests: dict[str, list[float]] = defaultdict(list)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        client_ip = scope.get("client", ("unknown",))[0]
        now = time()
        window_start = now - 60

        # Clean old requests outside the sliding window
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if t > window_start
        ]

        if len(self.requests[client_ip]) >= self.requests_per_minute:
            response = JSONResponse(
                status_code=429, content={"detail": "Rate limit exceeded"}
            )
            await response(scope, receive, send)
            return

        self.requests[client_ip].append(now)
        await self.app(scope, receive, send)


app = FastAPI(title="Auros", lifespan=lifespan)
configure_logging()

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        method = request.method
        REQUEST_IN_PROGRESS.inc()
        start = time()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            path = _get_route_path(request.scope)
            duration = max(time() - start, 0)
            REQUEST_COUNT.labels(method, path, str(status_code)).inc()
            REQUEST_LATENCY.labels(method, path).observe(duration)
            REQUEST_IN_PROGRESS.dec()


def _get_route_path(scope) -> str:
    route = scope.get("route")
    if route and hasattr(route, "path"):
        return route.path
    return scope.get("path", "unknown")


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.API_RATE_LIMIT_PER_MINUTE)
app.add_middleware(MetricsMiddleware)

app.include_router(jobs.router)
app.include_router(search.router)
app.include_router(export.router)
app.include_router(companies.router)
app.include_router(health.router)
app.include_router(stats.router)
app.include_router(metrics.router)

UI_DIST = Path(__file__).resolve().parents[1] / "ui" / "dist"
INDEX_FILE = UI_DIST / "index.html"

if UI_DIST.exists():
    assets_dir = UI_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/")
async def root():
    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE)
    return JSONResponse(
        {
            "service": "Auros API",
            "docs": "/docs",
            "health": "/health",
            "ui_hint": "Run the UI with `cd ui && npm install && npm run dev` (default http://localhost:5173)",
        }
    )


@app.get("/api")
async def api_root():
    return {
        "service": "Auros API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE)
    raise HTTPException(status_code=404, detail="Not Found")


async def _seed_companies() -> None:
    async with SessionLocal() as session:
        existing = (await session.execute(select(Company))).scalars().all()
        if existing:
            return
        for seed in DEFAULT_COMPANIES:
            session.add(
                Company(
                    id=seed.id,
                    name=seed.name,
                    careers_url=seed.careers_url,
                    tier=seed.tier,
                    enabled=seed.enabled,
                )
            )
        await session.commit()
