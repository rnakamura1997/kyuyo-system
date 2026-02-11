"""システム設定管理API"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.api.deps import require_roles
from app.models.company import User
from app.models.globals import SystemSetting

router = APIRouter(prefix="/system-settings", tags=["システム設定"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SystemSettingUpdate(BaseModel):
    setting_value: dict | None = None
    description: str | None = None


class SystemSettingResponse(BaseModel):
    id: int
    setting_key: str
    setting_value: dict | None = None
    description: str | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[SystemSettingResponse])
async def list_system_settings(
    user: User = Depends(require_roles("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """システム設定一覧取得"""
    result = await db.execute(
        select(SystemSetting).order_by(SystemSetting.setting_key)
    )
    items = result.scalars().all()
    return [SystemSettingResponse.model_validate(s) for s in items]


@router.get("/{key}", response_model=SystemSettingResponse)
async def get_system_setting(
    key: str,
    user: User = Depends(require_roles("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """システム設定取得（キー指定）"""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.setting_key == key)
    )
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="設定が見つかりません")
    return SystemSettingResponse.model_validate(setting)


@router.put("/{key}", response_model=SystemSettingResponse)
async def update_system_setting(
    key: str,
    body: SystemSettingUpdate,
    user: User = Depends(require_roles("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """システム設定更新"""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.setting_key == key)
    )
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="設定が見つかりません")

    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(setting, k, v)

    await db.flush()
    return SystemSettingResponse.model_validate(setting)
