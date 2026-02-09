"""データベース接続管理"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """データベースセッションを取得"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def set_rls_context(
    db: AsyncSession,
    company_id: int,
    is_super_admin: bool = False,
) -> None:
    """RLSコンテキストを設定"""
    await db.execute(
        text("SET LOCAL app.current_company_id = :company_id"),
        {"company_id": str(company_id)},
    )
    await db.execute(
        text("SET LOCAL app.is_super_admin = :is_super_admin"),
        {"is_super_admin": str(is_super_admin).lower()},
    )
