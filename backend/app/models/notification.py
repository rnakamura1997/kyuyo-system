"""通知・連携関連モデル"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger, Date, DateTime, Integer, Text,
    CheckConstraint, ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class PayrollNotificationToken(Base):
    """明細通知トークン"""

    __tablename__ = "payroll_notification_tokens"
    __table_args__ = (
        Index("idx_notification_tokens_record", "payroll_record_id"),
        Index("idx_notification_tokens_hash", "token_hash"),
        Index("idx_notification_tokens_expires", "expires_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payroll_record_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("payroll_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    accessed_at: Mapped[datetime | None] = mapped_column(DateTime)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default="now()")


class AccountingMapping(Base, TimestampMixin):
    """会計科目マッピング"""

    __tablename__ = "accounting_mappings"
    __table_args__ = (
        CheckConstraint(
            "item_type IN ('earning', 'deduction')",
            name="chk_accounting_mappings_type",
        ),
        CheckConstraint(
            "debit_credit IS NULL OR debit_credit IN ('debit', 'credit')",
            name="chk_accounting_mappings_dc",
        ),
        UniqueConstraint(
            "company_id", "item_type", "item_code",
            name="uk_accounting_mappings",
        ),
        Index("idx_accounting_mappings_company", "company_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    item_type: Mapped[str] = mapped_column(Text, nullable=False)
    item_code: Mapped[str] = mapped_column(Text, nullable=False)
    account_code: Mapped[str] = mapped_column(Text, nullable=False)
    account_name: Mapped[str] = mapped_column(Text, nullable=False)
    sub_account_code: Mapped[str | None] = mapped_column(Text)
    sub_account_name: Mapped[str | None] = mapped_column(Text)
    debit_credit: Mapped[str | None] = mapped_column(Text)


class BankTransferExport(Base):
    """銀行振込データ"""

    __tablename__ = "bank_transfer_exports"
    __table_args__ = (
        Index("idx_bank_transfer_exports_company", "company_id"),
        Index("idx_bank_transfer_exports_date", "export_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    export_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default="now()")
