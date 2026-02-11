"""賞与管理API"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.core.database import get_db
from app.api.deps import require_roles
from app.models.company import User
from app.models.bonus import BonusEvent, BonusRecord
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/bonus", tags=["賞与"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class BonusEventCreate(BaseModel):
    bonus_name: str
    payment_date: date
    status: str = "draft"
    notes: str | None = None


class BonusEventUpdate(BaseModel):
    bonus_name: str | None = None
    payment_date: date | None = None
    status: str | None = None
    notes: str | None = None


class BonusRecordCreate(BaseModel):
    employee_id: int
    bonus_amount: int
    health_insurance: int = 0
    pension_insurance: int = 0
    employment_insurance: int = 0
    income_tax: int = 0
    resident_tax: int = 0
    net_bonus: int
    calculation_details: dict | None = None


class BonusRecordUpdate(BaseModel):
    bonus_amount: int | None = None
    health_insurance: int | None = None
    pension_insurance: int | None = None
    employment_insurance: int | None = None
    income_tax: int | None = None
    resident_tax: int | None = None
    net_bonus: int | None = None
    calculation_details: dict | None = None


class BonusRecordResponse(BaseModel):
    id: int
    company_id: int
    bonus_event_id: int
    employee_id: int
    bonus_amount: int
    health_insurance: int
    pension_insurance: int
    employment_insurance: int
    income_tax: int
    resident_tax: int
    net_bonus: int
    calculation_details: dict | None = None
    pdf_path: str | None = None

    model_config = {"from_attributes": True}


class BonusEventResponse(BaseModel):
    id: int
    company_id: int
    bonus_name: str
    payment_date: date
    status: str
    notes: str | None = None

    model_config = {"from_attributes": True}


class BonusEventDetailResponse(BonusEventResponse):
    records: list[BonusRecordResponse] = []


# ---------------------------------------------------------------------------
# Endpoints — Events
# ---------------------------------------------------------------------------

@router.get("/events", response_model=PaginatedResponse[BonusEventResponse])
async def list_bonus_events(
    page: int = 1,
    limit: int = 20,
    user: User = Depends(require_roles("super_admin", "admin", "accountant")),
    db: AsyncSession = Depends(get_db),
):
    """賞与イベント一覧取得"""
    query = select(BonusEvent).where(
        BonusEvent.company_id == user.company_id
    )

    # 総件数
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # ページネーション
    query = (
        query.order_by(BonusEvent.payment_date.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[BonusEventResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit,
    )


@router.post("/events", response_model=BonusEventResponse, status_code=status.HTTP_201_CREATED)
async def create_bonus_event(
    body: BonusEventCreate,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """賞与イベント作成"""
    event = BonusEvent(
        company_id=user.company_id,
        **body.model_dump(),
    )
    db.add(event)
    await db.flush()
    return BonusEventResponse.model_validate(event)


@router.get("/events/{event_id}", response_model=BonusEventDetailResponse)
async def get_bonus_event(
    event_id: int,
    user: User = Depends(require_roles("super_admin", "admin", "accountant")),
    db: AsyncSession = Depends(get_db),
):
    """賞与イベント詳細取得（明細レコード付き）"""
    result = await db.execute(
        select(BonusEvent)
        .options(selectinload(BonusEvent.records))
        .where(
            BonusEvent.id == event_id,
            BonusEvent.company_id == user.company_id,
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="賞与イベントが見つかりません")

    resp = BonusEventDetailResponse.model_validate(event)
    resp.records = [BonusRecordResponse.model_validate(r) for r in event.records]
    return resp


@router.put("/events/{event_id}", response_model=BonusEventResponse)
async def update_bonus_event(
    event_id: int,
    body: BonusEventUpdate,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """賞与イベント更新"""
    result = await db.execute(
        select(BonusEvent).where(
            BonusEvent.id == event_id,
            BonusEvent.company_id == user.company_id,
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="賞与イベントが見つかりません")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(event, key, value)

    await db.flush()
    return BonusEventResponse.model_validate(event)


# ---------------------------------------------------------------------------
# Endpoints — Records
# ---------------------------------------------------------------------------

@router.post(
    "/events/{event_id}/records",
    response_model=BonusRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_bonus_record(
    event_id: int,
    body: BonusRecordCreate,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """賞与明細レコード追加"""
    # イベント存在チェック
    event_result = await db.execute(
        select(BonusEvent).where(
            BonusEvent.id == event_id,
            BonusEvent.company_id == user.company_id,
        )
    )
    event = event_result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="賞与イベントが見つかりません")

    # 同一従業員の重複チェック
    existing = await db.execute(
        select(BonusRecord).where(
            BonusRecord.bonus_event_id == event_id,
            BonusRecord.employee_id == body.employee_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="この従業員の賞与明細は既に登録されています",
        )

    record = BonusRecord(
        company_id=user.company_id,
        bonus_event_id=event_id,
        **body.model_dump(),
    )
    db.add(record)
    await db.flush()
    return BonusRecordResponse.model_validate(record)


@router.put(
    "/events/{event_id}/records/{record_id}",
    response_model=BonusRecordResponse,
)
async def update_bonus_record(
    event_id: int,
    record_id: int,
    body: BonusRecordUpdate,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """賞与明細レコード更新"""
    result = await db.execute(
        select(BonusRecord).where(
            BonusRecord.id == record_id,
            BonusRecord.bonus_event_id == event_id,
            BonusRecord.company_id == user.company_id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="賞与明細が見つかりません")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(record, key, value)

    await db.flush()
    return BonusRecordResponse.model_validate(record)
