from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..auth import require_api_key
from ..models import Company
from ..schemas import CompanyOut, CompanyUpdate

router = APIRouter(prefix="/companies", tags=["companies"], dependencies=[Depends(require_api_key)])


@router.get("", response_model=list[CompanyOut])
async def list_companies(session: AsyncSession = Depends(get_session)):
    companies = (await session.execute(select(Company))).scalars().all()
    return companies


@router.patch("/{company_id}", response_model=CompanyOut)
async def update_company(
    company_id: str,
    payload: CompanyUpdate,
    session: AsyncSession = Depends(get_session),
):
    company = (await session.execute(select(Company).where(Company.id == company_id))).scalars().first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    company.enabled = payload.enabled
    await session.commit()
    await session.refresh(company)
    return company
