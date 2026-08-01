"""Client CRUD endpoints."""
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from mmm.api.auth import OrganizationContext, UserContext, get_current_user, get_org_id

router = APIRouter(prefix="/clients", tags=["clients"])

# In-memory store for dev; replace with DB queries when wired.
_clients: dict[str, dict] = {}

class ClientCreate(BaseModel):
    name: str
    slug: str | None = None

class ClientOut(BaseModel):
    id: str
    organization_id: str
    name: str
    slug: str

@router.get("", response_model=list[ClientOut])
async def list_clients(ctx: OrganizationContext = Depends(get_org_id)):
    return [c for c in _clients.values() if c["organization_id"] == ctx.organization_id]

@router.post("", response_model=ClientOut, status_code=201)
async def create_client(body: ClientCreate, ctx: OrganizationContext = Depends(get_org_id)):
    cid = uuid.uuid4().hex[:12]
    slug = body.slug or body.name.lower().replace(" ", "-")
    client = {"id": cid, "organization_id": ctx.organization_id, "name": body.name, "slug": slug}
    _clients[cid] = client
    return client

@router.get("/{client_id}", response_model=ClientOut)
async def get_client(client_id: str, ctx: OrganizationContext = Depends(get_org_id)):
    c = _clients.get(client_id)
    if not c or c["organization_id"] != ctx.organization_id:
        raise HTTPException(404, "client not found")
    return c

@router.delete("/{client_id}", status_code=204)
async def delete_client(client_id: str, ctx: OrganizationContext = Depends(get_org_id)):
    c = _clients.pop(client_id, None)
    if not c or c["organization_id"] != ctx.organization_id:
        raise HTTPException(404, "client not found")
