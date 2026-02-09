"""共通モデル基盤"""

from datetime import datetime, timezone
from sqlalchemy import BigInteger, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TimestampMixin:
    """created_at / updated_at 共通カラム"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.current_timestamp(),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class SoftDeleteMixin:
    """論理削除 共通カラム"""

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
