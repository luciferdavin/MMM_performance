"""Meta Marketing API connector."""
from __future__ import annotations

from datetime import datetime

import httpx
import pandas as pd

from mmm.config import get_settings
from mmm.connectors.base import ConnectorConfig, DataConnector


class MetaAdsConnector(DataConnector):
    def __init__(self) -> None:
        super().__init__(ConnectorConfig(name="meta_ads", credentials={
            "access_token": get_settings().meta_access_token,
            "ad_account_id": "",
        }))
    def is_configured(self) -> bool:
        return bool(self.config.credentials.get("access_token"))
    def fetch_spend(self, start: datetime, end: datetime) -> pd.DataFrame:
        token = self.config.credentials["access_token"]
        account_id = self.config.credentials.get("ad_account_id", "")
        url = f"https://graph.facebook.com/v19.0/{account_id}/insights"
        tr = '{{"since":"{}","until":"{}"}}'.format(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        params = {"access_token": token, "fields": "spend,impressions,clicks,actions,action_values",
                  "level": "account", "time_range": tr, "time_increment": "1"}
        with httpx.Client(timeout=30) as c:
            r = c.get(url, params=params); r.raise_for_status()
            data = r.json().get("data", [])
        if not data:
            return pd.DataFrame(columns=["date","channel","spend","impressions","clicks","conversions","revenue"])
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date_start"]); df["channel"] = "meta"
        for col, default in [("spend",0),("impressions",0),("clicks",0)]:
            df[col] = pd.to_numeric(df.get(col, default), errors="coerce").fillna(default)
        df["conversions"] = 0; df["revenue"] = 0.0
        return df[["date","channel","spend","impressions","clicks","conversions","revenue"]]
