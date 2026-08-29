"""Verify the PDF report endpoint end-to-end (no PyMC fit needed)."""
import asyncio
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8012/api/v1"


def req(method, path, body=None, token=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            ctype = resp.headers.get("Content-Type", "")
            body_b = resp.read()
            if "application/json" in ctype:
                return resp.status, json.loads(body_b.decode())
            return resp.status, body_b
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


async def main():
    from mmm.db.session import init_db
    from mmm.db import repo

    # 1) register via API to get a real org + token
    import time as _t
    s, b = req("POST", "/auth/register", {
        "email": f"pdf+{int(_t.time())}@acme.test", "password": "pw-12345", "name": "PDF",
        "organization_name": "PDF Org",
    })
    print("register:", s)
    assert s in (200, 201), b
    token = b["access_token"]
    org_id = b["org_id"]

    # 2) insert a report row directly under that org
    await init_db()
    rep = await repo.create_report(
        organization_id=org_id,
        client_id=None,
        model_job_id=None,
        client_name="PDF Client",
        content={"markdown": "# MMM Report: PDF Client\n\n## Channel Contributions\n\n- **Google**: ROAS 1.9x\n- **Meta**: ROAS 0.3x\n"},
    )
    print("inserted report:", rep.id)

    # 3) fetch the PDF over HTTP
    s, body = req("GET", f"/reports/{rep.id}/pdf", token=token)
    print("pdf status:", s, "bytes:", len(body) if isinstance(body, (bytes, str)) else 0)
    assert s == 200, "pdf failed"
    assert isinstance(body, bytes) and body[:4] == b"%PDF", "not a PDF"
    print("PDF magic bytes OK ✅")
    return 0


if __name__ == "__main__":
    asyncio.run(main())
