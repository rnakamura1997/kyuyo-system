"""手当種別管理API"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.api.deps import require_roles
from app.models.company import User
from app.models.employee import AllowanceType
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/allowance-types", tags=["手当種別"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AllowanceTypeCreate(BaseModel):
    code: str
    name: str
    is_taxable: bool = True
    is_social_insurance_target: bool = True
    is_employment_insurance_target: bool = True
    is_overtime_base: bool = False
    display_order: int | None = None


class AllowanceTypeUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    is_taxable: bool | None = None
    is_social_insurance_target: bool | None = None
    is_employment_insurance_target: bool | None = None
    is_overtime_base: bool | None = None
    display_order: int | None = None


class AllowanceTypeResponse(BaseModel):
    id: int
    company_id: int
    code: str
    name: str
    is_taxable: bool
    is_social_insurance_target: bool
    is_employment_insurance_target: bool
    is_overtime_base: bool
    is_active: bool
    display_order: int | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedResponse[AllowanceTypeResponse])
async def list_allowance_types(
    is_active: bool | None = True,
    page: int = 1,
    limit: int = 50,
    user: User = Depends(require_roles("super_admin", "admin", "accountant")),
    db: AsyncSession = Depends(get_db),
):
    """手当種別一覧取得"""
    query = select(AllowanceType).where(
        AllowanceType.company_id == user.company_id
    )

    if is_active is not None:
        query = query.where(AllowanceType.is_active == is_active)

    # 総件数
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # ページネーション
    query = (
        query.order_by(AllowanceType.display_order, AllowanceType.id)
        .offset((page - 1) * limit)
        .limit(limit)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[AllowanceTypeResponse.model_validate(a) for a in items],
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit,
    )


@router.post("", response_model=AllowanceTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_allowance_type(
    body: AllowanceTypeCreate,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """手当種別作成"""
    # コード重複チェック
    existing = await db.execute(
        select(AllowanceType).where(
            AllowanceType.company_id == user.company_id,
            AllowanceType.code == body.code,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="この手当コードは既に使用されています",
        )

    allowance_type = AllowanceType(
        company_id=user.company_id,
        **body.model_dump(),
    )
    db.add(allowance_type)
    await db.flush()
    return AllowanceTypeResponse.model_validate(allowance_type)


@router.put("/{allowance_type_id}", response_model=AllowanceTypeResponse)
async def update_allowance_type(
    allowance_type_id: int,
    body: AllowanceTypeUpdate,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """手当種別更新"""
    result = await db.execute(
        select(AllowanceType).where(
            AllowanceType.id == allowance_type_id,
            AllowanceType.company_id == user.company_id,
        )
    )
    allowance_type = result.scalar_one_or_none()
    if not allowance_type:
        raise HTTPException(status_code=404, detail="手当種別が見つかりません")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(allowance_type, key, value)

    await db.flush()
    return AllowanceTypeResponse.model_validate(allowance_type)


@router.delete("/{allowance_type_id}", response_model=dict)
async def delete_allowance_type(
    allowance_type_id: int,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """手当種別削除（論理削除: is_active=False）"""
    result = await db.execute(
        select(AllowanceType).where(
            AllowanceType.id == allowance_type_id,
            AllowanceType.company_id == user.company_id,
            AllowanceType.is_active == True,
        )
    )
    allowance_type = result.scalar_one_or_none()
    if not allowance_type:
        raise HTTPException(status_code=404, detail="手当種別が見つかりません")

    allowance_type.is_active = False
    await db.flush()
    return {"message": "手当種別を無効化しました"}
