"""SQLAlchemy ORM models for the MMM Platform persistence layer.

Uses plain strings for status fields (no Python enums) for SQLite
compatibility. RLS is not applied here -- when using Supabase Postgres
with DATABASE_URL, row-level security is managed by Supabase itself.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
class Client(Base):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )


# ---------------------------------------------------------------------------
# ModelJob
# ---------------------------------------------------------------------------
class ModelJob(Base):
    __tablename__ = "model_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), index=True)
    client_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )
    model_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        String(20), default="queued", index=True
    )
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    r2: Mapped[float | None] = mapped_column(Float, nullable=True)
    mape: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )


# ---------------------------------------------------------------------------
# ChannelResult
# ---------------------------------------------------------------------------
class ChannelResult(Base):
    __tablename__ = "channel_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("model_jobs.id", ondelete="CASCADE"), index=True
    )
    channel: Mapped[str] = mapped_column(String(120))
    contribution: Mapped[float] = mapped_column(Float)
    share: Mapped[float] = mapped_column(Float)
    roas: Mapped[float] = mapped_column(Float)
    spend: Mapped[float] = mapped_column(Float)


# ---------------------------------------------------------------------------
# DataSource
# ---------------------------------------------------------------------------
class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="CASCADE"), index=True
    )
    source_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="idle")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
