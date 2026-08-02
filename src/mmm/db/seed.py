"""Seed the database with demo data: one client + a trained MMM model."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd


async def seed_demo_data(organization_id: str = "dev-org") -> dict[str, Any]:
    """Create a demo client and train a small MMM model, persisting results.

    - Generates 12 weeks of synthetic spend/revenue across 5 channels.
    - Trains with reduced parameters (draws=100, tune=100, chains=1) for speed.
    - Saves the ModelJob and ChannelResult rows to the database.
    - Returns a summary dict of what was created.
    """
    from mmm.config import get_settings
    from mmm.core.config import build_model_config
    from mmm.core.engine import MMMModel
    from mmm.db.repo import add_channel_results, create_client, create_model_job
    from mmm.db.session import init_db
    from mmm.models.schemas import MediaRecord, MMMDataset

    # Ensure tables exist
    await init_db()

    # --- Generate synthetic records ---
    rng = np.random.default_rng(42)
    dates = pd.date_range("2024-01-01", periods=12, freq="W-MON")
    base_spend = {"meta": 3000, "google_ads": 2500, "tiktok": 1500, "tv": 1000, "radio": 500}
    efficiency = {"meta": 3.5, "google_ads": 4.0, "tiktok": 3.0, "tv": 1.5, "radio": 1.2}

    rows: list[dict[str, Any]] = []
    for i, d in enumerate(dates):
        season = 1 + 0.15 * np.sin(2 * np.pi * i / 12)
        for idx, (ch, spend_base) in enumerate(base_spend.items()):
            wave = np.sin(2 * np.pi * i / 12 + idx)
            spend = max(spend_base * (1 + 0.08 * wave) + rng.normal(0, spend_base * 0.03), 0)
            revenue = spend * efficiency[ch] * (1 / (1 + spend / (spend_base * 20))) * season
            rows.append(
                {
                    "date": d,
                    "channel": ch,
                    "spend": round(float(spend), 2),
                    "impressions": int(spend * 1500),
                    "clicks": int(spend * 30),
                    "conversions": int(revenue / 80),
                    "revenue": round(float(revenue), 2),
                }
            )

    records = [MediaRecord(**r) for r in rows]
    dataset = MMMDataset(records=records)

    # --- Create demo client ---
    client_id = uuid.uuid4().hex[:12]
    await create_client(
        client_id=client_id,
        organization_id=organization_id,
        name="Demo Client",
        slug="demo-client",
    )

    # --- Train model with reduced parameters ---
    config = build_model_config(
        channels=dataset.channels,
        granularity="week",
        draws=100,
        tune=100,
        chains=1,
        adstock_max_lag=4,
        name="seed_model",
    )
    model = MMMModel(config)
    fit_result = model.fit(dataset)

    if fit_result.status != "ok":
        return {"status": "failed", "error": fit_result.error}

    # --- Extract metrics ---
    contributions = model.get_channel_contributions()
    diag = fit_result.diagnostics
    r2_val = round(diag.r2, 4) if diag else None
    mape_val = round(diag.mape, 4) if diag else None

    # --- Persist ModelJob ---
    job_id = uuid.uuid4().hex[:12]
    config_payload = json.dumps(
        {"model": config.model_dump(mode="json"), "records_count": len(records)},
        default=str,
    )
    await create_model_job(
        job_id=job_id,
        organization_id=organization_id,
        client_id=client_id,
        model_name=config.name,
        config_json=config_payload,
        status="succeeded",
        r2=r2_val,
        mape=mape_val,
    )

    # --- Persist ChannelResults ---
    channel_dicts = [c.model_dump() for c in contributions]
    await add_channel_results(job_id, channel_dicts)

    return {
        "status": "ok",
        "client_id": client_id,
        "job_id": job_id,
        "organization_id": organization_id,
        "channels": len(contributions),
        "records": len(records),
        "r2": r2_val,
        "mape": mape_val,
    }