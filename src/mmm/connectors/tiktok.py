"""TikTok Marketing API connector."""
from __future__ import annotations

from datetime import datetime

import httpx
import pandas as pd

from mmm.config import get_settings
from mmm.connectors.base import ConnectorConfig, DataConnector


class TikTokConnector(DataConnector):
    def __init__(self) -> None:
        super().__init__(ConnectorConfig(name="tiktok", credentials={
            "access_token": get_settings().tiktok_access_token,
            "app_id": get_settings().tiktok_app_id,
        }))
    def is_configured(self) -> bool:
        return bool(self.config.credentials.get("access_token"))
    def fetch_spend(self, start: datetime, end: datetime) -> pd.DataFrame:
        params = {"access_token": self.config.credentials["access_token"], "report_type": "BASIC",
            "data_level": "AUCTION_ADVERTISER", "dimensions": '["STAT_TIME_BY_DAY"]',
            "metrics": '["spend","impressions","clicks","conversion","conversion_value"]',
            "start_date": start.strftime("%Y-%m-%d"), "end_date": end.strftime("%Y-%m-%d")}
        with httpx.Client(timeout=30) as c:
            r = c.get("https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/", params=params)
            r.raise_for_status()
            data = r.json().get("data", {}).get("list", [])
        if not data:
            return pd.DataFrame(columns=["date","channel","spend","impressions","clicks","conversions","revenue"])
        rows = []
        for item in data:
            d = item.get("dimensions", {}); m = item.get("metrics", {})
            rows.append({"date": pd.to_datetime(d.get("stat_time_by_day")), "channel": "tiktok",
                "spend": float(m.get("spend", 0)), "impressions": int(m.get("impressions", 0)),
                "clicks": int(m.get("clicks", 0)), "conversions": int(m.get("conversion", 0)),
                "revenue": float(m.get("conversion_value", 0))})
        return pd.DataFrame(rows)
