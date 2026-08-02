"""FastAPI application for the MMM Platform API."""
from __future__ import annotations
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mmm.config import get_settings
from mmm.db.session import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    await init_db()
    yield

app = FastAPI(title="MMM Platform API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from mmm.api.routers import clients, models
app.include_router(clients.router, prefix="/api/v1")
app.include_router(models.router, prefix="/api/v1")

@app.get("/api/v1/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}
from mmm.api.routers import reports
app.include_router(reports.router, prefix="/api/v1")
