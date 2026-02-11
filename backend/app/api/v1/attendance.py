"""勤怠データAPI"""

import csv
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.api.deps import require_roles
from app.models.company import User
from app.models.attendance import AttendanceRecord
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/attendance", tags=["勤怠データ"])


class AttendanceCreate(BaseModel):
    employee_id: int
    year_month: int
    statutory_work_days: int | None = None
    work_days: int | None = None
    absence_days: int = 0
    late_count: int = 0
    early_leave_count: int = 0
    paid_leave_days: float = 0
    substitute_holiday_days: float = 0
    total_work_minutes: int | None = None
    regular_minutes: int | None = None
    overtime_within_statutory_minutes: int = 0
    overtime_statutory_minutes: int = 0
    night_minutes: int = 0
    statutory_holiday_minutes: int = 0
    non_statutory_holiday_minutes: int = 0
    night_overtime_minutes: int = 0
    night_holiday_minutes: int = 0
    night_overtime_holiday_minutes: int = 0
    notes: str | None = None


class AttendanceResponse(BaseModel):
    id: int
    company_id: int
    employee_id: int
    year_month: int
    statutory_work_days: int | None = None
    work_days: int | None = None
    absence_days: int
    late_count: int
    early_leave_count: int
    total_work_minutes: int | None = None
    regular_minutes: int | None = None
    overtime_within_statutory_minutes: int
    overtime_statutory_minutes: int
    night_minutes: int
    statutory_holiday_minutes: int
    non_statutory_holiday_minutes: int
    night_overtime_minutes: int
    night_holiday_minutes: int
    night_overtime_holiday_minutes: int

    model_config = {"from_attributes": True}


@router.get("", response_model=PaginatedResponse[AttendanceResponse])
async def list_attendance(
    year_month: int | None = None,
    employee_id: int | None = None,
    page: int = 1,
    limit: int = 50,
    user: User = Depends(require_roles("super_admin", "admin", "accountant")),
    db: AsyncSession = Depends(get_db),
):
    """勤怠データ一覧取得"""
    query = select(AttendanceRecord).where(
        AttendanceRecord.company_id == user.company_id
    )
    if year_month:
        query = query.where(AttendanceRecord.year_month == year_month)
    if employee_id:
        query = query.where(AttendanceRecord.employee_id == employee_id)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(AttendanceRecord.employee_id).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[AttendanceResponse.model_validate(a) for a in items],
        total=total, page=page, limit=limit,
        pages=(total + limit - 1) // limit,
    )


@router.post("", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
async def upsert_attendance(
    body: AttendanceCreate,
    user: User = Depends(require_roles("super_admin", "admin", "accountant")),
    db: AsyncSession = Depends(get_db),
):
    """勤怠データ登録/更新（UPSERT）"""
    result = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.company_id == user.company_id,
            AttendanceRecord.employee_id == body.employee_id,
            AttendanceRecord.year_month == body.year_month,
        )
    )
    record = result.scalar_one_or_none()

    if record:
        for key, value in body.model_dump(exclude={"employee_id", "year_month"}).items():
            setattr(record, key, value)
    else:
        record = AttendanceRecord(company_id=user.company_id, **body.model_dump())
        db.add(record)

    await db.flush()
    return AttendanceResponse.model_validate(record)


@router.post("/import", response_model=dict)
async def import_attendance_csv(
    file: UploadFile = File(...),
    year_month: int = 0,
    user: User = Depends(require_roles("super_admin", "admin", "accountant")),
    db: AsyncSession = Depends(get_db),
):
    """CSVインポート"""
    content = await file.read()
    decoded = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded))

    imported = 0
    for row in reader:
        ym = int(row.get("year_month", year_month))
        emp_id = int(row["employee_id"])

        result = await db.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.company_id == user.company_id,
                AttendanceRecord.employee_id == emp_id,
                AttendanceRecord.year_month == ym,
            )
        )
        record = result.scalar_one_or_none()

        data = {
            "work_days": int(row.get("work_days", 0)),
            "absence_days": int(row.get("absence_days", 0)),
            "regular_minutes": int(row.get("regular_minutes", 0)),
            "overtime_statutory_minutes": int(row.get("overtime_statutory_minutes", 0)),
            "night_minutes": int(row.get("night_minutes", 0)),
            "statutory_holiday_minutes": int(row.get("statutory_holiday_minutes", 0)),
            "total_work_minutes": int(row.get("total_work_minutes", 0)),
        }

        if record:
            for k, v in data.items():
                setattr(record, k, v)
        else:
            record = AttendanceRecord(
                company_id=user.company_id, employee_id=emp_id,
                year_month=ym, **data,
            )
            db.add(record)
        imported += 1

    await db.flush()
    return {"message": f"{imported}件の勤怠データをインポートしました", "count": imported}
