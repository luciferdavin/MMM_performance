"""Tests for the auth dependencies in ``mmm.api.auth``.

Covers JWT creation/verification, org resolution against the DB-backed
membership layer, and RBAC gates. Uses a real on-disk SQLite database
(isolated via DATABASE_URL) seeded with an org + user + membership.
"""

from __future__ import annotations

import os
import tempfile
import time
from unittest.mock import patch

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from mmm.api.auth import (
    ORG_CACHE_TTL_SECONDS,
    OrganizationContext,
    UserContext,
    _bearer_token,
    create_access_token,
    get_current_user,
    get_org_id,
    require_analyst_or_above,
    require_owner,
)
from mmm.db import repo
from mmm.db.session import close_db, init_db

TEST_SECRET = "test-jwt-secret-for-unit-tests-0123456789"


def _settings(secret=TEST_SECRET, bypass=False):
    return type(
        "S",
        (),
        {
            "supabase_jwt_secret": secret,
            "secret_key": "k",
            "env": "production",
            "auth_bypass_when_no_secret": bypass,
        },
    )()


@pytest.fixture()
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{path}"
    yield path
    os.environ.pop("DATABASE_URL", None)
    try:
        os.remove(path)
    except OSError:
        pass


@pytest.fixture()
async def seeded_db(db_path):
    """Fresh SQLite DB seeded with org/user/membership."""
    await init_db(database_url=f"sqlite+aiosqlite:///{db_path}")
    suffix = os.urandom(4).hex()
    org = await repo.create_organization(name="Acme", slug=f"acme-{suffix}")
    user = await repo.create_user(email="user@example.com", user_id="u-1")
    await repo.create_membership(organization_id=org.id, user_id=user.id, role="analyst")
    owner_org = await repo.create_organization(name="OwnerCo", slug=f"ownerco-{suffix}")
    await repo.create_membership(organization_id=owner_org.id, user_id=user.id, role="agency_owner")
    yield {"org": org, "user": user, "owner_org": owner_org}
    await close_db()


# ---------------------------------------------------------------------------
# _bearer_token
# ---------------------------------------------------------------------------
class TestBearerTokenParsing:
    def test_valid_bearer(self):
        assert _bearer_token("Bearer tok123") == "tok123"

    def test_case_insensitive(self):
        assert _bearer_token("bearer tok123") == "tok123"

    def test_missing_header(self):
        with pytest.raises(Exception) as exc:
            _bearer_token(None)
        assert exc.value.status_code == 401

    def test_no_prefix(self):
        with pytest.raises(Exception) as exc:
            _bearer_token("Basic tok123")
        assert exc.value.status_code == 401

    def test_empty_credentials(self):
        with pytest.raises(Exception) as exc:
            _bearer_token("Bearer ")
        assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# Token create + decode
# ---------------------------------------------------------------------------
class TestTokenLifecycle:
    def test_create_and_decode(self):
        with patch("mmm.api.auth.get_settings") as ms:
            ms.return_value = _settings()
            tok = create_access_token(user_id="u-1", email="e@x.com", org_id="org-1", role="analyst")
            claims = jwt.decode(tok, TEST_SECRET, algorithms=["HS256"], audience="authenticated")
            assert claims["sub"] == "u-1"
            assert claims["org_id"] == "org-1"

    def test_wrong_secret(self):
        with patch("mmm.api.auth.get_settings") as ms:
            ms.return_value = _settings()
            tok = create_access_token(user_id="u", org_id="o", role="analyst")
        with patch("mmm.api.auth.get_settings") as ms:
            ms.return_value = _settings(secret="other-secret-other-secret-0123456789")
            with pytest.raises(jwt.InvalidTokenError):
                jwt.decode(
                    tok,
                    "other-secret-other-secret-0123456789",
                    algorithms=["HS256"],
                    audience="authenticated",
                )


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------
class TestGetCurrentUser:
    def _app(self):
        app = FastAPI()

        @app.get("/whoami")
        def whoami(user: UserContext = Depends(get_current_user)):
            return {"user_id": user.user_id, "email": user.email}

        return app

    def test_returns_user_info(self):
        with patch("mmm.api.auth.get_settings") as ms:
            ms.return_value = _settings()
            tok = create_access_token(user_id="u-99", email="a@b.com", org_id="o", role="analyst")
            client = TestClient(self._app())
            resp = client.get("/whoami", headers={"Authorization": f"Bearer {tok}"})
            assert resp.status_code == 200
            assert resp.json()["user_id"] == "u-99"

    def test_401_without_token(self):
        with patch("mmm.api.auth.get_settings") as ms:
            ms.return_value = _settings()
            client = TestClient(self._app())
            resp = client.get("/whoami")
            assert resp.status_code == 401


# ---------------------------------------------------------------------------
# get_org_id (DB-backed)
# ---------------------------------------------------------------------------
class TestGetOrgId:
    def _app(self):
        app = FastAPI()

        @app.get("/org")
        def org_view(ctx: OrganizationContext = Depends(get_org_id)):
            return {"org": ctx.organization_id, "role": ctx.role, "user": ctx.user_id}

        return app

    @pytest.mark.asyncio
    async def test_resolves_from_jwt_claim(self, seeded_db):
        with patch("mmm.api.auth.get_settings") as ms:
            ms.return_value = _settings()
            tok = create_access_token(user_id="u-1", email="user@example.com", org_id=seeded_db["org"].id, role="analyst")
            client = TestClient(self._app())
            resp = client.get("/org", headers={"Authorization": f"Bearer {tok}"})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["org"] == seeded_db["org"].id
        assert data["role"] == "analyst"

    @pytest.mark.asyncio
    async def test_header_overrides_jwt_claim(self, seeded_db):
        with patch("mmm.api.auth.get_settings") as ms:
            ms.return_value = _settings()
            tok = create_access_token(user_id="u-1", email="user@example.com", org_id=seeded_db["owner_org"].id, role="agency_owner")
            client = TestClient(self._app())
            resp = client.get(
                "/org",
                headers={"Authorization": f"Bearer {tok}", "X-Organization-Id": seeded_db["org"].id},
            )
        assert resp.json()["org"] == seeded_db["org"].id

    @pytest.mark.asyncio
    async def test_404_when_not_member(self, seeded_db):
        with patch("mmm.api.auth.get_settings") as ms:
            ms.return_value = _settings()
            tok = create_access_token(user_id="u-1", email="user@example.com", org_id="nonexistent", role="analyst")
            client = TestClient(self._app())
            resp = client.get(
                "/org",
                headers={"Authorization": f"Bearer {tok}", "X-Organization-Id": "nonexistent"},
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_first_membership_when_no_org(self, seeded_db):
        with patch("mmm.api.auth.get_settings") as ms:
            ms.return_value = _settings()
            tok = create_access_token(user_id="u-1", email="user@example.com", org_id=None, role="analyst")
            client = TestClient(self._app())
            resp = client.get("/org", headers={"Authorization": f"Bearer {tok}"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["org"] == seeded_db["org"].id


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------
class TestRBAC:
    def _make_ctx(self, role, org_id="org-t"):
        return OrganizationContext(user_id="u", organization_id=org_id, role=role)

    def test_owner_passes_owner_gate(self):
        ctx = self._make_ctx("agency_owner")
        assert require_owner(ctx) is ctx

    def test_analyst_rejected_by_owner(self):
        ctx = self._make_ctx("analyst")
        with pytest.raises(Exception) as exc:
            require_owner(ctx)
        assert exc.value.status_code == 403

    def test_owner_passes_analyst(self):
        assert require_analyst_or_above(self._make_ctx("agency_owner")).role == "agency_owner"

    def test_analyst_passes_analyst(self):
        assert require_analyst_or_above(self._make_ctx("analyst")).role == "analyst"

    def test_viewer_rejected_by_analyst(self):
        with pytest.raises(Exception) as exc:
            require_analyst_or_above(self._make_ctx("viewer"))
        assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
class TestCache:
    def test_clear(self):
        from mmm.api.auth import _org_cache, clear_org_cache

        clear_org_cache()
        _org_cache[("u", "o")] = (time.monotonic(), OrganizationContext(user_id="u", organization_id="o", role="viewer"))
        assert len(_org_cache) == 1
        clear_org_cache()
        assert len(_org_cache) == 0

    def test_expires(self):
        from mmm.api.auth import _org_cache, clear_org_cache

        ctx = OrganizationContext(user_id="u", organization_id="o", role="viewer")
        _org_cache[("u", "o")] = (time.monotonic() - ORG_CACHE_TTL_SECONDS - 1, ctx)
        hit = _org_cache.get(("u", "o"))
        assert (time.monotonic() - hit[0]) > ORG_CACHE_TTL_SECONDS
        clear_org_cache()
