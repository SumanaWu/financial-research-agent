"""Owner-scoped company research endpoints."""

from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.server.services.company_research import research_result, resolve_company
from src.server.utils.api import CurrentUserId

router = APIRouter(prefix="/api/v1", tags=["Company research"])


class ResolveRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9.\-]+$")
    identity: str = Field(min_length=3, max_length=200)


@router.post("/company-research/resolve")
async def resolve(request: ResolveRequest, user_id: CurrentUserId):
    return await resolve_company(request)


@router.get("/threads/{thread_id}/company-research")
async def result(thread_id: UUID, user_id: CurrentUserId):
    return await research_result(str(thread_id), user_id, acquire=True)
