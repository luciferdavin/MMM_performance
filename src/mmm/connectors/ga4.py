"""Google Analytics 4 Data API connector."""
from __future__ import annotations
import pandas as pd
from datetime import datetime
from mmm.connectors.base import DataConnector, ConnectorConfig
from mmm.config import get_settings

class GA4Connector(DataConnector):
    def __init__(self) -> None:
        super().__init__(ConnectorConfig(name="ga4", credentials={"property_id": get_settings().ga4_property_id}))
    def is_configured(self) -> bool:
        return bool(self.config.credentials.get("property_id"))
    def fetch_spend(self, start: datetime, end: datetime) -> pd.DataFrame:
        try:
            from google.analytics.data_v1beta import BetaAnalyticsDataClient
            from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric
        except ImportError:
            raise ImportError("pip install google-analytics-data")
        client = BetaAnalyticsDataClient()
        req = RunReportRequest(
            property=f"properties/{self.config.credentials['property_id']}",
            date_ranges=[DateRange(start_date=str(start.date()), end_date=str(end.date()))],
            dimensions=[Dimension(name="date")],
            metrics=[Metric(name="sessions"), Metric(name="screenPageViews"), Metric(name="transactions"), Metric(name="totalRevenue")],
        )
        rows = []
        for row in client.run_report(req).rows:
            rows.append({"date": pd.to_datetime(row.dimension_values[0].value, format="%Y%m%d"), "channel": "organic",
                "spend": 0, "impressions": int(row.metric_values[1].value), "clicks": int(row.metric_values[0].value),
                "conversions": int(row.metric_values[2].value), "revenue": float(row.metric_values[3].value)})
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["date","channel","spend","impressions","clicks","conversions","revenue"])
