"""従業員管理API"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import require_roles
from app.models.company import User
from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeResponse
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/employees", tags=["従業員管理"])


@router.get("", response_model=PaginatedResponse[EmployeeResponse])
async def list_employees(
    page: int = 1,
    limit: int = 20,
    search: str | None = None,
    employment_type: str | None = None,
    is_deleted: bool = False,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """従業員一覧取得"""
    query = select(Employee).where(Employee.company_id == user.company_id)

    if not is_deleted:
        query = query.where(Employee.is_deleted == False)

    if search:
        query = query.where(
            or_(
                Employee.first_name.ilike(f"%{search}%"),
                Employee.last_name.ilike(f"%{search}%"),
                Employee.employee_code.ilike(f"%{search}%"),
                Employee.first_name_kana.ilike(f"%{search}%"),
                Employee.last_name_kana.ilike(f"%{search}%"),
            )
        )

    if employment_type:
        query = query.where(Employee.employment_type == employment_type)

    # 総件数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # ページネーション
    query = query.order_by(Employee.employee_code).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[EmployeeResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit,
    )


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: int,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """従業員詳細取得"""
    result = await db.execute(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.company_id == user.company_id,
            Employee.is_deleted == False,
        )
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="従業員が見つかりません")
    return EmployeeResponse.model_validate(employee)


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    body: EmployeeCreate,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """従業員作成"""
    # 従業員コード重複チェック
    existing = await db.execute(
        select(Employee).where(
            Employee.company_id == user.company_id,
            Employee.employee_code == body.employee_code,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="この従業員コードは既に使用されています",
        )

    employee = Employee(
        company_id=user.company_id,
        **body.model_dump(),
    )
    db.add(employee)
    await db.flush()
    return EmployeeResponse.model_validate(employee)


@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: int,
    body: EmployeeUpdate,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """従業員更新"""
    result = await db.execute(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.company_id == user.company_id,
            Employee.is_deleted == False,
        )
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="従業員が見つかりません")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(employee, key, value)

    await db.flush()
    return EmployeeResponse.model_validate(employee)


@router.delete("/{employee_id}", response_model=dict)
async def delete_employee(
    employee_id: int,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """従業員削除（論理削除）"""
    result = await db.execute(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.company_id == user.company_id,
            Employee.is_deleted == False,
        )
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="従業員が見つかりません")

    employee.is_deleted = True
    await db.flush()
    return {"message": "従業員を削除しました"}
