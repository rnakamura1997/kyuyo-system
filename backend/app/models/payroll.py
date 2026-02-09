"""給与明細関連モデル"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Boolean, Date, DateTime, Integer, Numeric, Text,
    CheckConstraint, ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class PayrollRecordGroup(Base, TimestampMixin):
    """給与明細グループ"""

    __tablename__ = "payroll_record_groups"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "employee_id", "payroll_period_id",
            name="uk_payroll_record_groups",
        ),
        Index("idx_payroll_groups_employee", "employee_id"),
        Index("idx_payroll_groups_period", "payroll_period_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    employee_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False
    )
    payroll_period_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("payroll_periods.id", ondelete="RESTRICT"), nullable=False
    )
    current_payroll_record_id: Mapped[int | None] = mapped_column(BigInteger)

    # リレーション
    records: Mapped[list["PayrollRecord"]] = relationship(
        "PayrollRecord", back_populates="group"
    )


class PayrollRecord(Base, TimestampMixin):
    """給与明細"""

    __tablename__ = "payroll_records"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'confirmed', 'cancelled')",
            name="chk_payroll_records_status",
        ),
        CheckConstraint(
            "total_earnings >= 0 AND total_deductions >= 0",
            name="chk_payroll_records_amounts",
        ),
        Index("idx_payroll_records_group", "payroll_record_group_id"),
        Index("idx_payroll_records_employee", "employee_id"),
        Index("idx_payroll_records_period", "payroll_period_id"),
        Index("idx_payroll_records_status", "company_id", "status"),
        Index(
            "idx_payroll_records_company_status_payment",
            "company_id", "status", "payment_date",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payroll_record_group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("payroll_record_groups.id", ondelete="RESTRICT"),
        nullable=False,
    )
    employee_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False
    )
    payroll_period_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("payroll_periods.id", ondelete="RESTRICT"), nullable=False
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)

    # 金額（円単位）
    total_earnings: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_deductions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    net_pay: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 計算詳細
    calculation_details: Mapped[dict | None] = mapped_column(JSONB)

    # 確定・取消情報
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime)
    confirmed_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id")
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancelled_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id")
    )
    cancellation_reason: Mapped[str | None] = mapped_column(Text)

    # PDF
    pdf_path: Mapped[str | None] = mapped_column(Text)

    # リレーション
    group: Mapped["PayrollRecordGroup"] = relationship(
        "PayrollRecordGroup", back_populates="records"
    )
    items: Mapped[list["PayrollRecordItem"]] = relationship(
        "PayrollRecordItem", back_populates="record"
    )
    snapshot: Mapped["PayrollSnapshot | None"] = relationship(
        "PayrollSnapshot", back_populates="record", uselist=False
    )


class PayrollRecordItem(Base):
    """給与明細項目"""

    __tablename__ = "payroll_record_items"
    __table_args__ = (
        CheckConstraint(
            "item_type IN ('earning', 'deduction')",
            name="chk_payroll_items_type",
        ),
        Index("idx_payroll_items_record", "payroll_record_id"),
        Index("idx_payroll_items_type", "payroll_record_id", "item_type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payroll_record_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("payroll_records.id", ondelete="CASCADE"), nullable=False
    )

    item_type: Mapped[str] = mapped_column(Text, nullable=False)
    item_code: Mapped[str] = mapped_column(Text, nullable=False)
    item_name: Mapped[str] = mapped_column(Text, nullable=False)

    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    is_taxable: Mapped[bool] = mapped_column(Boolean, default=True)
    is_social_insurance_target: Mapped[bool] = mapped_column(Boolean, default=True)
    is_employment_insurance_target: Mapped[bool] = mapped_column(Boolean, default=True)

    display_order: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default="now()")

    # リレーション
    record: Mapped["PayrollRecord"] = relationship(
        "PayrollRecord", back_populates="items"
    )


class PayrollSnapshot(Base):
    """給与スナップショット"""

    __tablename__ = "payroll_snapshots"
    __table_args__ = (
        Index("idx_payroll_snapshots_record", "payroll_record_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payroll_record_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("payroll_records.id", ondelete="RESTRICT"),
        nullable=False,
    )
    snapshot_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default="now()")

    # リレーション
    record: Mapped["PayrollRecord"] = relationship(
        "PayrollRecord", back_populates="snapshot"
    )


class PayrollHistory(Base):
    """給与履歴"""

    __tablename__ = "payroll_histories"
    __table_args__ = (
        Index("idx_payroll_histories_record", "payroll_record_id"),
        Index("idx_payroll_histories_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payroll_record_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("payroll_records.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    changed_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id")
    )
    old_values: Mapped[dict | None] = mapped_column(JSONB)
    new_values: Mapped[dict | None] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default="now()")
