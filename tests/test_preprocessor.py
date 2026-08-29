"""Tests for preprocessor module."""
from mmm.core.preprocessor import aggregate_wide, records_to_dataframe
from mmm.models.schemas import Granularity, MediaRecord

SAMPLE_RECORDS = [
    MediaRecord(date="2024-01-01", channel="meta", spend=1000, impressions=50000, clicks=2000, conversions=50, revenue=2500),
    MediaRecord(date="2024-01-01", channel="google", spend=800, impressions=40000, clicks=1500, conversions=40, revenue=2000),
    MediaRecord(date="2024-01-08", channel="meta", spend=1200, impressions=55000, clicks=2200, conversions=55, revenue=2750),
    MediaRecord(date="2024-01-08", channel="google", spend=900, impressions=42000, clicks=1600, conversions=45, revenue=2250),
]

def test_records_to_dataframe():
    df = records_to_dataframe(SAMPLE_RECORDS)
    assert len(df) == 4
    assert "date" in df.columns
    assert "channel" in df.columns
    assert df["spend"].dtype in ("float64", "int64")

def test_aggregate_wide():
    df = records_to_dataframe(SAMPLE_RECORDS)
    wide, channels = aggregate_wide(df, granularity=Granularity.WEEK)
    assert "meta" in channels
    assert "google" in channels
    assert len(wide) == 2
    assert wide.loc[wide.index[0], "meta"] == 1000

def test_aggregate_monthly():
    df = records_to_dataframe(SAMPLE_RECORDS)
    wide, channels = aggregate_wide(df, granularity=Granularity.MONTH)
    assert len(wide) == 1
    assert wide.loc[wide.index[0], "meta"] == 2200
