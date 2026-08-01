"""Database access layer for the MMM API.

Thin asyncpg wrapper used by the auth dependencies to resolve the current
user's organization and role from the ``memberships`` table. Ownership of the
asyncpg pool lifecycle (startup/shutdown) belongs to the application wiring in
``main.py`` via ``init_db_pool`` / ``close_db_pool``; the connection is a
read-only pool pointing at the Postgres database behind Supabase. RLS is
bypassed deliberately for org/role lookups (the pool connects with the
service role), because the auth dependency itself IS the enforcement layer
(see docs/02-trd.md §5.1 and docs/05-backend-schema.md §4). Use the Supabase
service role connection string (``DATABASE_URL``) only with this trusted pool;
never expose it to clients.

TODO(backend): the membership resolver only needs ``memberships`` plus the
``organizations`` row for 404 semantics. If the deployment uses the Supabase
HTTP API (postgrest) instead of a direct Postgres connection, replace
``membership_lookup`` with a ``supabase`` client call while keeping the same
return shape (``OrganizationContext`` in ``auth.py``).
"""

from __future__ import annotations

from typing import TypedDict

import asyncpg
from asyncpg import Pool

_pool: Pool | None = None


class MembershipRow(TypedDict):
    organization_id: str
    role: str


async def init_db_pool(database_url: str, *, min_size: int = 1, max_size: int = 10) -> Pool:
    """Create (or reuse) the read-only connection pool used by auth lookups.

    Call once at FastAPI startup; store the returned pool with
    :func:`set_db_pool` (or rely on the module-level default for tests).
    """
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(dsn=database_url, min_size=min_size, max_size=max_size)
    return _pool


async def close_db_pool() -> None:
    """Close the auth lookup pool. Call once at FastAPI shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def set_db_pool(pool: Pool | None) -> None:
    """Override the pool used by :func:`membership_lookup` (dependency injection / tests)."""
    global _pool
    _pool = pool


async def membership_lookup(*, user_id: str, organization_id: str | None) -> MembershipRow | None:
    """Resolve a user's membership in an organization.

    Returns ``None`` when the user is not a member of ``organization_id``
    (or, if ``organization_id`` is None, when the user has no memberships).
    """
    pool = _pool
    if pool is None:
        raise RuntimeError("DB pool not initialized — call init_db_pool() at app startup")

    if organization_id is not None:
        query = """
            SELECT organization_id, role
            FROM public.memberships
            WHERE user_id = $1::uuid
              AND organization_id = $2::uuid
            LIMIT 1
        """
        params: tuple[str, str] = (user_id, organization_id)
    else:
        query = """
            SELECT organization_id, role
            FROM public.memberships
            WHERE user_id = $1::uuid
            ORDER BY created_at ASC
            LIMIT 1
        """
        params = (user_id,)

    row = await pool.fetchrow(query, *params)
    if row is None:
        return None
    return {"organization_id": str(row["organization_id"]), "role": str(row["role"])}
