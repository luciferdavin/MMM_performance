"""Google Ads API connector."""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from mmm.config import get_settings
from mmm.connectors.base import ConnectorConfig, DataConnector


class GoogleAdsConnector(DataConnector):
    def __init__(self) -> None:
        s = get_settings()
        super().__init__(ConnectorConfig(name="google_ads", credentials={
            "developer_token": s.google_ads_developer_token, "client_id": s.google_ads_client_id,
            "client_secret": s.google_ads_client_secret, "refresh_token": s.google_ads_refresh_token,
            "customer_id": s.google_ads_customer_id,
        }))
    def is_configured(self) -> bool:
        return all(self.config.credentials.get(k) for k in ("developer_token", "refresh_token", "customer_id"))
    def fetch_spend(self, start: datetime, end: datetime) -> pd.DataFrame:
        try:
            from google.ads.googleads.client import GoogleAdsClient
        except ImportError:
            raise ImportError("pip install google-ads")
        creds = {k: v for k, v in self.config.credentials.items() if v}
        client = GoogleAdsClient.load_from_dict(creds)
        ga = client.get_service("GoogleAdsService")
        q = "SELECT segments.date, metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions, metrics.conversions_value FROM campaign WHERE segments.date BETWEEN '{}' AND '{}'".format(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        rows = []
        for batch in ga.search_stream(customer_id=self.config.credentials["customer_id"], query=q):
            for r in batch.results:
                rows.append({"date": pd.to_datetime(r.segments.date), "channel": "google_ads",
                    "spend": r.metrics.cost_micros / 1e6, "impressions": r.metrics.impressions,
                    "clicks": r.metrics.clicks, "conversions": int(r.metrics.conversions),
                    "revenue": r.metrics.conversions_value})
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["date","channel","spend","impressions","clicks","conversions","revenue"])
