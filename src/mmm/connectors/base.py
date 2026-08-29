"""Abstract data connector interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

import pandas as pd
from pydantic import BaseModel


class ConnectorConfig(BaseModel):
    name: str
    enabled: bool = True
    credentials: dict[str, str] = {}


class DataConnector(ABC):
    def __init__(self, config: ConnectorConfig) -> None:
        self.config = config

    @abstractmethod
    def fetch_spend(self, start: datetime, end: datetime) -> pd.DataFrame:
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        pass
