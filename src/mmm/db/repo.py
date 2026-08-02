"""Async repository functions for SQLAlchemy 2.0 style persistence."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select

from mmm.db.models import ChannelResult, Client, ModelJob
from mmm.db.session import get_session


# ---------------------------------------------------------------------------
# Client CRUD
# ---------------------------------------------------------------------------

async def create_client(
    *,
    client_id: str,
    organization_id: str,
    name: str,
    slug: str,
) -> Client:
    """Insert a new client row."""
    client = Client(
        id=client_id,
        organization_id=organization_id,
        name=name,
        slug=slug,
        created_at=datetime.now(timezone.utc),
    )
    async with get_session() as db:
        db.add(client)
    return client


async def list_clients(organization_id: str) -> list[Client]:
    """Return all clients for an organization, ordered by creation time."""
    stmt = (
        select(Client)
        .where(Client.organization_id == organization_id)
        .order_by(Client.created_at.desc())
    )
    async with get_session() as db:
        result = await db.execute(stmt)
        return list(result.scalars().all())


async def get_client(client_id: str) -> Client | None:
    """Fetch a single client by ID."""
    async with get_session() as db:
        return await db.get(Client, client_id)


async def delete_client(client_id: str) -> bool:
    """Delete a client by ID. Returns True if it existed."""
    async with get_session() as db:
        client = await db.get(Client, client_id)
        if client is None:
            return False
        await db.delete(client)
        return True


# ---------------------------------------------------------------------------
# ModelJob CRUD
# ---------------------------------------------------------------------------

async def create_model_job(
    *,
    job_id: str,
    organization_id: str,
    client_id: str | None,
    model_name: str,
    config_json: str,
    status: str = "queued",
    r2: float | None = None,
    mape: float | None = None,
) -> ModelJob:
    """Insert a new model job row."""
    job = ModelJob(
        id=job_id,
        organization_id=organization_id,
        client_id=client_id,
        model_name=model_name,
        config_json=config_json,
        status=status,
        r2=r2,
        mape=mape,
        created_at=datetime.now(timezone.utc),
    )
    async with get_session() as db:
        db.add(job)
    return job


async def update_model_job(
    job_id: str,
    *,
    status: str | None = None,
    r2: float | None = None,
    mape: float | None = None,
) -> ModelJob | None:
    """Update mutable fields on a model job. Returns updated row or None."""
    updates: dict[str, Any] = {}
    if status is not None:
        updates["status"] = status
    if r2 is not None:
        updates["r2"] = r2
    if mape is not None:
        updates["mape"] = mape
    if not updates:
        return await get_model_job(job_id)

    async with get_session() as db:
        job = await db.get(ModelJob, job_id)
        if job is None:
            return None
        for key, val in updates.items():
            setattr(job, key, val)
    return job


async def list_model_jobs(organization_id: str) -> list[ModelJob]:
    """Return all model jobs for an organization, most recent first."""
    stmt = (
        select(ModelJob)
        .where(ModelJob.organization_id == organization_id)
        .order_by(ModelJob.created_at.desc())
    )
    async with get_session() as db:
        result = await db.execute(stmt)
        return list(result.scalars().all())


async def get_model_job(job_id: str) -> ModelJob | None:
    """Fetch a single model job by ID."""
    async with get_session() as db:
        return await db.get(ModelJob, job_id)


# ---------------------------------------------------------------------------
# ChannelResult
# ---------------------------------------------------------------------------

async def add_channel_results(
    job_id: str,
    results: list[dict[str, Any]],
) -> list[ChannelResult]:
    """Insert channel contribution results for a model job.

    Each dict should have keys: channel, contribution, share, roas, spend.
    """
    rows = [
        ChannelResult(
            model_job_id=job_id,
            channel=r["channel"],
            contribution=r["contribution"],
            share=r["share"],
            roas=r["roas"],
            spend=r["spend"],
        )
        for r in results
    ]
    async with get_session() as db:
        db.add_all(rows)
    return rows


async def get_channel_results(job_id: str) -> list[ChannelResult]:
    """Return channel results for a model job, ordered by contribution descending."""
    stmt = (
        select(ChannelResult)
        .where(ChannelResult.model_job_id == job_id)
        .order_by(ChannelResult.contribution.desc())
    )
    async with get_session() as db:
        result = await db.execute(stmt)
        return list(result.scalars().all())