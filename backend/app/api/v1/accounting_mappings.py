"""会計科目マッピング管理API"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.api.deps import require_roles
from app.models.company import User
from app.models.notification import AccountingMapping
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/accounting-mappings", tags=["会計科目マッピング"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AccountingMappingCreate(BaseModel):
    item_type: str
    item_code: str
    account_code: str
    account_name: str
    sub_account_code: str | None = None
    sub_account_name: str | None = None
    debit_credit: str | None = None


class AccountingMappingUpdate(BaseModel):
    item_type: str | None = None
    item_code: str | None = None
    account_code: str | None = None
    account_name: str | None = None
    sub_account_code: str | None = None
    sub_account_name: str | None = None
    debit_credit: str | None = None


class AccountingMappingResponse(BaseModel):
    id: int
    company_id: int
    item_type: str
    item_code: str
    account_code: str
    account_name: str
    sub_account_code: str | None = None
    sub_account_name: str | None = None
    debit_credit: str | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedResponse[AccountingMappingResponse])
async def list_accounting_mappings(
    item_type: str | None = None,
    page: int = 1,
    limit: int = 50,
    user: User = Depends(require_roles("super_admin", "admin", "accountant")),
    db: AsyncSession = Depends(get_db),
):
    """会計科目マッピング一覧取得"""
    query = select(AccountingMapping).where(
        AccountingMapping.company_id == user.company_id
    )

    if item_type is not None:
        query = query.where(AccountingMapping.item_type == item_type)

    # 総件数
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # ページネーション
    query = (
        query.order_by(AccountingMapping.item_type, AccountingMapping.item_code)
        .offset((page - 1) * limit)
        .limit(limit)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[AccountingMappingResponse.model_validate(m) for m in items],
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit,
    )


@router.post("", response_model=AccountingMappingResponse, status_code=status.HTTP_201_CREATED)
async def create_accounting_mapping(
    body: AccountingMappingCreate,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """会計科目マッピング作成"""
    # 重複チェック（company_id + item_type + item_code のユニーク制約）
    existing = await db.execute(
        select(AccountingMapping).where(
            AccountingMapping.company_id == user.company_id,
            AccountingMapping.item_type == body.item_type,
            AccountingMapping.item_code == body.item_code,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="同一の項目タイプ・項目コードのマッピングが既に存在します",
        )

    mapping = AccountingMapping(
        company_id=user.company_id,
        **body.model_dump(),
    )
    db.add(mapping)
    await db.flush()
    return AccountingMappingResponse.model_validate(mapping)


@router.put("/{mapping_id}", response_model=AccountingMappingResponse)
async def update_accounting_mapping(
    mapping_id: int,
    body: AccountingMappingUpdate,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """会計科目マッピング更新"""
    result = await db.execute(
        select(AccountingMapping).where(
            AccountingMapping.id == mapping_id,
            AccountingMapping.company_id == user.company_id,
        )
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(status_code=404, detail="マッピングが見つかりません")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(mapping, key, value)

    await db.flush()
    return AccountingMappingResponse.model_validate(mapping)


@router.delete("/{mapping_id}", response_model=dict)
async def delete_accounting_mapping(
    mapping_id: int,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """会計科目マッピング削除"""
    result = await db.execute(
        select(AccountingMapping).where(
            AccountingMapping.id == mapping_id,
            AccountingMapping.company_id == user.company_id,
        )
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(status_code=404, detail="マッピングが見つかりません")

    await db.delete(mapping)
    await db.flush()
    return {"message": "マッピングを削除しました"}
