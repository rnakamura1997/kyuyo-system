"""会社管理API"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import require_roles
from app.models.company import Company, User
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/companies", tags=["会社管理"])


@router.get("", response_model=PaginatedResponse[CompanyResponse])
async def list_companies(
    page: int = 1,
    limit: int = 20,
    is_deleted: bool = False,
    user: User = Depends(require_roles("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """会社一覧取得"""
    query = select(Company)
    if not is_deleted:
        query = query.where(Company.is_deleted == False)

    # 総件数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # ページネーション
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[CompanyResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit,
    )


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: int,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """会社詳細取得"""
    result = await db.execute(
        select(Company).where(
            Company.company_id == company_id,
            Company.is_deleted == False,
        )
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="会社が見つかりません")
    return CompanyResponse.model_validate(company)


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    body: CompanyCreate,
    user: User = Depends(require_roles("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """会社作成"""
    # company_id の自動採番（既存の最大値 + 1）
    max_result = await db.execute(select(func.max(Company.company_id)))
    max_id = max_result.scalar() or 0

    company = Company(
        company_id=max_id + 1,
        **body.model_dump(),
    )
    db.add(company)
    await db.flush()
    return CompanyResponse.model_validate(company)


@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    body: CompanyUpdate,
    user: User = Depends(require_roles("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """会社更新"""
    result = await db.execute(
        select(Company).where(
            Company.company_id == company_id,
            Company.is_deleted == False,
        )
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="会社が見つかりません")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(company, key, value)

    await db.flush()
    return CompanyResponse.model_validate(company)


@router.delete("/{company_id}", response_model=dict)
async def delete_company(
    company_id: int,
    user: User = Depends(require_roles("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """会社削除（論理削除）"""
    result = await db.execute(
        select(Company).where(
            Company.company_id == company_id,
            Company.is_deleted == False,
        )
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="会社が見つかりません")

    company.is_deleted = True
    await db.flush()
    return {"message": "会社を削除しました"}
