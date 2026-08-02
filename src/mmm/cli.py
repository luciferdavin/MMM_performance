"""CLI for training, optimizing, and reporting."""
from __future__ import annotations
import asyncio
import json
import click
import pandas as pd
from rich.console import Console
from rich.table import Table
from mmm.core.engine import MMMModel
from mmm.core.config import build_model_config
from mmm.core.optimizer import allocate_budget_scipy
from mmm.connectors.csv_upload import CSVConnector
from mmm.models.schemas import BudgetConstraints, MediaRecord, MMMDataset

console = Console()


@click.group()
def main():
    """MMM Platform CLI."""


@main.command()
@click.option("--csv", type=click.Path(exists=True), required=True)
@click.option("--granularity", default="week")
@click.option("--draws", default=1000)
@click.option("--tune", default=1000)
@click.option("--out", type=click.Path(), default="model_artifacts/model")
def train(csv, granularity, draws, tune, out):
    """Train an MMM model from a CSV file."""
    df = pd.read_csv(csv)
    records = [MediaRecord(**row) for row in df.to_dict("records")]
    dataset = MMMDataset(records=records)
    channels = dataset.channels
    config = build_model_config(channels=channels, granularity=granularity, draws=draws, tune=tune)
    model = MMMModel(config)
    result = model.fit(dataset)
    console.print(json.dumps(result.model_dump(), indent=2, default=str))
    if result.status == "ok":
        model.save(out)
        console.print(f"[green]Model saved to {out}[/green]")


@main.command()
@click.option("--model", type=click.Path(exists=True), required=True)
@click.option("--budget", type=float, required=True)
def allocate(model, budget):
    """Allocate a budget across channels using a trained model."""
    m = MMMModel.load(model)
    constraints = BudgetConstraints(total_budget=budget)
    result = m.allocate_budget(budget, constraints=constraints)
    table = Table(title=f"Budget Allocation (${budget:,.0f})")
    table.add_column("Channel"); table.add_column("Budget"); table.add_column("Share"); table.add_column("Expected Revenue")
    for a in result.allocations:
        table.add_row(a.channel, f"${a.allocated_budget:,.0f}", f"{a.share:.1%}", f"${a.expected_revenue:,.0f}")
    console.print(table)
    console.print(f"[bold]Expected total revenue: ${result.expected_total_revenue:,.0f}[/bold]")


@main.command()
@click.option("--model", type=click.Path(exists=True), required=True)
def contributions(model):
    """Show channel contributions from a trained model."""
    m = MMMModel.load(model)
    table = Table(title="Channel Contributions")
    table.add_column("Channel"); table.add_column("Spend"); table.add_column("Share"); table.add_column("ROAS")
    for c in m.get_channel_contributions():
        table.add_row(c.channel, f"${c.spend:,.0f}", f"{c.share:.1%}", f"{c.roas:.2f}x")
    console.print(table)


@main.command()
def seed() -> None:
    """Create a demo environment with synthetic data and a trained model."""
    from pathlib import Path

    import numpy as np

    rng = np.random.default_rng(42)
    dates = pd.date_range("2024-01-01", periods=12, freq="W-MON")
    rows = []
    base = {"meta": 3000, "google_ads": 2500, "tiktok": 1500, "tv": 1000, "radio": 500}
    eff = {"meta": 3.5, "google_ads": 4.0, "tiktok": 3.0, "tv": 1.5, "radio": 1.2}
    for i, d in enumerate(dates):
        season = 1 + 0.15 * np.sin(2 * np.pi * i / 12)
        for channel_index, (ch, spend_base) in enumerate(base.items()):
            channel_wave = np.sin(2 * np.pi * i / 12 + channel_index)
            spend = spend_base * (1 + 0.08 * channel_wave) + rng.normal(0, spend_base * 0.03)
            spend = max(spend, 0)
            revenue = spend * eff[ch] * (1 / (1 + spend / (spend_base * 20))) * season
            rows.append({
                "date": d.date().isoformat(), "channel": ch, "spend": round(spend, 2),
                "impressions": int(spend * 1500), "clicks": int(spend * 30),
                "conversions": int(revenue / 80), "revenue": round(revenue, 2),
            })

    sample_path = Path("data/sample/seed_data.csv")
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(sample_path, index=False)

    records = [MediaRecord(**row) for row in df.to_dict("records")]
    dataset = MMMDataset(records=records)
    channels = dataset.channels
    config = build_model_config(
        channels=channels,
        granularity="week",
        draws=100,
        tune=100,
        chains=1,
        adstock_max_lag=4,
        name="seed_model",
    )
    model = MMMModel(config)
    console.print("[bold]Training seed MMM model...[/bold]")
    result = model.fit(dataset)
    if result.status != "ok":
        console.print(f"[red]Seed model fit status: {result.status}[/red]")
        console.print(f"[red]Error: {result.error or 'Unknown fit error'}[/red]")
        raise click.exceptions.Exit(1)

    # Persist to database
    async def _persist_seed():
        from mmm.db.session import init_db
        from mmm.db.repo import create_client, create_model_job, add_channel_results

        await init_db()

        client = await create_client(
            client_id="seed-client",
            organization_id="dev-org",
            name="Seed Demo Client",
            slug="seed-demo",
        )
        console.print(f"Persisted client: {client.id} ({client.name})")

        job = await create_model_job(
            job_id=result.model_id,
            organization_id="dev-org",
            client_id=client.id,
            model_name=config.name,
            config_json=json.dumps(config.model_dump(), default=str),
            status="completed",
            r2=result.diagnostics.r2 if result.diagnostics else None,
            mape=result.diagnostics.mape if result.diagnostics else None,
        )
        console.print(f"Persisted model job: {job.id}")

        contribs = model.get_channel_contributions()
        if contribs:
            channel_results = [
                {
                    "channel": c.channel,
                    "contribution": c.contribution,
                    "share": c.share,
                    "roas": c.roas,
                    "spend": c.spend,
                }
                for c in contribs
            ]
            await add_channel_results(job.id, channel_results)
            console.print(f"Persisted {len(channel_results)} channel results")

    asyncio.run(_persist_seed())

    allocation = model.allocate_budget(total_budget=50000, constraints=BudgetConstraints(total_budget=50000))
    model_path = Path("model_artifacts/seed_model")
    model.save(model_path)

    diagnostics = result.diagnostics
    console.print("[green]Seed demo environment created[/green]")
    console.print(f"Channels trained: {', '.join(channels)}")
    if diagnostics:
        console.print(f"FitResult status: {result.status} | R²: {diagnostics.r2:.3f} | MAPE: {diagnostics.mape:.1f}%")
    else:
        console.print(f"FitResult status: {result.status}")
    console.print(f"Seed data written to {sample_path}")
    console.print(f"Model saved to {model_path}")

    table = Table(title="Seed Budget Allocation ($50,000)")
    table.add_column("Channel"); table.add_column("Budget"); table.add_column("Share")
    for item in allocation.allocations:
        table.add_row(item.channel, f"${item.allocated_budget:,.0f}", f"{item.share:.1%}")
    console.print(table)


@main.command()
def generate_sample():
    """Generate a synthetic sample dataset."""
    import numpy as np
    rng = np.random.default_rng(42)
    dates = pd.date_range("2023-01-02", periods=104, freq="W")
    rows = []
    base = {"meta": 3000, "google_ads": 2500, "tiktok": 1500, "tv": 1000, "radio": 500}
    eff = {"meta": 3.5, "google_ads": 4.0, "tiktok": 3.0, "tv": 1.5, "radio": 1.2}
    for i, d in enumerate(dates):
        season = 1 + 0.3 * np.sin(2 * np.pi * i / 52)
        for ch, spend_base in base.items():
            spend = spend_base * (1 + 0.05 * np.sin(2 * np.pi * i / 52 + hash(ch) % 7))
            spend = max(spend, 0)
            revenue = spend * eff[ch] * (1 / (1 + spend / (spend_base * 20))) * season
            rows.append({"date": d, "channel": ch, "spend": round(spend, 2),
                         "impressions": int(spend * 1500), "clicks": int(spend * 30),
                         "conversions": int(revenue / 80), "revenue": round(revenue, 2)})
    df = pd.DataFrame(rows)
    df.to_csv("data/sample/sample_data.csv", index=False)
    console.print("[green]Sample data written to data/sample/sample_data.csv[/green]")


if __name__ == "__main__":
    main()
