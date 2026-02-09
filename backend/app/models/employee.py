"""従業員関連モデル"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Boolean, Date, DateTime, Integer, Numeric, Text,
    CheckConstraint, ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, SoftDeleteMixin


class Employee(Base, TimestampMixin, SoftDeleteMixin):
    """従業員マスタ"""

    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint(
            "salary_type IN ('daily', 'hourly', 'monthly', 'commission')",
            name="chk_employees_salary_type",
        ),
        CheckConstraint(
            "tax_category IN ('kou', 'otsu', 'hei')",
            name="chk_employees_tax_category",
        ),
        CheckConstraint(
            "gender IN ('male', 'female', 'other')",
            name="chk_employees_gender",
        ),
        CheckConstraint(
            "account_type IS NULL OR account_type IN ('savings', 'checking')",
            name="chk_employees_account_type",
        ),
        CheckConstraint(
            "resident_tax_type IS NULL OR resident_tax_type IN ('special', 'ordinary')",
            name="chk_employees_resident_tax_type",
        ),
        UniqueConstraint("company_id", "employee_code", name="uk_employees_company_code"),
        Index("idx_employees_company_id", "company_id", postgresql_where="is_deleted = false"),
        Index("idx_employees_email", "email"),
        Index("idx_employees_hire_date", "hire_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    employee_code: Mapped[str] = mapped_column(Text, nullable=False)

    # 基本情報
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    first_name_kana: Mapped[str | None] = mapped_column(Text)
    last_name_kana: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    birth_date: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)

    # 雇用情報
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    termination_date: Mapped[date | None] = mapped_column(Date)
    employment_type: Mapped[str] = mapped_column(Text, nullable=False)
    department: Mapped[str | None] = mapped_column(Text)
    position: Mapped[str | None] = mapped_column(Text)

    # 給与設定
    salary_type: Mapped[str] = mapped_column(Text, nullable=False)
    salary_settings: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # 税金・社会保険
    tax_category: Mapped[str] = mapped_column(Text, nullable=False)
    dependents_count: Mapped[int] = mapped_column(Integer, default=0)
    social_insurance_enrolled: Mapped[bool] = mapped_column(Boolean, default=False)
    pension_insurance_enrolled: Mapped[bool] = mapped_column(Boolean, default=False)
    employment_insurance_enrolled: Mapped[bool] = mapped_column(Boolean, default=False)
    resident_tax_type: Mapped[str | None] = mapped_column(Text)
    resident_tax_monthly_amount: Mapped[int | None] = mapped_column(Integer)

    # 銀行口座
    bank_name: Mapped[str | None] = mapped_column(Text)
    branch_name: Mapped[str | None] = mapped_column(Text)
    account_type: Mapped[str | None] = mapped_column(Text)
    account_number: Mapped[str | None] = mapped_column(Text)
    account_holder: Mapped[str | None] = mapped_column(Text)

    # その他
    notes: Mapped[str | None] = mapped_column(Text)

    # リレーション
    company: Mapped["Company"] = relationship(
        "Company", back_populates="employees", foreign_keys=[company_id]
    )
    allowances: Mapped[list["EmployeeAllowance"]] = relationship(
        "EmployeeAllowance", back_populates="employee"
    )
    commute_details: Mapped[list["CommuteDetail"]] = relationship(
        "CommuteDetail", back_populates="employee"
    )


class AllowanceType(Base, TimestampMixin):
    """手当種別マスタ"""

    __tablename__ = "allowance_types"
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uk_allowance_types_company_code"),
        Index("idx_allowance_types_company_id", "company_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    is_taxable: Mapped[bool] = mapped_column(Boolean, default=True)
    is_social_insurance_target: Mapped[bool] = mapped_column(Boolean, default=True)
    is_employment_insurance_target: Mapped[bool] = mapped_column(Boolean, default=True)
    is_overtime_base: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int | None] = mapped_column(Integer)


class EmployeeAllowance(Base, TimestampMixin):
    """従業員手当設定"""

    __tablename__ = "employee_allowances"
    __table_args__ = (
        Index("idx_employee_allowances_employee_id", "employee_id"),
        Index("idx_employee_allowances_effective", "effective_from", "effective_to"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    employee_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    allowance_type_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("allowance_types.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)

    # リレーション
    employee: Mapped["Employee"] = relationship("Employee", back_populates="allowances")
    allowance_type: Mapped["AllowanceType"] = relationship("AllowanceType")


class CommuteDetail(Base, TimestampMixin):
    """通勤情報"""

    __tablename__ = "commute_details"
    __table_args__ = (
        CheckConstraint(
            "commute_method IN ('public_transport', 'car', 'bicycle', 'mixed')",
            name="chk_commute_details_method",
        ),
        Index("idx_commute_details_employee_id", "employee_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    employee_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    commute_method: Mapped[str] = mapped_column(Text, nullable=False)
    distance: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    route: Mapped[str | None] = mapped_column(Text)
    monthly_cost: Mapped[int | None] = mapped_column(Integer)
    non_taxable_limit: Mapped[int | None] = mapped_column(Integer)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)

    # リレーション
    employee: Mapped["Employee"] = relationship("Employee", back_populates="commute_details")


# 循環参照回避
from app.models.company import Company  # noqa: E402
