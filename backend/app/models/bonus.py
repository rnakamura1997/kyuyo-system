"""賞与関連モデル"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger, Date, DateTime, Integer, Text,
    CheckConstraint, ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class BonusEvent(Base, TimestampMixin):
    """賞与イベント"""

    __tablename__ = "bonus_events"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'confirmed', 'paid')",
            name="chk_bonus_events_status",
        ),
        Index("idx_bonus_events_company", "company_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    bonus_name: Mapped[str] = mapped_column(Text, nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    notes: Mapped[str | None] = mapped_column(Text)

    # リレーション
    records: Mapped[list["BonusRecord"]] = relationship(
        "BonusRecord", back_populates="event"
    )


class BonusRecord(Base, TimestampMixin):
    """賞与明細"""

    __tablename__ = "bonus_records"
    __table_args__ = (
        UniqueConstraint("bonus_event_id", "employee_id", name="uk_bonus_records"),
        Index("idx_bonus_records_event", "bonus_event_id"),
        Index("idx_bonus_records_employee", "employee_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    bonus_event_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("bonus_events.id", ondelete="RESTRICT"), nullable=False
    )
    employee_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False
    )

    bonus_amount: Mapped[int] = mapped_column(Integer, nullable=False)

    # 社会保険料
    health_insurance: Mapped[int] = mapped_column(Integer, default=0)
    pension_insurance: Mapped[int] = mapped_column(Integer, default=0)
    employment_insurance: Mapped[int] = mapped_column(Integer, default=0)

    # 税金
    income_tax: Mapped[int] = mapped_column(Integer, default=0)
    resident_tax: Mapped[int] = mapped_column(Integer, default=0)

    net_bonus: Mapped[int] = mapped_column(Integer, nullable=False)

    calculation_details: Mapped[dict | None] = mapped_column(JSONB)
    pdf_path: Mapped[str | None] = mapped_column(Text)

    # リレーション
    event: Mapped["BonusEvent"] = relationship("BonusEvent", back_populates="records")
