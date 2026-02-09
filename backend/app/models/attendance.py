"""勤怠データ・給与期間モデル"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Date, DateTime, Integer, Numeric, Text,
    CheckConstraint, ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class AttendanceRecord(Base, TimestampMixin):
    """勤怠データ"""

    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "employee_id", "year_month",
            name="uk_attendance_records",
        ),
        Index("idx_attendance_records_employee_month", "employee_id", "year_month"),
        Index("idx_attendance_records_company_month", "company_id", "year_month"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    employee_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False
    )
    year_month: Mapped[int] = mapped_column(Integer, nullable=False)

    # 勤務日数
    statutory_work_days: Mapped[int | None] = mapped_column(Integer)
    work_days: Mapped[int | None] = mapped_column(Integer)
    absence_days: Mapped[int] = mapped_column(Integer, default=0)
    late_count: Mapped[int] = mapped_column(Integer, default=0)
    early_leave_count: Mapped[int] = mapped_column(Integer, default=0)
    paid_leave_days: Mapped[Decimal] = mapped_column(Numeric(3, 1), default=0)
    substitute_holiday_days: Mapped[Decimal] = mapped_column(Numeric(3, 1), default=0)

    # 労働時間（分単位）
    total_work_minutes: Mapped[int | None] = mapped_column(Integer)
    regular_minutes: Mapped[int | None] = mapped_column(Integer)
    overtime_within_statutory_minutes: Mapped[int] = mapped_column(Integer, default=0)
    overtime_statutory_minutes: Mapped[int] = mapped_column(Integer, default=0)
    night_minutes: Mapped[int] = mapped_column(Integer, default=0)
    statutory_holiday_minutes: Mapped[int] = mapped_column(Integer, default=0)
    non_statutory_holiday_minutes: Mapped[int] = mapped_column(Integer, default=0)
    night_overtime_minutes: Mapped[int] = mapped_column(Integer, default=0)
    night_holiday_minutes: Mapped[int] = mapped_column(Integer, default=0)
    night_overtime_holiday_minutes: Mapped[int] = mapped_column(Integer, default=0)

    # その他
    notes: Mapped[str | None] = mapped_column(Text)


class PayrollPeriod(Base, TimestampMixin):
    """給与期間"""

    __tablename__ = "payroll_periods"
    __table_args__ = (
        CheckConstraint(
            "period_type IN ('monthly', 'weekly', 'daily')",
            name="chk_payroll_periods_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'confirmed', 'paid')",
            name="chk_payroll_periods_status",
        ),
        CheckConstraint(
            "weekly_closing_day IS NULL OR weekly_closing_day BETWEEN 0 AND 6",
            name="chk_payroll_periods_weekly_day",
        ),
        Index("idx_payroll_periods_company_id", "company_id"),
        Index("idx_payroll_periods_year_month", "company_id", "year_month"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    period_type: Mapped[str] = mapped_column(Text, nullable=False)
    year_month: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    closing_date: Mapped[date] = mapped_column(Date, nullable=False)
    weekly_closing_day: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
