"""Unit tests for data connectors."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from mmm.connectors.base import ConnectorConfig, DataConnector
from mmm.connectors.csv_upload import CSVConnector
from mmm.connectors.meta_ads import MetaAdsConnector
from mmm.connectors.tiktok import TikTokConnector


CANONICAL_COLUMNS = [
    "date",
    "channel",
    "spend",
    "impressions",
    "clicks",
    "conversions",
    "revenue",
]


class FakeResponse:
    """Minimal httpx response double for connector tests."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class FakeClient:
    """Context-manager compatible httpx.Client double."""

    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.requests: list[dict] = []

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def get(self, url: str, **kwargs: object) -> FakeResponse:
        self.requests.append({"url": url, **kwargs})
        return FakeResponse(self.payload)


def build_connector(connector_cls: type[DataConnector], credentials: dict[str, str]) -> DataConnector:
    """Create a connector with explicit credentials, avoiding environment settings."""
    connector = connector_cls.__new__(connector_cls)
    DataConnector.__init__(
        connector,
        ConnectorConfig(name=connector_cls.__name__, credentials=credentials),
    )
    return connector


def patch_http_client(monkeypatch: pytest.MonkeyPatch, module: object, payload: dict) -> FakeClient:
    """Patch a connector module's httpx.Client with a fake response payload."""
    fake_client = FakeClient(payload)
    monkeypatch.setattr(module.httpx, "Client", lambda **_: fake_client)
    return fake_client


def test_csv_load_dataframe_then_fetch_spend_filters_date_range() -> None:
    connector = CSVConnector()
    source = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-15", "2024-02-01"],
            "channel": ["meta", "tiktok", "google_ads"],
            "spend": [100.0, 200.0, 300.0],
        }
    )

    connector.load_dataframe(source)
    result = connector.fetch_spend(datetime(2024, 1, 10), datetime(2024, 1, 31))

    assert result["channel"].tolist() == ["tiktok"]
    assert result["spend"].tolist() == [200.0]
    assert pd.api.types.is_datetime64_any_dtype(result["date"])


def test_csv_load_file_from_temp_csv(tmp_path: pytest.TempPathFactory) -> None:
    connector = CSVConnector()
    csv_path = tmp_path / "spend.csv"
    pd.DataFrame(
        {
            "date": ["2024-03-01", "2024-03-02"],
            "channel": ["meta", "tiktok"],
            "spend": [10.5, 20.5],
        }
    ).to_csv(csv_path, index=False)

    connector.load_file(csv_path)
    result = connector.fetch_spend(datetime(2024, 3, 1), datetime(2024, 3, 1))

    assert result["channel"].tolist() == ["meta"]
    assert result["spend"].tolist() == [10.5]


def test_csv_fetch_spend_without_loaded_data_raises_value_error() -> None:
    connector = CSVConnector()

    with pytest.raises(ValueError, match="no data loaded"):
        connector.fetch_spend(datetime(2024, 1, 1), datetime(2024, 1, 31))


def test_tiktok_fetch_spend_maps_response_to_canonical_dataframe(monkeypatch: pytest.MonkeyPatch) -> None:
    import mmm.connectors.tiktok as tiktok_module

    payload = {
        "data": {
            "list": [
                {
                    "dimensions": {"stat_time_by_day": "2024-01-01"},
                    "metrics": {
                        "spend": "123.45",
                        "impressions": "1000",
                        "clicks": "50",
                        "conversion": "7",
                        "conversion_value": "456.78",
                    },
                }
            ]
        }
    }
    fake_client = patch_http_client(monkeypatch, tiktok_module, payload)
    connector = build_connector(TikTokConnector, {"access_token": "token", "app_id": "app"})

    result = connector.fetch_spend(datetime(2024, 1, 1), datetime(2024, 1, 31))

    assert result.columns.tolist() == CANONICAL_COLUMNS
    assert result.loc[0, "channel"] == "tiktok"
    assert result.loc[0, "spend"] == pytest.approx(123.45)
    assert isinstance(result.loc[0, "spend"], float)
    assert result.loc[0, "impressions"] == 1000
    assert pd.api.types.is_integer_dtype(result["impressions"])
    assert result.loc[0, "clicks"] == 50
    assert result.loc[0, "conversions"] == 7
    assert result.loc[0, "revenue"] == pytest.approx(456.78)
    assert fake_client.requests[0]["url"] == "https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/"


def test_tiktok_fetch_spend_empty_response_returns_empty_canonical_dataframe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import mmm.connectors.tiktok as tiktok_module

    patch_http_client(monkeypatch, tiktok_module, {"data": {"list": []}})
    connector = build_connector(TikTokConnector, {"access_token": "token"})

    result = connector.fetch_spend(datetime(2024, 1, 1), datetime(2024, 1, 31))

    assert result.empty
    assert result.columns.tolist() == CANONICAL_COLUMNS


def test_meta_ads_fetch_spend_maps_response_to_canonical_dataframe(monkeypatch: pytest.MonkeyPatch) -> None:
    import mmm.connectors.meta_ads as meta_ads_module

    payload = {
        "data": [
            {
                "date_start": "2024-02-01",
                "spend": "321.09",
                "impressions": "2000",
                "clicks": "80",
            }
        ]
    }
    fake_client = patch_http_client(monkeypatch, meta_ads_module, payload)
    connector = build_connector(
        MetaAdsConnector,
        {"access_token": "token", "ad_account_id": "act_123456"},
    )

    result = connector.fetch_spend(datetime(2024, 2, 1), datetime(2024, 2, 29))

    assert result.columns.tolist() == CANONICAL_COLUMNS
    assert result.loc[0, "channel"] == "meta"
    assert result.loc[0, "spend"] == pytest.approx(321.09)
    assert result.loc[0, "impressions"] == 2000
    assert result.loc[0, "clicks"] == 80
    assert result.loc[0, "conversions"] == 0
    assert result.loc[0, "revenue"] == pytest.approx(0.0)
    assert fake_client.requests[0]["url"] == "https://graph.facebook.com/v19.0/act_123456/insights"


def test_connector_is_configured_for_empty_vs_populated_credentials() -> None:
    empty_connector = build_connector(TikTokConnector, {"access_token": ""})
    configured_connector = build_connector(TikTokConnector, {"access_token": "token"})

    assert not empty_connector.is_configured()
    assert configured_connector.is_configured()
