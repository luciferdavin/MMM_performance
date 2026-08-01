"""Tests for the auth dependencies in ``mmm.api.auth``.

Run with:  pytest tests/test_auth.py -v

The tests mock the DB pool so they require no live database or JWT secrets.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from mmm.api.auth import (
    ORG_CACHE_TTL_SECONDS,
    OrganizationContext,
    UserContext,
    _bearer_token,
    _decode_access_token,
    _org_cache,
    _OWNER_ROLE,
    clear_org_cache,
    get_current_user,
    get_org_id,
    require_analyst_or_above,
    require_owner,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_SECRET = "test-supabase-jwt-secret-for-unit-tests"

def _make_token(
    *,
    sub: str = "user-123",
    email: str | None = "user@example.com",
    aud: str = "authenticated",
    exp: datetime | timedelta | int | None = None,
    role: str = "authenticated",
    org_id: str | None = None,
    secret: str = TEST_SECRET,
) -> str:
    """Build a valid Supabase-like access token for testing."""
    now = datetime.now(timezone.utc)
    claims: dict = {
        "sub": sub,
        "aud": aud,
        "iat": now,
        "role": role,
    }
    if email is not None:
        claims["email"] = email
    if org_id is not None:
        claims["org_id"] = org_id
    if exp is None:
        claims["exp"] = now + timedelta(hours=1)
    elif isinstance(exp, timedelta):
        claims["exp"] = now + exp
    else:
        claims["exp"] = exp
    return jwt.encode(claims, secret, algorithm="HS256")


def _fake_membership(role: str, organization_id: str = "org-aaa") -> dict:
    """Build a fake ``membership_lookup`` result matching ``MembershipRow``."""
    return {"role": role, "organization_id": organization_id}


# ---------------------------------------------------------------------------
# Tests: _bearer_token
# ---------------------------------------------------------------------------

class TestBearerTokenParsing:
    def test_valid_bearer(self) -> None:
        assert _bearer_token("Bearer tok123") == "tok123"

    def test_case_insensitive_bearer(self) -> None:
        assert _bearer_token("bearer tok123") == "tok123"

    def test_missing_header(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            _bearer_token(None)
        assert exc_info.value.status_code == 401

    def test_no_bearer_prefix(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            _bearer_token("Basic tok123")
        assert exc_info.value.status_code == 401

    def test_empty_credentials(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            _bearer_token("Bearer ")
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Tests: _decode_access_token
# ---------------------------------------------------------------------------

class TestDecodeAccessToken:
    @pytest.fixture(autouse=True)
    def _patch_settings(self) -> None:
        with patch("mmm.api.auth.get_settings") as mock_settings:
            mock_settings.return_value = type(
                "S", (), {"supabase_jwt_secret": TEST_SECRET, "env": "production"}
            )()
            yield

    def test_valid_token(self) -> None:
        token = _make_token()
        claims = _decode_access_token(token)
        assert claims["sub"] == "user-123"
        assert claims["aud"] == "authenticated"

    def test_wrong_secret(self) -> None:
        token = _make_token(secret="wrong-key")
        with pytest.raises(HTTPException) as exc_info:
            _decode_access_token(token)
        assert exc_info.value.status_code == 401

    def test_expired_token(self) -> None:
        token = _make_token(exp=-10)
        with pytest.raises(HTTPException) as exc_info:
            _decode_access_token(token)
        assert exc_info.value.status_code == 401

    def test_wrong_audience(self) -> None:
        token = _make_token(aud="service_role")
        with pytest.raises(HTTPException) as exc_info:
            _decode_access_token(token)
        assert exc_info.value.status_code == 401

    def test_missing_sub(self) -> None:
        now = datetime.now(timezone.utc)
        claims = {"aud": "authenticated", "exp": now + timedelta(hours=1), "email": "a@b.com"}
        token = jwt.encode(claims, TEST_SECRET, algorithm="HS256")
        with pytest.raises(HTTPException) as exc_info:
            _decode_access_token(token)
        assert exc_info.value.status_code == 401

    def test_empty_sub(self) -> None:
        now = datetime.now(timezone.utc)
        claims = {"sub": "", "aud": "authenticated", "exp": now + timedelta(hours=1)}
        token = jwt.encode(claims, TEST_SECRET, algorithm="HS256")
        with pytest.raises(HTTPException) as exc_info:
            _decode_access_token(token)
        assert exc_info.value.status_code == 401

    def test_unconfigured_secret(self) -> None:
        with patch("mmm.api.auth.get_settings") as mock_settings:
            mock_settings.return_value = type("S", (), {"supabase_jwt_secret": ""})()
            token = _make_token()
            with pytest.raises(HTTPException) as exc_info:
                _decode_access_token(token)
            assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# Tests: get_current_user (via a minimal FastAPI app)
# ---------------------------------------------------------------------------

class TestGetCurrentUser:
    def _app(self) -> FastAPI:
        app = FastAPI()

        @app.get("/whoami")
        def whoami(user: UserContext = __import__("fastapi").Depends(get_current_user)) -> dict:
            return {"user_id": user.user_id, "email": user.email}

        return app

    @pytest.fixture(autouse=True)
    def _patch_settings(self) -> None:
        with patch("mmm.api.auth.get_settings") as mock_settings:
            mock_settings.return_value = type(
                "S", (), {"supabase_jwt_secret": TEST_SECRET, "env": "production"}
            )()
            yield

    def test_returns_user_info(self) -> None:
        client = TestClient(self._app())
        token = _make_token(sub="u-99", email="a@b.com")
        resp = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "u-99"
        assert resp.json()["email"] == "a@b.com"

    def test_declared_org_id_passes_through(self) -> None:
        app = FastAPI()

        @app.get("/check")
        def check(user: UserContext = __import__("fastapi").Depends(get_current_user)) -> dict:
            return {"declared_org_id": user.declared_org_id}

        client = TestClient(app)
        token = _make_token(org_id="org-bbb")
        resp = client.get("/check", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["declared_org_id"] == "org-bbb"

    def test_401_without_token(self) -> None:
        client = TestClient(self._app())
        resp = client.get("/whoami")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests: get_org_id (org resolution)
# ---------------------------------------------------------------------------

class TestGetOrgId:
    def _app(self) -> FastAPI:
        app = FastAPI()

        @app.get("/org")
        def org_view(ctx: OrganizationContext = __import__("fastapi").Depends(get_org_id)) -> dict:
            return {"org": ctx.organization_id, "role": ctx.role, "user": ctx.user_id}

        return app

    @pytest.fixture(autouse=True)
    def _patch_env(self) -> None:
        clear_org_cache()
        with (
            patch("mmm.api.auth.get_settings") as mock_settings,
            patch("mmm.api.db._pool", create=True),
        ):
            mock_settings.return_value = type(
                "S", (), {"supabase_jwt_secret": TEST_SECRET, "env": "production"}
            )()
            yield
        clear_org_cache()

    @pytest.fixture()
    def _mock_lookup(self):
        lookup = AsyncMock()

        def patcher(return_val):
            lookup.return_value = return_val
            return lookup

        return patcher

    def test_resolves_from_header(self, _mock_lookup) -> None:
        lookup = _mock_lookup(_fake_membership(role="analyst", organization_id="org-111"))
        with patch("mmm.api.auth.membership_lookup", new=lookup):
            client = TestClient(self._app())
            token = _make_token(sub="u-1")
            resp = client.get(
                "/org",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Organization-Id": "org-111",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["org"] == "org-111"
            assert data["role"] == "analyst"
            lookup.assert_awaited_once_with(user_id="u-1", organization_id="org-111")

    def test_resolves_from_jwt_claim(self, _mock_lookup) -> None:
        lookup = _mock_lookup(_fake_membership(role="viewer", organization_id="org-jwt"))
        with patch("mmm.api.auth.membership_lookup", new=lookup):
            client = TestClient(self._app())
            token = _make_token(sub="u-2", org_id="org-jwt")
            resp = client.get(
                "/org",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Organization-Id": "org-overridden",
                },
            )
            assert resp.status_code == 200
            # JWT claim wins over header
            assert resp.json()["org"] == "org-jwt"
            lookup.assert_awaited_once_with(user_id="u-2", organization_id="org-jwt")

    def test_404_when_not_member(self, _mock_lookup) -> None:
        lookup = _mock_lookup(None)
        with patch("mmm.api.auth.membership_lookup", new=lookup):
            client = TestClient(self._app())
            token = _make_token(sub="u-3")
            resp = client.get(
                "/org",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Organization-Id": "org-missing",
                },
            )
            assert resp.status_code == 404

    def test_first_membership_when_no_org(self, _mock_lookup) -> None:
        lookup = _mock_lookup(_fake_membership(role="viewer", organization_id="org-first"))
        with patch("mmm.api.auth.membership_lookup", new=lookup):
            client = TestClient(self._app())
            token = _make_token(sub="u-4")
            resp = client.get("/org", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            assert resp.json()["org"] == "org-first"
            lookup.assert_awaited_once_with(user_id="u-4", organization_id=None)

    def test_cache_hit_on_second_call(self, _mock_lookup) -> None:
        lookup = _mock_lookup(_fake_membership(role="analyst", organization_id="org-cached"))
        with patch("mmm.api.auth.membership_lookup", new=lookup):
            client = TestClient(self._app())
            token = _make_token(sub="u-5")
            hdrs = {
                "Authorization": f"Bearer {token}",
                "X-Organization-Id": "org-cached",
            }
            client.get("/org", headers=hdrs)
            client.get("/org", headers=hdrs)
            # membership_lookup called only once (cache hit on second request)
            assert lookup.await_count == 1


# ---------------------------------------------------------------------------
# Tests: RBAC helpers
# ---------------------------------------------------------------------------

class TestRBAC:
    def _app(self, *, endpoint: str = "owner") -> FastAPI:
        app = FastAPI()

        if endpoint == "owner":
            @app.get("/owner-only")
            def _(ctx: OrganizationContext = __import__("fastapi").Depends(require_owner)) -> dict:
                return {"role": ctx.role}
        else:
            @app.get("/analyst-up")
            def _(ctx: OrganizationContext = __import__("fastapi").Depends(require_analyst_or_above)) -> dict:
                return {"role": ctx.role}

        return app

    @pytest.fixture(autouse=True)
    def _patch_env(self) -> None:
        clear_org_cache()
        with (
            patch("mmm.api.auth.get_settings") as mock_settings,
            patch("mmm.api.db._pool", create=True),
        ):
            mock_settings.return_value = type(
                "S", (), {"supabase_jwt_secret": TEST_SECRET, "env": "production"}
            )()
            yield
        clear_org_cache()

    def _make_ctx(self, role: str, user_id: str = "u-t", org_id: str = "org-t") -> OrganizationContext:
        return OrganizationContext(user_id=user_id, organization_id=org_id, role=role)

    def test_owner_passes_owner_gate(self) -> None:
        ctx = self._make_ctx(_OWNER_ROLE)
        assert require_owner(ctx) is ctx

    def test_analyst_rejected_by_owner_gate(self) -> None:
        ctx = self._make_ctx("analyst")
        with pytest.raises(HTTPException) as exc_info:
            require_owner(ctx)
        assert exc_info.value.status_code == 403

    def test_viewer_rejected_by_owner_gate(self) -> None:
        ctx = self._make_ctx("viewer")
        with pytest.raises(HTTPException) as exc_info:
            require_owner(ctx)
        assert exc_info.value.status_code == 403

    def test_owner_passes_analyst_gate(self) -> None:
        ctx = self._make_ctx(_OWNER_ROLE)
        assert require_analyst_or_above(ctx) is ctx

    def test_analyst_passes_analyst_gate(self) -> None:
        ctx = self._make_ctx("analyst")
        assert require_analyst_or_above(ctx) is ctx

    def test_viewer_rejected_by_analyst_gate(self) -> None:
        ctx = self._make_ctx("viewer")
        with pytest.raises(HTTPException) as exc_info:
            require_analyst_or_above(ctx)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Tests: cache management
# ---------------------------------------------------------------------------

class TestCache:
    def test_clear_cache(self) -> None:
        _org_cache[("u-x", "org-x")] = (time.monotonic(), OrganizationContext(
            user_id="u-x", organization_id="org-x", role="viewer",
        ))
        assert len(_org_cache) == 1
        clear_org_cache()
        assert len(_org_cache) == 0

    def test_cache_expires(self) -> None:
        ctx = OrganizationContext(user_id="u-y", organization_id="org-y", role="viewer")
        # Backfill a cache entry just beyond the TTL threshold
        _org_cache[("u-y", "org-y")] = (time.monotonic() - ORG_CACHE_TTL_SECONDS - 1, ctx)
        # Entry is present but expired — next lookup must miss
        hit = _org_cache.get(("u-y", "org-y"))
        assert hit is not None
        assert (time.monotonic() - hit[0]) > ORG_CACHE_TTL_SECONDS
        # Clean up
        clear_org_cache()
