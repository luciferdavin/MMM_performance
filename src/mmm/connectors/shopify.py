"""Shopify Admin API connector."""
from __future__ import annotations
import httpx, pandas as pd
from datetime import datetime
from mmm.connectors.base import DataConnector, ConnectorConfig
from mmm.config import get_settings

class ShopifyConnector(DataConnector):
    def __init__(self) -> None:
        super().__init__(ConnectorConfig(name="shopify", credentials={
            "store_domain": get_settings().shopify_store_domain,
            "access_token": get_settings().shopify_access_token,
        }))
    def is_configured(self) -> bool:
        return all(self.config.credentials.get(k) for k in ("store_domain", "access_token"))
    def fetch_spend(self, start: datetime, end: datetime) -> pd.DataFrame:
        domain = self.config.credentials["store_domain"]
        url = f"https://{domain}/admin/api/2024-01/orders.json"
        params = {"created_at_min": start.isoformat(), "created_at_max": end.isoformat(), "status": "any"}
        with httpx.Client(timeout=30) as c:
            r = c.get(url, headers={"X-Shopify-Access-Token": self.config.credentials["access_token"]}, params=params)
            r.raise_for_status()
            orders = r.json().get("orders", [])
        if not orders:
            return pd.DataFrame(columns=["date","channel","spend","impressions","clicks","conversions","revenue"])
        rows = [{"date": pd.to_datetime(o["created_at"]).normalize(), "channel": "shopify_revenue",
                 "spend": 0, "impressions": 0, "clicks": 0, "conversions": 1, "revenue": float(o.get("total_price", 0))} for o in orders]
        df = pd.DataFrame(rows).groupby("date", as_index=False).agg({"spend":"sum","impressions":"sum","clicks":"sum","conversions":"sum","revenue":"sum"})
        df["channel"] = "shopify_revenue"
        return df
