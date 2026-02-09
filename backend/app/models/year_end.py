"""年末調整関連モデル"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger, Date, DateTime, Integer, Text,
    CheckConstraint, ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class YearEndAdjustment(Base, TimestampMixin):
    """年末調整"""

    __tablename__ = "year_end_adjustments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'submitted', 'returned', 'approved', 'confirmed')",
            name="chk_yea_status",
        ),
        UniqueConstraint(
            "company_id", "employee_id", "target_year",
            name="uk_year_end_adjustments",
        ),
        Index("idx_year_end_adjustments_employee", "employee_id"),
        Index("idx_year_end_adjustments_year", "company_id", "target_year"),
        Index("idx_yea_company_year_status", "company_id", "target_year", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    employee_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False
    )
    target_year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")

    # 控除情報
    basic_deduction: Mapped[int] = mapped_column(Integer, default=0)
    spouse_deduction: Mapped[int] = mapped_column(Integer, default=0)
    dependent_deduction: Mapped[int] = mapped_column(Integer, default=0)
    disability_deduction: Mapped[int] = mapped_column(Integer, default=0)
    widow_deduction: Mapped[int] = mapped_column(Integer, default=0)
    working_student_deduction: Mapped[int] = mapped_column(Integer, default=0)
    social_insurance_premium: Mapped[int] = mapped_column(Integer, default=0)
    small_business_mutual_aid: Mapped[int] = mapped_column(Integer, default=0)
    life_insurance_premium: Mapped[int] = mapped_column(Integer, default=0)
    earthquake_insurance_premium: Mapped[int] = mapped_column(Integer, default=0)
    housing_loan_deduction: Mapped[int] = mapped_column(Integer, default=0)

    # 精算情報
    annual_income: Mapped[int | None] = mapped_column(Integer)
    annual_withheld_tax: Mapped[int | None] = mapped_column(Integer)
    annual_calculated_tax: Mapped[int | None] = mapped_column(Integer)
    adjustment_amount: Mapped[int | None] = mapped_column(Integer)

    # 申告情報
    spouse_info: Mapped[dict | None] = mapped_column(JSONB)
    dependent_info: Mapped[dict | None] = mapped_column(JSONB)
    insurance_info: Mapped[dict | None] = mapped_column(JSONB)

    # 日時
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime)
    return_reason: Mapped[str | None] = mapped_column(Text)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    approved_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime)
    confirmed_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))

    # リレーション
    histories: Mapped[list["YearEndAdjustmentHistory"]] = relationship(
        "YearEndAdjustmentHistory", back_populates="adjustment"
    )
    certificates: Mapped[list["DeductionCertificate"]] = relationship(
        "DeductionCertificate", back_populates="adjustment"
    )
    withholding_slip: Mapped["TaxWithholdingSlip | None"] = relationship(
        "TaxWithholdingSlip", back_populates="adjustment", uselist=False
    )


class YearEndAdjustmentHistory(Base):
    """年末調整履歴"""

    __tablename__ = "year_end_adjustment_histories"
    __table_args__ = (
        Index("idx_yea_histories_adjustment", "year_end_adjustment_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    year_end_adjustment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("year_end_adjustments.id", ondelete="CASCADE"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    changed_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    old_status: Mapped[str | None] = mapped_column(Text)
    new_status: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default="now()")

    # リレーション
    adjustment: Mapped["YearEndAdjustment"] = relationship(
        "YearEndAdjustment", back_populates="histories"
    )


class DeductionCertificate(Base):
    """控除証明書"""

    __tablename__ = "deduction_certificates"
    __table_args__ = (
        Index("idx_deduction_certificates_adjustment", "year_end_adjustment_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    year_end_adjustment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("year_end_adjustments.id", ondelete="CASCADE"),
        nullable=False,
    )
    certificate_type: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default="now()")

    # リレーション
    adjustment: Mapped["YearEndAdjustment"] = relationship(
        "YearEndAdjustment", back_populates="certificates"
    )


class TaxWithholdingSlip(Base):
    """源泉徴収票"""

    __tablename__ = "tax_withholding_slips"
    __table_args__ = (
        UniqueConstraint("year_end_adjustment_id", name="uk_tax_withholding_slips"),
        Index("idx_tax_withholding_slips_employee", "employee_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    year_end_adjustment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("year_end_adjustments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    employee_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False
    )
    target_year: Mapped[int] = mapped_column(Integer, nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    slip_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    pdf_path: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default="now()")

    # リレーション
    adjustment: Mapped["YearEndAdjustment"] = relationship(
        "YearEndAdjustment", back_populates="withholding_slip"
    )
