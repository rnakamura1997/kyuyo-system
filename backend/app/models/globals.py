"""グローバルテーブル（company_id なし）"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Boolean, Date, DateTime, Integer, Numeric, Text,
    CheckConstraint, UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class Role(Base, TimestampMixin):
    """ロール定義"""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    permissions: Mapped[dict | None] = mapped_column(JSONB)


class SystemSetting(Base, TimestampMixin):
    """システム設定"""

    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    setting_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    setting_value: Mapped[dict | None] = mapped_column(JSONB)
    description: Mapped[str | None] = mapped_column(Text)


class IncomeTaxTable(Base, TimestampMixin):
    """所得税額表"""

    __tablename__ = "income_tax_tables"
    __table_args__ = (
        CheckConstraint(
            "table_type IN ('monthly_kou', 'daily_kou', 'otsu', 'hei')",
            name="chk_income_tax_table_type",
        ),
        Index(
            "idx_income_tax_tables_lookup",
            "table_type", "valid_from", "valid_to", "income_from", "dependents_count",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    table_type: Mapped[str] = mapped_column(Text, nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)
    income_from: Mapped[int] = mapped_column(Integer, nullable=False)
    income_to: Mapped[int | None] = mapped_column(Integer)
    dependents_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tax_amount: Mapped[int] = mapped_column(Integer, nullable=False)


class CommuteTaxLimit(Base, TimestampMixin):
    """通勤手当非課税限度額"""

    __tablename__ = "commute_tax_limits"
    __table_args__ = (
        CheckConstraint(
            "commute_type IN ('public_transport', 'car', 'bicycle', 'mixed')",
            name="chk_commute_tax_limit_type",
        ),
        Index("idx_commute_tax_limits_lookup", "valid_from", "valid_to", "commute_type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)
    commute_type: Mapped[str] = mapped_column(Text, nullable=False)
    distance_from: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    distance_to: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    limit_amount: Mapped[int] = mapped_column(Integer, nullable=False)


class InsuranceConstant(Base, TimestampMixin):
    """社会保険定数"""

    __tablename__ = "insurance_constants"
    __table_args__ = (
        CheckConstraint(
            "constant_type IN ('bonus_health_limit', 'bonus_pension_limit')",
            name="chk_insurance_constant_type",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    constant_type: Mapped[str] = mapped_column(Text, nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)
    limit_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
