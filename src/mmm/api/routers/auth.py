"""Auth endpoints: self-contained register/login issuing signed JWTs.

These give the platform a working auth path with **no external provider**.
Tokens are accepted on every other endpoint via ``mmm.api.auth``. When a
Supabase project is configured (``SUPABASE_JWT_SECRET``), those tokens are
accepted too.
"""

from __future__ import annotations

import hashlib
import secrets

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from mmm.api.auth import OrgContext, create_access_token
from mmm.db import repo

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Password hashing (salted SHA-256 — sufficient for local/HMAC auth; swap for
# argon2/bcrypt in high-security deployments).
# ---------------------------------------------------------------------------
def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return digest, salt


def verify_password(password: str, salt: str, expected: str) -> bool:
    digest, _ = _hash_password(password, salt)
    return secrets.compare_digest(digest, expected)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str | None = None
    organization_name: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    org_id: str
    role: str
    email: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest):
    existing = await repo.get_user_by_email(body.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    org_name = body.organization_name or f"{body.email.split('@')[0]}'s Org"
    slug = org_name.lower().replace(" ", "-").replace("'", "")[:120] or "org"
    # ensure unique slug
    base_slug, n = slug, 1
    while await repo.get_organization_by_slug(slug):
        slug = f"{base_slug}-{n}"
        n += 1
    org = await repo.create_organization(name=org_name, slug=slug)

    digest, salt = _hash_password(body.password)
    user = await repo.create_user(
        email=body.email,
        hashed_password=f"{salt}:{digest}",
        full_name=body.name,
    )
    await repo.create_membership(organization_id=org.id, user_id=user.id, role="agency_owner")

    token = create_access_token(user_id=user.id, email=user.email, org_id=org.id, role="agency_owner")
    return TokenResponse(
        access_token=token, user_id=user.id, org_id=org.id, role="agency_owner", email=user.email
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    user = await repo.get_user_by_email(body.email)
    if not user or not user.hashed_password or ":" not in user.hashed_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    salt, expected = user.hashed_password.split(":", 1)
    if not verify_password(body.password, salt, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    memberships = await repo.list_memberships(user.id)
    if not memberships:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization membership")
    m = memberships[0]
    token = create_access_token(user_id=user.id, email=user.email, org_id=m.organization_id, role=m.role)
    return TokenResponse(
        access_token=token, user_id=user.id, org_id=m.organization_id, role=m.role, email=user.email
    )


@router.get("/me", response_model=TokenResponse)
async def me(ctx: OrgContext):
    return TokenResponse(
        access_token="", user_id=ctx.user_id, org_id=ctx.organization_id, role=ctx.role, email=ctx.email
    )


__all__ = ["router"]
