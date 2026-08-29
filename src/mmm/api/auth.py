"""Authentication and authorization dependencies for the MMM API.

The platform is **self-contained**: it can issue and verify its own JWTs via
``/api/v1/auth/register`` and ``/api/v1/auth/login`` (a built-in auth provider
stored in the same database). This means the product runs end-to-end with zero
external dependencies.

It is also **Supabase-compatible**: if ``SUPABASE_JWT_SECRET`` is configured,
tokens issued by Supabase Auth are accepted as-is (HS256, ``aud=authenticated``),
and the org/role claims are taken from the JWT ``org_id`` claim (or the
``X-Organization-Id`` header), validated against the ``memberships`` table.

Multi-tenancy flow:
1. :func:`get_current_user` decodes/verifies the Bearer JWT, producing a
   :class:`UserContext` (``sub``, ``email``, ``role``).
2. :func:`get_org_id` resolves the active organization (first membership if no
   claim/header), yielding an :class:`OrganizationContext`.
3. :func:`require_owner` / :func:`require_analyst_or_above` gate endpoints.

In development mode (``ENV=development``) with **no** token, a synthetic
dev context is returned so the API is testable without auth. This is never
active in production (``ENV != development``).
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Annotated, Final, Literal

import jwt
from fastapi import Depends, Header, HTTPException, status
from jwt import InvalidTokenError
from pydantic import BaseModel, ConfigDict

from mmm.config import get_settings
from mmm.db import repo

# --- Constants -----------------------------------------------------------------
SUPABASE_AUDIENCE: Final = "authenticated"
ACCESS_TOKEN_ALGORITHMS: Final = ("HS256",)
ORG_CACHE_TTL_SECONDS: Final = 60
TOKEN_EXPIRE_HOURS: Final = 24

_OWNER_ROLE: Final = "agency_owner"
_ANALYST_ROLES: Final = (_OWNER_ROLE, "analyst")

# --- Models --------------------------------------------------------------------
class UserContext(BaseModel):
    """Authenticated user resolved from the verified JWT."""

    model_config = ConfigDict(frozen=True)

    user_id: str
    email: str | None = None
    token_role: str | None = None
    declared_org_id: str | None = None


class OrganizationContext(UserContext):
    """User plus the active tenant (org id and the user's role in that org)."""

    organization_id: str
    role: Literal["agency_owner", "analyst", "viewer"]


# --- Token issuance (built-in auth provider) ------------------------------------
def create_access_token(*, user_id: str, email: str | None = None, org_id: str, role: str,
                         expires_hours: int = TOKEN_EXPIRE_HOURS) -> str:
    """Mint a signed JWT carrying the org/role claims.

    Uses ``SUPABASE_JWT_SECRET`` when set (so tokens match a Supabase project
    if one is attached), else falls back to ``SECRET_KEY``.
    """
    settings = get_settings()
    secret = settings.supabase_jwt_secret or settings.secret_key
    now = datetime.now(UTC)
    claims = {
        "sub": user_id,
        "email": email,
        "org_id": org_id,
        "role": role,
        "aud": SUPABASE_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=expires_hours)).timestamp()),
    }
    return jwt.encode(claims, secret, algorithm="HS256")


def _decode_access_token(token: str) -> dict:
    """Verify a JWT and return its claims. Raises 401 on any failure."""
    settings = get_settings()
    # Prefer the Supabase secret (allows Supabase-issued tokens); fall back to app secret.
    secrets = [s for s in (settings.supabase_jwt_secret, settings.secret_key) if s]
    if not secrets:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server not configured: no JWT secret available",
        )
    last_err: Exception | None = None
    for secret in secrets:
        try:
            return jwt.decode(
                token,
                secret,
                algorithms=ACCESS_TOKEN_ALGORITHMS,
                audience=SUPABASE_AUDIENCE,
                options={"require": ["exp"]},
            )
        except InvalidTokenError as exc:
            last_err = exc
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    ) from last_err


def _bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )
    return credentials


# --- Org resolution (DB-backed, no asyncpg dependency) --------------------------
_org_cache: dict[tuple[str, str | None], tuple[float, OrganizationContext]] = {}


async def _resolve_org(*, user: UserContext, requested_org_id: str | None, cached: bool) -> OrganizationContext:
    if cached:
        key = (user.user_id, requested_org_id)
        now = time.monotonic()
        hit = _org_cache.get(key)
        if hit is not None and now - hit[0] < ORG_CACHE_TTL_SECONDS:
            return hit[1]

    if requested_org_id:
        membership = await repo.get_membership(organization_id=requested_org_id, user_id=user.user_id)
    else:
        membership = await _first_membership(user.user_id)

    if membership is None:
        if requested_org_id is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization membership")

    ctx = OrganizationContext(
        user_id=user.user_id,
        email=user.email,
        token_role=user.token_role,
        declared_org_id=user.declared_org_id,
        organization_id=membership.organization_id,
        role=membership.role,
    )
    if cached:
        _org_cache[(user.user_id, requested_org_id)] = (time.monotonic(), ctx)
    return ctx


async def _first_membership(user_id: str) -> object | None:
    memberships = await repo.list_memberships(user_id)
    return memberships[0] if memberships else None


# --- Public dependencies -------------------------------------------------------
def get_current_user(authorization: str | None = Header(default=None)) -> UserContext:
    """Authenticate the caller from the Bearer token.

    In development mode (``ENV=development``) with no token, a synthetic dev
    user is returned so the API can be exercised without auth. Production
    always requires a valid token.
    """
    if not authorization and get_settings().env == "development":
        return UserContext(user_id="dev-user", email="dev@local", token_role="authenticated", declared_org_id=None)
    claims = _decode_access_token(_bearer_token(authorization))
    return UserContext(
        user_id=claims["sub"],
        email=claims.get("email"),
        token_role=claims.get("role"),
        declared_org_id=claims.get("org_id"),
    )


async def get_org_id(
    user: UserContext = Depends(get_current_user),
    x_organization_id: Annotated[str | None, Header()] = None,
) -> OrganizationContext:
    """Resolve the active organization context."""
    if user.user_id == "dev-user" and get_settings().env == "development":
        return _dev_context()
    requested_org_id = x_organization_id or user.declared_org_id
    return await _resolve_org(user=user, requested_org_id=requested_org_id, cached=True)


OrgContext = Annotated[OrganizationContext, Depends(get_org_id)]


def require_owner(org_ctx: OrganizationContext = Depends(get_org_id)) -> OrganizationContext:
    if org_ctx.role != _OWNER_ROLE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires agency_owner role")
    return org_ctx


def require_analyst_or_above(org_ctx: OrganizationContext = Depends(get_org_id)) -> OrganizationContext:
    if org_ctx.role not in _ANALYST_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires analyst or agency_owner role")
    return org_ctx


# --- Cache management ----------------------------------------------------------
def clear_org_cache() -> None:
    _org_cache.clear()


# --- Dev-mode bypass -----------------------------------------------------------
def _dev_context() -> OrganizationContext:
    return OrganizationContext(
        organization_id="dev-org",
        user_id="dev-user",
        email="dev@local",
        role=_OWNER_ROLE,
    )
