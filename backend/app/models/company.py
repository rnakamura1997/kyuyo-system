"""会社・ユーザー関連モデル"""

from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Integer, Text,
    CheckConstraint, ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, SoftDeleteMixin


class Company(Base, TimestampMixin, SoftDeleteMixin):
    """会社マスタ"""

    __tablename__ = "companies"
    __table_args__ = (
        CheckConstraint("closing_day BETWEEN 1 AND 31", name="chk_companies_closing_day"),
        CheckConstraint("payment_day BETWEEN 1 AND 31", name="chk_companies_payment_day"),
        UniqueConstraint("company_id", name="uk_companies_company_id"),
        Index("idx_companies_company_id", "company_id", postgresql_where="is_deleted = false"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_kana: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    representative_name: Mapped[str | None] = mapped_column(Text)
    legal_number: Mapped[str | None] = mapped_column(Text)
    logo_path: Mapped[str | None] = mapped_column(Text)

    # 給与設定
    closing_day: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_day: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_month_offset: Mapped[int] = mapped_column(Integer, default=1)

    # 健康保険
    health_insurance_type: Mapped[str | None] = mapped_column(Text)
    health_insurance_prefecture: Mapped[str | None] = mapped_column(Text)
    health_insurance_union_name: Mapped[str | None] = mapped_column(Text)
    business_office_symbol: Mapped[str | None] = mapped_column(Text)
    care_insurance_applicable: Mapped[bool] = mapped_column(Boolean, default=True)

    # 厚生年金
    pension_office_number: Mapped[str | None] = mapped_column(Text)

    # 雇用保険
    employment_office_number: Mapped[str | None] = mapped_column(Text)
    employment_business_type: Mapped[str | None] = mapped_column(Text)

    # その他
    settings: Mapped[dict | None] = mapped_column(JSONB)

    # リレーション
    users: Mapped[list["User"]] = relationship("User", back_populates="company")
    employees: Mapped[list["Employee"]] = relationship(
        "Employee", back_populates="company", foreign_keys="Employee.company_id"
    )


class User(Base, TimestampMixin):
    """ユーザーアカウント"""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="uk_users_username"),
        UniqueConstraint("email", name="uk_users_email"),
        Index("idx_users_company_id", "company_id"),
        Index("idx_users_email", "email"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("companies.company_id", ondelete="RESTRICT"),
        nullable=False,
    )
    username: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)

    # リレーション
    company: Mapped["Company"] = relationship("Company", back_populates="users")
    user_roles: Mapped[list["UserRole"]] = relationship("UserRole", back_populates="user")


class UserRole(Base):
    """ユーザーロール紐付け"""

    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uk_user_roles"),
        Index("idx_user_roles_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default="now()"
    )

    # リレーション
    user: Mapped["User"] = relationship("User", back_populates="user_roles")
    role: Mapped["Role"] = relationship("Role")


# 循環参照回避のためのインポート
from app.models.globals import Role  # noqa: E402
from app.models.employee import Employee  # noqa: E402
