# Data Connector Specification

*Research date: 2026-08-01.*

## Canonical Schema

Every connector normalizes to:

```
date: datetime
channel: str        # meta, google_ads, tiktok, shopify_revenue, organic, tv, radio...
spend: float        # media spend in local currency
impressions: int
clicks: int
conversions: int
revenue: float      # attributed/known revenue (or target KPI)
```

## Connector Priority

| Priority | Connector | API | Auth | Notes |
|----------|-----------|-----|------|-------|
| P0 | CSV upload | n/a | none | Universal fallback; file or pasted frame |
| P0 | Shopify | Admin API | X-Shopify-Access-Token | Revenue source; orders endpoint |
| P1 | Meta Ads | Marketing API v19+ | OAuth2 / long-lived token | insights endpoint, time_increment=1 |
| P1 | Google Ads | GoogleAdsService | OAuth2 + developer token | GAQL query; cost_micros -> spend |
| P1 | GA4 | Data API v1beta | service account | organic sessions/revenue |
| P2 | TikTok | Marketing API v1.3 | access token | integrated report endpoint |
| P2 | LinkedIn / Snap / Pinterest | respective APIs | OAuth2 | lower priority |
| P3 | Programmatic (DV360/TTD) | DV360 API / TTD | OAuth2 | complex; later |

## Design Principles

1. Every connector implements `DataConnector` ABC: `fetch_spend(start, end) -> DataFrame` + `is_configured() -> bool`.
2. Normalization happens inside connector; outputs share the canonical schema.
3. Credentials live in `.env` / secret manager / per-tenant encrypted `data_sources` table — never in code.
4. Rate limiting + retry with exponential backoff on HTTP 429.
5. Connectors are async-safe for FastAPI (httpx).

## Control Variables (for model robustness)

- Holidays calendar (US + target markets)
- Google Trends index per category
- Pricing changes / promos
- Macro (CPI, seasonality dummies)

*Implementation: src/mmm/connectors/* — base.py, csv_upload.py, meta_ads.py, google_ads.py, ga4.py, tiktok.py, shopify.py.*
