"""Authentication and authorization dependencies for the MMM API.

Enforces the multi-tenant security model described in ``docs/02-trd.md``
(§5 Authentication and Authorization) on top of Supabase Auth and the
``memberships`` table (``docs/05-backend-schema.md`` §3.3 / §4 RLS).

Flow:
1. :func:`get_current_user` decodes and verifies the Supabase JWT from the
   ``Authorization: Bearer <token>`` header (HS256, ``aud="authenticated"``),
   producing a :class:`UserContext` (``sub``, ``email``, token ``role``).
2. :func:`get_org_id` resolves the active organization from the JWT
   ``org_id`` claim if present, else from the ``X-Organization-Id`` header —
   and cross-checks both against the ``memberships`` table (the header value
   is never trusted on its own). Yields an :class:`OrganizationContext`
   carrying the org id and the user's real role in that org.
3. :func:`require_owner` / :func:`require_analyst_or_above` gate the endpoint
   on the org role.

Dependency-injectable via ``Depends(...)``:

    from fastapi import APIRouter, Depends
    from mmm.api.auth import require_analyst_or_above, require_owner

    router = APIRouter()

    @router.post("/clients")
    def create_client(ctx=Depends(require_analyst_or_above)):
        ...

    @router.delete("/clients/{client_id}")
    def delete_client(ctx=Depends(require_owner)):
        ...

Error mapping: 401 missing/invalid token · 403 insufficient role ·
404 organization not found (or the user has no membership).

A 60-second TTL cache keyed by (user_id, org_id) avoids a DB hit on every
request (docs/02-trd.md §5.3). Org role changes take effect within that
window. Module state is only ever assigned at import time (immutable by
contract); individual lookups are read-only.
"""

from __future__ import annotations

import time
from typing import Annotated, Final, Literal

import jwt
from fastapi import Depends, Header, HTTPException, status
from jwt import InvalidTokenError
from pydantic import BaseModel, ConfigDict

from mmm.api.db import membership_lookup
from mmm.config import get_settings

# --- Constants -----------------------------------------------------------------

SUPABASE_AUDIENCE: Final = "authenticated"
ACCESS_TOKEN_ALGORITHMS: Final = ("HS256",)
ORG_CACHE_TTL_SECONDS: Final = 60

#: Role a user must hold to pass :func:`require_owner`.
_OWNER_ROLE: Final = "agency_owner"
#: Roles accepted by :func:`require_analyst_or_above` (owner or analyst).
_ANALYST_ROLES: Final = (_OWNER_ROLE, "analyst")

# --- Models --------------------------------------------------------------------

class UserContext(BaseModel):
    """Authenticated Supabase user resolved from the verified JWT."""

    model_config = ConfigDict(frozen=True)

    user_id: str
    email: str | None = None
    # The JWT ``role`` claim is Supabase's auth-role (always "authenticated"
    # for access tokens) — NOT the tenant ``memberships.role``.
    token_role: str | None = None
    # Optional org_id claim — set by a Supabase auth hook when the user
    # switches active org on the frontend. If present the ``get_org_id``
    # dependency uses it in preference to the ``X-Organization-Id`` header;
    # either value is still validated against the memberships table.
    declared_org_id: str | None = None


class OrganizationContext(UserContext):
    """User plus the active tenant (org id and the user's role in that org)."""

    organization_id: str
    role: Literal["agency_owner", "analyst", "viewer"]


# --- Token parsing -------------------------------------------------------------

def _decode_access_token(token: str) -> dict:
    """Verify a Supabase access token and return its validated claims.

    Raises:
        HTTPException(401): token is expired, signed with the wrong key,
            has an unexpected audience, or is otherwise malformed.
    """
    settings = get_settings()
    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server not configured: SUPABASE_JWT_SECRET is unset",
        )
    try:
        claims = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=ACCESS_TOKEN_ALGORITHMS,
            audience=SUPABASE_AUDIENCE,
            options={"require": ["exp"]},
        )
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc
    if not isinstance(claims.get("sub"), str) or not claims["sub"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return claims


def _bearer_token(authorization: str | None) -> str:
    """Extract the JWT from an ``Authorization`` header value."""
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


# --- Organization resolution cache ----------------------------------------------

_org_cache: dict[tuple[str, str | None], tuple[float, OrganizationContext]] = {}


async def _resolve_org(
    *,
    user: UserContext,
    requested_org_id: str | None,
    cached: bool,
) -> OrganizationContext:
    """Resolve the active org/role for a user, using a TTL cache when enabled.

    ``requested_org_id`` of ``None`` means "any of my orgs" (first membership).
    A ``requested_org_id`` that does not resolve to a membership is treated as
    an unknown organization (404) — it is not silently swapped for the user's
    first org, because the header/claim explicitly named a tenant.
    """
    if cached:
        key = (user.user_id, requested_org_id)
        now = time.monotonic()
        hit = _org_cache.get(key)
        if hit is not None and now - hit[0] < ORG_CACHE_TTL_SECONDS:
            return hit[1]

    membership = await membership_lookup(
        user_id=user.user_id,
        organization_id=requested_org_id,
    )
    if membership is None:
        if requested_org_id is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No organization membership",
        )

    ctx = OrganizationContext(
        **user.model_dump(),
        organization_id=membership["organization_id"],
        role=membership["role"],
    )
    if cached:
        _org_cache[(user.user_id, requested_org_id)] = (time.monotonic(), ctx)
    return ctx


# --- Public dependencies --------------------------------------------------------

def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> UserContext:
    """Dependency: authenticate the caller from the Bearer token."""
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
    """Dependency: resolve the active organization context.

    Strategy (docs/02-trd.md §5.1 — never trust client-sent org claims):

    1. JWT ``org_id`` claim (highest precedence — set by a Supabase auth hook;
       the claim is cryptographically verified so it cannot be forged by the
       caller).
    2. ``X-Organization-Id`` header (falls back here when the token does not
       carry an org claim).
    3. ``None`` — if neither is present the user's first membership is used.

    In all cases the org is validated against the ``memberships`` table via
    :func:`membership_lookup`, so a forged or stale header cannot escalate
    access.  The lookup result is cached for 60 seconds (see
    ``ORG_CACHE_TTL_SECONDS``).
    """
    requested_org_id = user.declared_org_id or x_organization_id
    return await _resolve_org(user=user, requested_org_id=requested_org_id, cached=True)


#: FastAPI alias: inject as ``ctx: OrgContext = Depends(get_org_id)``.
OrgContext = Annotated[OrganizationContext, Depends(get_org_id)]


def require_owner(org_ctx: OrganizationContext = Depends(get_org_id)) -> OrganizationContext:
    """Dependency: only an ``agency_owner`` may proceed."""
    if org_ctx.role != _OWNER_ROLE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires agency_owner role",
        )
    return org_ctx


def require_analyst_or_above(
    org_ctx: OrganizationContext = Depends(get_org_id),
) -> OrganizationContext:
    """Dependency: ``agency_owner`` or ``analyst`` may proceed."""
    if org_ctx.role not in _ANALYST_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires analyst or agency_owner role",
        )
    return org_ctx


# --- Cache management -------------------------------------------------------------

def clear_org_cache() -> None:
    """Drop all cached org resolutions (call after membership role changes)."""
    _org_cache.clear()
