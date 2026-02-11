"""社会保険料率管理API"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.api.deps import require_roles
from app.models.company import User
from app.models.insurance import InsuranceRate
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/insurance-rates", tags=["社会保険料率"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class InsuranceRateCreate(BaseModel):
    insurance_type: str
    valid_from: date
    valid_to: date | None = None
    prefecture: str | None = None
    business_type: str | None = None
    employee_rate: Decimal
    employer_rate: Decimal
    care_insurance_rate: Decimal | None = None


class InsuranceRateUpdate(BaseModel):
    insurance_type: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    prefecture: str | None = None
    business_type: str | None = None
    employee_rate: Decimal | None = None
    employer_rate: Decimal | None = None
    care_insurance_rate: Decimal | None = None


class InsuranceRateResponse(BaseModel):
    id: int
    company_id: int | None = None
    insurance_type: str
    valid_from: date
    valid_to: date | None = None
    prefecture: str | None = None
    business_type: str | None = None
    employee_rate: Decimal
    employer_rate: Decimal
    care_insurance_rate: Decimal | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedResponse[InsuranceRateResponse])
async def list_insurance_rates(
    insurance_type: str | None = None,
    prefecture: str | None = None,
    page: int = 1,
    limit: int = 50,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """社会保険料率一覧取得"""
    query = select(InsuranceRate).where(
        InsuranceRate.company_id == user.company_id
    )

    if insurance_type is not None:
        query = query.where(InsuranceRate.insurance_type == insurance_type)
    if prefecture is not None:
        query = query.where(InsuranceRate.prefecture == prefecture)

    # 総件数
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # ページネーション
    query = (
        query.order_by(InsuranceRate.valid_from.desc(), InsuranceRate.id)
        .offset((page - 1) * limit)
        .limit(limit)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[InsuranceRateResponse.model_validate(r) for r in items],
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit,
    )


@router.post("", response_model=InsuranceRateResponse, status_code=status.HTTP_201_CREATED)
async def create_insurance_rate(
    body: InsuranceRateCreate,
    user: User = Depends(require_roles("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """社会保険料率作成"""
    rate = InsuranceRate(
        company_id=user.company_id,
        **body.model_dump(),
    )
    db.add(rate)
    await db.flush()
    return InsuranceRateResponse.model_validate(rate)


@router.put("/{rate_id}", response_model=InsuranceRateResponse)
async def update_insurance_rate(
    rate_id: int,
    body: InsuranceRateUpdate,
    user: User = Depends(require_roles("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """社会保険料率更新"""
    result = await db.execute(
        select(InsuranceRate).where(
            InsuranceRate.id == rate_id,
            InsuranceRate.company_id == user.company_id,
        )
    )
    rate = result.scalar_one_or_none()
    if not rate:
        raise HTTPException(status_code=404, detail="保険料率が見つかりません")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rate, key, value)

    await db.flush()
    return InsuranceRateResponse.model_validate(rate)
