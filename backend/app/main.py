"""FastAPIアプリケーション エントリーポイント"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import get_settings
from app.api.v1 import (
    auth, companies, employees, attendance, payroll_periods,
    allowance_types, insurance_rates, users, system_settings,
    accounting_mappings, bonus, payroll, year_end, reports,
)

settings = get_settings()

# レート制限
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="給与明細管理システム",
    description="kyuuyomeisai - 給与明細管理システム API",
    version="1.0.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

# ミドルウェア
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# APIルーター登録
app.include_router(auth.router, prefix="/api/v1")
app.include_router(companies.router, prefix="/api/v1")
app.include_router(employees.router, prefix="/api/v1")
app.include_router(attendance.router, prefix="/api/v1")
app.include_router(payroll_periods.router, prefix="/api/v1")
app.include_router(allowance_types.router, prefix="/api/v1")
app.include_router(insurance_rates.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(system_settings.router, prefix="/api/v1")
app.include_router(accounting_mappings.router, prefix="/api/v1")
app.include_router(bonus.router, prefix="/api/v1")
app.include_router(payroll.router, prefix="/api/v1")
app.include_router(year_end.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")


@app.get("/api/health")
async def health_check():
    """ヘルスチェック"""
    return {"status": "ok", "service": "kyuuyomeisai"}
