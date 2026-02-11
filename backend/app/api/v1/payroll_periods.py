"""給与期間管理API"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.api.deps import require_roles
from app.models.company import User
from app.models.attendance import PayrollPeriod
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/payroll-periods", tags=["給与期間"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PayrollPeriodCreate(BaseModel):
    period_type: str
    year_month: int
    start_date: date
    end_date: date
    payment_date: date
    closing_date: date
    weekly_closing_day: int | None = None
    status: str = "draft"


class PayrollPeriodUpdate(BaseModel):
    period_type: str | None = None
    year_month: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    payment_date: date | None = None
    closing_date: date | None = None
    weekly_closing_day: int | None = None
    status: str | None = None


class PayrollPeriodResponse(BaseModel):
    id: int
    company_id: int
    period_type: str
    year_month: int
    start_date: date
    end_date: date
    payment_date: date
    closing_date: date
    weekly_closing_day: int | None = None
    status: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedResponse[PayrollPeriodResponse])
async def list_payroll_periods(
    year_month: int | None = None,
    period_status: str | None = None,
    page: int = 1,
    limit: int = 20,
    user: User = Depends(require_roles("super_admin", "admin", "accountant")),
    db: AsyncSession = Depends(get_db),
):
    """給与期間一覧取得"""
    query = select(PayrollPeriod).where(
        PayrollPeriod.company_id == user.company_id
    )

    if year_month is not None:
        query = query.where(PayrollPeriod.year_month == year_month)
    if period_status is not None:
        query = query.where(PayrollPeriod.status == period_status)

    # 総件数
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # ページネーション
    query = (
        query.order_by(PayrollPeriod.year_month.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[PayrollPeriodResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit,
    )


@router.post("", response_model=PayrollPeriodResponse, status_code=status.HTTP_201_CREATED)
async def create_payroll_period(
    body: PayrollPeriodCreate,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """給与期間作成"""
    # 同一 year_month の重複チェック
    existing = await db.execute(
        select(PayrollPeriod).where(
            PayrollPeriod.company_id == user.company_id,
            PayrollPeriod.year_month == body.year_month,
            PayrollPeriod.period_type == body.period_type,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="同一年月・期間タイプの給与期間が既に存在します",
        )

    period = PayrollPeriod(
        company_id=user.company_id,
        **body.model_dump(),
    )
    db.add(period)
    await db.flush()
    return PayrollPeriodResponse.model_validate(period)


@router.put("/{period_id}", response_model=PayrollPeriodResponse)
async def update_payroll_period(
    period_id: int,
    body: PayrollPeriodUpdate,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """給与期間更新"""
    result = await db.execute(
        select(PayrollPeriod).where(
            PayrollPeriod.id == period_id,
            PayrollPeriod.company_id == user.company_id,
        )
    )
    period = result.scalar_one_or_none()
    if not period:
        raise HTTPException(status_code=404, detail="給与期間が見つかりません")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(period, key, value)

    await db.flush()
    return PayrollPeriodResponse.model_validate(period)


@router.delete("/{period_id}", response_model=dict)
async def delete_payroll_period(
    period_id: int,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """給与期間削除（draftステータスのみ）"""
    result = await db.execute(
        select(PayrollPeriod).where(
            PayrollPeriod.id == period_id,
            PayrollPeriod.company_id == user.company_id,
        )
    )
    period = result.scalar_one_or_none()
    if not period:
        raise HTTPException(status_code=404, detail="給与期間が見つかりません")

    if period.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="draftステータスの給与期間のみ削除できます",
        )

    await db.delete(period)
    await db.flush()
    return {"message": "給与期間を削除しました"}
