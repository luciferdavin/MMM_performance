"""Client CRUD endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from mmm.api.auth import OrganizationContext, get_org_id
from mmm.db import repo

router = APIRouter(prefix="/clients", tags=["clients"])


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
    organization_id = ctx.organization_id
    clients = await repo.list_clients(organization_id)
    return [ClientOut(id=c.id, organization_id=c.organization_id, name=c.name, slug=c.slug) for c in clients]


@router.post("", response_model=ClientOut, status_code=201)
async def create_client(body: ClientCreate, ctx: OrganizationContext = Depends(get_org_id)):
    organization_id = ctx.organization_id
    cid = uuid.uuid4().hex[:12]
    slug = body.slug or body.name.lower().replace(" ", "-")
    client = await repo.create_client(
        client_id=cid,
        organization_id=organization_id,
        name=body.name,
        slug=slug,
    )
    return ClientOut(id=client.id, organization_id=client.organization_id, name=client.name, slug=client.slug)


@router.get("/{client_id}", response_model=ClientOut)
async def get_client(client_id: str, ctx: OrganizationContext = Depends(get_org_id)):
    organization_id = ctx.organization_id
    client = await repo.get_client(client_id)
    if not client or client.organization_id != organization_id:
        raise HTTPException(404, "client not found")
    return ClientOut(id=client.id, organization_id=client.organization_id, name=client.name, slug=client.slug)


@router.delete("/{client_id}", status_code=204)
async def delete_client(client_id: str, ctx: OrganizationContext = Depends(get_org_id)):
    organization_id = ctx.organization_id
    client = await repo.get_client(client_id)
    if not client or client.organization_id != organization_id:
        raise HTTPException(404, "client not found")
    await repo.delete_client(client_id)
