"""ユーザー管理API"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.core.security import hash_password
from app.api.deps import require_roles
from app.models.company import User, UserRole
from app.models.globals import Role
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/users", tags=["ユーザー管理"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    is_super_admin: bool = False
    is_active: bool = True
    role_codes: list[str] = []


class UserUpdate(BaseModel):
    username: str | None = None
    email: str | None = None
    full_name: str | None = None
    is_super_admin: bool | None = None


class UserPasswordChange(BaseModel):
    new_password: str


class RoleResponse(BaseModel):
    code: str
    name: str

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: int
    company_id: int
    username: str
    email: str
    full_name: str
    is_super_admin: bool
    is_active: bool
    last_login_at: datetime | None = None
    roles: list[RoleResponse] = []

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _build_user_response(db: AsyncSession, user: User) -> UserResponse:
    """ユーザーレスポンスを構築（ロール情報付き）"""
    result = await db.execute(
        select(Role)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    roles = result.scalars().all()
    resp = UserResponse.model_validate(user)
    resp.roles = [RoleResponse.model_validate(r) for r in roles]
    return resp


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    company_id: int | None = None,
    page: int = 1,
    limit: int = 20,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """ユーザー一覧取得"""
    # super_admin のみ company_id フィルタを指定可能
    if company_id is not None and not user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="company_idによるフィルタはsuper_adminのみ使用できます",
        )

    target_company_id = company_id if (company_id is not None and user.is_super_admin) else user.company_id
    query = select(User).where(User.company_id == target_company_id)

    # 総件数
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # ページネーション
    query = query.order_by(User.id).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    response_items = []
    for u in items:
        response_items.append(await _build_user_response(db, u))

    return PaginatedResponse(
        items=response_items,
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """ユーザー作成"""
    # ユーザー名重複チェック
    existing = await db.execute(
        select(User).where(User.username == body.username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="このユーザー名は既に使用されています",
        )

    # メール重複チェック
    existing_email = await db.execute(
        select(User).where(User.email == body.email)
    )
    if existing_email.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="このメールアドレスは既に使用されています",
        )

    new_user = User(
        company_id=user.company_id,
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        is_super_admin=body.is_super_admin if user.is_super_admin else False,
        is_active=body.is_active,
    )
    db.add(new_user)
    await db.flush()

    # ロール割り当て
    if body.role_codes:
        role_result = await db.execute(
            select(Role).where(Role.code.in_(body.role_codes))
        )
        roles = role_result.scalars().all()
        for role in roles:
            user_role = UserRole(
                company_id=user.company_id,
                user_id=new_user.id,
                role_id=role.id,
            )
            db.add(user_role)
        await db.flush()

    return await _build_user_response(db, new_user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """ユーザー詳細取得"""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.company_id == user.company_id,
        )
    )
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    return await _build_user_response(db, target_user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    body: UserUpdate,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """ユーザー更新（パスワード以外）"""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.company_id == user.company_id,
        )
    )
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    update_data = body.model_dump(exclude_unset=True)

    # is_super_admin は super_admin のみ変更可能
    if "is_super_admin" in update_data and not user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="super_admin権限の変更はsuper_adminのみ可能です",
        )

    # ユーザー名の重複チェック
    if "username" in update_data and update_data["username"] != target_user.username:
        dup = await db.execute(
            select(User).where(User.username == update_data["username"])
        )
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="このユーザー名は既に使用されています",
            )

    # メールの重複チェック
    if "email" in update_data and update_data["email"] != target_user.email:
        dup = await db.execute(
            select(User).where(User.email == update_data["email"])
        )
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="このメールアドレスは既に使用されています",
            )

    for key, value in update_data.items():
        setattr(target_user, key, value)

    await db.flush()
    return await _build_user_response(db, target_user)


@router.put("/{user_id}/password", response_model=dict)
async def change_user_password(
    user_id: int,
    body: UserPasswordChange,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """ユーザーパスワード変更"""
    # 自分自身のパスワード変更、または admin/super_admin による変更を許可
    if user.id != user_id:
        result = await db.execute(
            select(User).where(
                User.id == user_id,
                User.company_id == user.company_id,
            )
        )
        target_user = result.scalar_one_or_none()
        if not target_user:
            raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    else:
        target_user = user

    target_user.password_hash = hash_password(body.new_password)
    await db.flush()
    return {"message": "パスワードを変更しました"}


@router.put("/{user_id}/toggle-active", response_model=UserResponse)
async def toggle_user_active(
    user_id: int,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """ユーザー有効/無効切り替え"""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.company_id == user.company_id,
        )
    )
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    if target_user.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="自分自身を無効化することはできません",
        )

    target_user.is_active = not target_user.is_active
    await db.flush()
    return await _build_user_response(db, target_user)
