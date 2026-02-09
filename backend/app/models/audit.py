"""監査ログモデル"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLog(Base):
    """監査ログ"""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_logs_company", "company_id"),
        Index("idx_audit_logs_user", "user_id"),
        Index("idx_audit_logs_table", "table_name", "record_id"),
        Index("idx_audit_logs_created", "created_at"),
        Index("idx_audit_logs_action", "action"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int | None] = mapped_column(BigInteger)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    table_name: Mapped[str | None] = mapped_column(Text)
    record_id: Mapped[int | None] = mapped_column(BigInteger)
    old_values: Mapped[dict | None] = mapped_column(JSONB)
    new_values: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(Text)
    user_agent: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default="now()")
