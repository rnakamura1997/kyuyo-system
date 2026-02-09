"""社会保険料率モデル"""

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Date, Numeric, Text,
    CheckConstraint, Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class InsuranceRate(Base, TimestampMixin):
    """社会保険料率"""

    __tablename__ = "insurance_rates"
    __table_args__ = (
        CheckConstraint(
            "insurance_type IN ('health', 'pension', 'employment')",
            name="chk_insurance_rates_type",
        ),
        Index(
            "idx_insurance_rates_lookup",
            "insurance_type", "valid_from", "valid_to", "prefecture",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int | None] = mapped_column(BigInteger)
    insurance_type: Mapped[str] = mapped_column(Text, nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)
    prefecture: Mapped[str | None] = mapped_column(Text)
    business_type: Mapped[str | None] = mapped_column(Text)
    employee_rate: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    employer_rate: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    care_insurance_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 5))
