"""認証API"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.api.deps import get_current_user, get_redis, get_current_user_with_roles
from app.models.company import User, UserRole
from app.models.globals import Role
from app.models.audit import AuditLog
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserInfo,
    RefreshResponse,
    MessageResponse,
)

router = APIRouter(prefix="/auth", tags=["認証"])
settings = get_settings()


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """ログイン"""
    result = await db.execute(
        select(User).where(User.username == body.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが正しくありません",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="アカウントが無効です",
        )

    # ロール取得
    role_result = await db.execute(
        select(Role.code)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    roles = [row[0] for row in role_result.all()]

    # トークン生成
    token_data = {
        "user_id": user.id,
        "username": user.username,
        "company_id": user.company_id,
        "is_super_admin": user.is_super_admin,
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # リフレッシュトークンをRedisに保存
    await redis.setex(
        f"refresh:{user.id}",
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        refresh_token,
    )

    # Cookie設定
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.APP_ENV == "production",
        samesite="strict",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.APP_ENV == "production",
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )

    # 最終ログイン更新
    user.last_login_at = datetime.now(timezone.utc)

    # 監査ログ
    audit = AuditLog(
        company_id=user.company_id,
        user_id=user.id,
        action="login",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(audit)

    return TokenResponse(
        access_token=access_token,
        user=UserInfo(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_super_admin=user.is_super_admin,
            company_id=user.company_id,
            roles=roles,
        ),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """ログアウト"""
    # アクセストークンをブラックリストに追加
    token = request.cookies.get("access_token") or ""
    if token:
        await redis.setex(
            f"blacklist:{token}",
            settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "1",
        )

    # リフレッシュトークン削除
    await redis.delete(f"refresh:{user.id}")

    # Cookie削除
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    # 監査ログ
    audit = AuditLog(
        company_id=user.company_id,
        user_id=user.id,
        action="logout",
        ip_address=request.client.host if request.client else None,
    )
    db.add(audit)

    return MessageResponse(message="ログアウトしました")


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """トークン更新"""
    refresh = request.cookies.get("refresh_token")
    if not refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="リフレッシュトークンがありません",
        )

    payload = decode_token(refresh)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なリフレッシュトークンです",
        )

    user_id = payload.get("user_id")

    # Redisに保存されたトークンと照合
    stored = await redis.get(f"refresh:{user_id}")
    if stored != refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="リフレッシュトークンが無効化されています",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザーが見つからないか無効です",
        )

    # 新しいトークン生成（ローテーション）
    token_data = {
        "user_id": user.id,
        "username": user.username,
        "company_id": user.company_id,
        "is_super_admin": user.is_super_admin,
    }
    new_access = create_access_token(token_data)
    new_refresh = create_refresh_token(token_data)

    # 旧リフレッシュトークンを無効化、新トークンを保存
    await redis.setex(
        f"refresh:{user.id}",
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        new_refresh,
    )

    response.set_cookie(
        key="access_token",
        value=new_access,
        httponly=True,
        secure=settings.APP_ENV == "production",
        samesite="strict",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        secure=settings.APP_ENV == "production",
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )

    return RefreshResponse(access_token=new_access)


@router.get("/me", response_model=UserInfo)
async def get_me(
    user: User = Depends(get_current_user_with_roles),
):
    """現在のユーザー情報を取得"""
    return UserInfo(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_super_admin=user.is_super_admin,
        company_id=user.company_id,
        roles=getattr(user, "_roles", []),
    )
