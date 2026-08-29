"""End-to-end smoke test against a running API (port 8011)."""

import json
import socket
import sys
import urllib.request

socket.setdefaulttimeout(600)

BASE = "http://127.0.0.1:8011/api/v1"


def req(method, path, body=None, token=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=600) as resp:
            ctype = resp.headers.get("Content-Type", "")
            body = resp.read()
            if "application/json" in ctype:
                return resp.status, json.loads(body.decode())
            return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            return e.code, json.loads(body.decode())
        except Exception:
            return e.code, body


def main():
    print("1) register")
    import time as _t
    email = f"arpit+{int(_t.time())}@acme.test"
    s, b = req("POST", "/auth/register", {
        "email": email, "password": "pw-12345", "name": "Arpit",
        "organization_name": "Acme E2E",
    })
    print("  ", s, b)
    assert s in (200, 201), b
    token = b["access_token"]

    print("2) me")
    s, b = req("GET", "/auth/me", token=token)
    print("  ", s, b)
    assert s == 200

    print("3) create client")
    s, b = req("POST", "/clients", {"name": "Test Brand"}, token=token)
    print("  ", s, b)
    assert s in (200, 201), b
    client_id = b["id"]

    print("4) seed 4 weeks of media records (2 channels — fast fit for live proof)")
    channels = ["Meta", "Google"]
    records = []
    base = __import__("datetime").date(2024, 1, 1)
    for w in range(4):
        d = (base + __import__("datetime").timedelta(weeks=w)).isoformat()
        for ch in channels:
            spend = 1000 + w * 50 + (hash(ch) % 300)
            records.append({
                "date": d,
                "channel": ch,
                "spend": spend,
                "impressions": spend * 40,
                "clicks": spend // 3,
                "conversions": spend // 20,
                "revenue": spend * 3,
            })

    print("5) train-sync (fits real model, persists to DB + disk)")
    s, b = req("POST", "/models/train-sync", {
        "config": {"name": "e2e-model", "draws": 100, "tune": 100, "chains": 1, "adstock_max_lag": 4},
        "records": records,
        "client_id": client_id,
    }, token=token)
    print("  ", s, b if s != 200 else {k: b.get(k) for k in ("model_id", "status", "diagnostics")})
    assert s == 200, b
    model_id = b["model_id"]
    assert b["status"] == "ok", b

    print("6) contributions (reloads artifact from disk)")
    s, b = req("GET", f"/models/{model_id}/contributions", token=token)
    print("  ", s, b if s != 200 else f"{len(b)} channels")
    assert s == 200 and len(b) == 2, b

    print("7) allocate budget")
    s, b = req("POST", f"/models/{model_id}/allocate", {
        "total_budget": 30000,
        "channel_bounds": {"Meta": [0.2, 0.6], "Google": [0.2, 0.6]},
    }, token=token)
    print("  ", s, b if s != 200 else f"expected_rev={b.get('expected_total_revenue')}")
    assert s == 200, b

    print("8) insights")
    s, b = req("POST", f"/models/{model_id}/insights", {"client_name": "Test Brand"}, token=token)
    print("  ", s, b if s != 200 else f"{len(b)} insights")
    assert s == 200, b

    print("9) report generate (DB-backed)")
    s, b = req("POST", "/reports/generate", {
        "records": records[:6],
        "config": {"name": "e2e-model", "draws": 100, "tune": 100, "chains": 1},
        "client_name": "Test Brand",
        "total_budget": 30000,
        "client_id": client_id,
    }, token=token)
    print("  ", s, b if s != 200 else {k: b.get(k) for k in ("report_id",)})
    assert s in (200, 201), b
    report_id = b["report_id"]

    print("10) report list")
    s, b = req("GET", "/reports", token=token)
    print("  ", s, b if s != 200 else f"{len(b)} reports")
    assert s == 200 and len(b) >= 1, b

    print("11) report PDF")
    s, body = req("GET", f"/reports/{report_id}/pdf", token=token)
    print("  ", s, f"{len(body) if isinstance(body, (bytes, str)) else 0} bytes")
    assert s == 200 and isinstance(body, bytes) and body[:4] == b"%PDF", "pdf failed"

    print("12) model job persisted (GET /models)")
    s, b = req("GET", "/models", token=token)
    print("  ", s, b if s != 200 else f"{len(b)} jobs, status={[j['status'] for j in b]}")
    assert s == 200 and any(j["status"] == "succeeded" for j in b), b

    print("\nALL END-TO-END CHECKS PASSED ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
