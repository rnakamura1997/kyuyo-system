"""API依存性注入"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.database import get_db, set_rls_context
from app.core.security import decode_token
from app.models.company import User, UserRole
from app.models.globals import Role

settings = get_settings()

# Redis接続
redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_redis() -> aioredis.Redis:
    """Redis接続を取得"""
    return redis_client


def _extract_token(request: Request) -> str | None:
    """リクエストからトークンを取得（Cookie優先、Authorizationヘッダーも対応）"""
    token = request.cookies.get("access_token")
    if token:
        return token

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]

    return None


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> User:
    """現在のログインユーザーを取得"""
    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証が必要です",
        )

    # ブラックリスト確認
    is_blacklisted = await redis.get(f"blacklist:{token}")
    if is_blacklisted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="トークンが無効化されています",
        )

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なトークンです",
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なトークンです",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザーが見つからないか無効です",
        )

    # RLSコンテキスト設定
    await set_rls_context(db, user.company_id, user.is_super_admin)

    return user


async def get_current_user_with_roles(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """ロール情報付きのユーザーを取得"""
    result = await db.execute(
        select(Role.code)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    user._roles = [row[0] for row in result.all()]
    return user


def require_roles(*required_roles: str):
    """指定ロールのいずれかを要求"""
    async def dependency(
        user: User = Depends(get_current_user_with_roles),
    ) -> User:
        user_roles = getattr(user, "_roles", [])
        if user.is_super_admin:
            return user
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="権限がありません",
            )
        return user
    return dependency


CurrentUser = Annotated[User, Depends(get_current_user)]
