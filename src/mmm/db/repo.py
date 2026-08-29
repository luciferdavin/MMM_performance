"""Async repository functions for SQLAlchemy 2.0 style persistence.

Every read/write is scoped by ``organization_id`` to enforce the multi-tenant
security model at the application layer (the API resolves the caller's org
from the verified JWT before calling these functions).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from mmm.db.models import (
    BudgetOptimization,
    ChannelResult,
    Client,
    DataSource,
    Insight,
    MarketingData,
    Membership,
    ModelJob,
    Organization,
    Report,
    User,
)
from mmm.db.session import get_session


def _now() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------
async def create_organization(*, name: str, slug: str, logo_url: str | None = None) -> Organization:
    org = Organization(id=uuid.uuid4().hex, name=name, slug=slug, logo_url=logo_url)
    async with get_session() as db:
        db.add(org)
    return org


async def get_organization(organization_id: str) -> Organization | None:
    async with get_session() as db:
        return await db.get(Organization, organization_id)


async def get_organization_by_slug(slug: str) -> Organization | None:
    stmt = select(Organization).where(Organization.slug == slug)
    async with get_session() as db:
        result = await db.execute(stmt)
        return result.scalars().first()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
async def create_user(
   *,
    email: str,
    hashed_password: str | None = None,
    full_name: str | None = None,
    user_id: str | None = None,
) -> User:
    user = User(
        id=user_id or uuid.uuid4().hex,
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
    )
    async with get_session() as db:
        db.add(user)
    return user


async def get_user(user_id: str) -> User | None:
    async with get_session() as db:
        return await db.get(User, user_id)


async def get_user_by_email(email: str) -> User | None:
    stmt = select(User).where(User.email == email)
    async with get_session() as db:
        result = await db.execute(stmt)
        return result.scalars().first()


async def list_users(organization_id: str) -> list[User]:
    stmt = (
        select(User)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.organization_id == organization_id)
    )
    async with get_session() as db:
        result = await db.execute(stmt)
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Memberships
# ---------------------------------------------------------------------------
async def create_membership(*, organization_id: str, user_id: str, role: str = "analyst") -> Membership:
    m = Membership(
        id=uuid.uuid4().hex,
        organization_id=organization_id,
        user_id=user_id,
        role=role,
    )
    async with get_session() as db:
        db.add(m)
    return m


async def get_membership(*, organization_id: str, user_id: str) -> Membership | None:
    stmt = select(Membership).where(
        Membership.organization_id == organization_id,
        Membership.user_id == user_id,
    )
    async with get_session() as db:
        result = await db.execute(stmt)
        return result.scalars().first()


async def list_memberships(user_id: str) -> list[Membership]:
    stmt = select(Membership).where(Membership.user_id == user_id).order_by(Membership.created_at.asc())
    async with get_session() as db:
        result = await db.execute(stmt)
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
async def create_client(
    *,
    client_id: str | None,
    organization_id: str,
    name: str,
    slug: str,
    industry: str | None = None,
    website: str | None = None,
) -> Client:
    client = Client(
        id=client_id or uuid.uuid4().hex,
        organization_id=organization_id,
        name=name,
        slug=slug,
        industry=industry,
        website=website,
    )
    async with get_session() as db:
        db.add(client)
    return client


async def list_clients(organization_id: str) -> list[Client]:
    stmt = (
        select(Client)
        .where(Client.organization_id == organization_id)
        .order_by(Client.created_at.desc())
    )
    async with get_session() as db:
        result = await db.execute(stmt)
        return list(result.scalars().all())


async def get_client(client_id: str) -> Client | None:
    async with get_session() as db:
        return await db.get(Client, client_id)


async def delete_client(client_id: str) -> bool:
    async with get_session() as db:
        client = await db.get(Client, client_id)
        if client is None:
            return False
        await db.delete(client)
    return True


# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------
async def create_data_source(
    *,
    organization_id: str,
    client_id: str,
    connector_type: str,
    config_json: str = "{}",
    status: str = "pending",
) -> DataSource:
    ds = DataSource(
        id=uuid.uuid4().hex,
        organization_id=organization_id,
        client_id=client_id,
        connector_type=connector_type,
        config_json=config_json,
        status=status,
    )
    async with get_session() as db:
        db.add(ds)
    return ds


async def list_data_sources(organization_id: str, *, client_id: str | None = None) -> list[DataSource]:
    stmt = select(DataSource).where(DataSource.organization_id == organization_id)
    if client_id:
        stmt = stmt.where(DataSource.client_id == client_id)
    stmt = stmt.order_by(DataSource.created_at.desc())
    async with get_session() as db:
        result = await db.execute(stmt)
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Marketing data (canonical normalized rows)
# ---------------------------------------------------------------------------
async def bulk_insert_marketing_data(rows: list[dict[str, Any]]) -> int:
    """Insert many normalized marketing rows. Each dict must contain keys:
    client_id, organization_id, data_source_id, date, channel, spend,
    impressions, clicks, conversions, revenue."""
    if not rows:
        return 0
    objs = [MarketingData(id=uuid.uuid4().hex, **r) for r in rows]
    async with get_session() as db:
        db.add_all(objs)
    return len(objs)


# ---------------------------------------------------------------------------
# ModelJob CRUD
# ---------------------------------------------------------------------------
async def create_model_job(
    *,
    job_id: str | None,
    organization_id: str,
    client_id: str | None,
    name: str,
    config_json: str,
    status: str = "queued",
) -> ModelJob:
    job = ModelJob(
        id=job_id or uuid.uuid4().hex,
        organization_id=organization_id,
        client_id=client_id,
        name=name,
        config_json=config_json,
        status=status,
        created_at=_now(),
    )
    async with get_session() as db:
        db.add(job)
    return job


async def update_model_job(
    job_id: str,
    *,
    status: str | None = None,
    error: str | None = None,
    artifact_key: str | None = None,
    result_summary: dict[str, Any] | None = None,
    duration_seconds: float | None = None,
    finished_at: datetime | None = None,
) -> ModelJob | None:
    updates: dict[str, Any] = {}
    if status is not None:
        updates["status"] = status
    if error is not None:
        updates["error"] = error
    if artifact_key is not None:
        updates["artifact_key"] = artifact_key
    if result_summary is not None:
        updates["result_summary_json"] = json.dumps(result_summary, default=str)
    if duration_seconds is not None:
        updates["duration_seconds"] = duration_seconds
    if finished_at is not None:
        updates["finished_at"] = finished_at
    if not updates:
        return await get_model_job(job_id)
    async with get_session() as db:
        job = await db.get(ModelJob, job_id)
        if job is None:
            return None
        for key, val in updates.items():
            setattr(job, key, val)
    return job


async def list_model_jobs(organization_id: str, *, client_id: str | None = None) -> list[ModelJob]:
    stmt = (
        select(ModelJob)
        .where(ModelJob.organization_id == organization_id)
        .order_by(ModelJob.created_at.desc())
    )
    if client_id:
        stmt = stmt.where(ModelJob.client_id == client_id)
    async with get_session() as db:
        result = await db.execute(stmt)
        return list(result.scalars().all())


async def get_model_job(job_id: str) -> ModelJob | None:
    async with get_session() as db:
        return await db.get(ModelJob, job_id)


# ---------------------------------------------------------------------------
# ChannelResult
# ---------------------------------------------------------------------------
async def add_channel_results(
    job_id: str,
    organization_id: str,
    client_id: str | None,
    results: list[dict[str, Any]],
) -> list[ChannelResult]:
    rows = [
        ChannelResult(
            id=uuid.uuid4().hex,
            model_job_id=job_id,
            organization_id=organization_id,
            client_id=client_id,
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
    stmt = (
        select(ChannelResult)
        .where(ChannelResult.model_job_id == job_id)
        .order_by(ChannelResult.contribution.desc())
    )
    async with get_session() as db:
        result = await db.execute(stmt)
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Budget optimizations
# ---------------------------------------------------------------------------
async def create_budget_optimization(
    *,
    organization_id: str,
    client_id: str | None,
    model_job_id: str | None,
    constraints: dict[str, Any],
    allocations: dict[str, Any],
    total_budget: float,
    expected_total_revenue: float,
    is_feasible: bool,
    created_by: str | None = None,
) -> BudgetOptimization:
    opt = BudgetOptimization(
        id=uuid.uuid4().hex,
        organization_id=organization_id,
        client_id=client_id,
        model_job_id=model_job_id,
        constraints_json=json.dumps(constraints, default=str),
        allocations_json=json.dumps(allocations, default=str),
        total_budget=total_budget,
        expected_total_revenue=expected_total_revenue,
        is_feasible=is_feasible,
        created_by=created_by,
    )
    async with get_session() as db:
        db.add(opt)
    return opt


async def list_budget_optimizations(organization_id: str, *, client_id: str | None = None) -> list[BudgetOptimization]:
    stmt = (
        select(BudgetOptimization)
        .where(BudgetOptimization.organization_id == organization_id)
        .order_by(BudgetOptimization.created_at.desc())
    )
    if client_id:
        stmt = stmt.where(BudgetOptimization.client_id == client_id)
    async with get_session() as db:
        result = await db.execute(stmt)
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
async def create_report(
    *,
    organization_id: str,
    client_id: str | None,
    model_job_id: str | None,
    client_name: str,
    content: dict[str, Any],
) -> Report:
    report = Report(
        id=uuid.uuid4().hex,
        organization_id=organization_id,
        client_id=client_id,
        model_job_id=model_job_id,
        client_name=client_name,
        content_json=json.dumps(content, default=str),
    )
    async with get_session() as db:
        db.add(report)
    return report


async def get_report(report_id: str) -> Report | None:
    async with get_session() as db:
        return await db.get(Report, report_id)


async def list_reports(organization_id: str, *, client_id: str | None = None) -> list[Report]:
    stmt = (
        select(Report)
        .where(Report.organization_id == organization_id)
        .order_by(Report.created_at.desc())
    )
    if client_id:
        stmt = stmt.where(Report.client_id == client_id)
    async with get_session() as db:
        result = await db.execute(stmt)
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------
async def add_insight(
    *,
    organization_id: str,
    client_id: str | None,
    model_job_id: str | None,
    type: str,
    title: str,
    body: str,
    confidence: float = 0.0,
    metrics: dict[str, Any] | None = None,
    source: str = "llm",
) -> Insight:
    insight = Insight(
        id=uuid.uuid4().hex,
        organization_id=organization_id,
        client_id=client_id,
        model_job_id=model_job_id,
        type=type,
        title=title,
        body=body,
        confidence=confidence,
        metrics_json=json.dumps(metrics or {}, default=str),
        source=source,
    )
    async with get_session() as db:
        db.add(insight)
    return insight


async def list_insights(model_job_id: str) -> list[Insight]:
    stmt = select(Insight).where(Insight.model_job_id == model_job_id).order_by(Insight.created_at.desc())
    async with get_session() as db:
        result = await db.execute(stmt)
        return list(result.scalars().all())
