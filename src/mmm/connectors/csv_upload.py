"""CSV upload connector - universal fallback."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from mmm.connectors.base import ConnectorConfig, DataConnector


class CSVConnector(DataConnector):
    def __init__(self) -> None:
        super().__init__(ConnectorConfig(name="csv"))
        self._df: pd.DataFrame | None = None

    def is_configured(self) -> bool:
        return True

    def load_file(self, path: str | Path) -> None:
        p = Path(path)
        self._df = pd.read_csv(p) if p.suffix == ".csv" else pd.read_excel(p)

    def load_dataframe(self, df: pd.DataFrame) -> None:
        self._df = df

    def fetch_spend(self, start: datetime, end: datetime) -> pd.DataFrame:
        if self._df is None:
            raise ValueError("no data loaded")
        df = self._df.copy()
        df["date"] = pd.to_datetime(df["date"])
        return df[(df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))]
