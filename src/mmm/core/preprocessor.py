"""Data validation, aggregation, and pivoting into training format."""
from __future__ import annotations

import pandas as pd

from mmm.models.schemas import Granularity, MediaRecord, MMMDataset


def records_to_dataframe(records: list[MediaRecord]) -> pd.DataFrame:
    df = pd.DataFrame([r.model_dump() for r in records])
    df["date"] = pd.to_datetime(df["date"])
    return df

def to_training_frame(
    dataset: MMMDataset, *, granularity: Granularity = Granularity.WEEK,
    target_column: str = "revenue",
) -> tuple[pd.DataFrame, list[str]]:
    df = records_to_dataframe(dataset.records)
    return aggregate_wide(df, granularity=granularity, target_column=target_column)

def aggregate_wide(
    df: pd.DataFrame, *, granularity: Granularity = Granularity.WEEK,
    target_column: str = "revenue",
) -> tuple[pd.DataFrame, list[str]]:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["bucket"] = _bucket(df["date"], granularity)
    pivot = df.pivot_table(index="bucket", columns="channel", values="spend", aggfunc="sum").fillna(0)
    target = df.groupby("bucket")[target_column].sum() if target_column in df.columns else pd.Series(0.0, index=pivot.index)
    controls: dict[str, pd.Series] = {}
    for col in ("clicks", "impressions", "conversions"):
        if col in df.columns and col != target_column:
            controls[col] = df.groupby("bucket")[col].sum()
    wide = pivot.copy()
    for name, series in controls.items():
        wide[name] = series.reindex(wide.index).fillna(0)
    wide[target_column] = target.reindex(wide.index).fillna(0)
    wide = wide.sort_index()
    channel_cols = [c for c in pivot.columns if c not in (target_column, "clicks", "impressions", "conversions")]
    return wide, channel_cols

def _bucket(dates: pd.Series, granularity: Granularity) -> pd.Series:
    if granularity == Granularity.DAY:
        return dates.dt.date.astype("datetime64[ns]")
    if granularity == Granularity.WEEK:
        return dates.dt.to_period("W").dt.start_time
    return dates.dt.to_period("M").dt.start_time

def validate_dataset(df: pd.DataFrame, channels: list[str]) -> list[str]:
    warnings: list[str] = []
    if df.empty:
        raise ValueError("dataset is empty")
    missing = [c for c in channels if c not in df.columns]
    if missing:
        raise ValueError(f"missing channel columns: {missing}")
    if df[channels].sum().sum() <= 0:
        raise ValueError("total media spend is zero across all channels")
    idx = df["bucket"] if "bucket" in df.columns else pd.to_datetime(df.index)
    if len(idx) > 1:
        # diff().days returns Index (when idx is a DatetimeIndex) or Series
        # (when idx is a column); drop the leading NaT via dropna() in both cases.
        diffs = idx.sort_values().diff().days
        gap_count = int((diffs.dropna() > 8).sum())
        if gap_count:
            warnings.append(f"date gaps detected: {gap_count} missing buckets")
    return warnings
