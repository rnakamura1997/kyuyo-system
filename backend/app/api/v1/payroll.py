"""給与計算API"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import date, datetime, timezone

from app.core.database import get_db
from app.api.deps import require_roles
from app.models.company import User
from app.models.payroll import (
    PayrollRecordGroup,
    PayrollRecord,
    PayrollRecordItem,
    PayrollSnapshot,
    PayrollHistory,
)
from app.models.attendance import PayrollPeriod
from app.models.employee import Employee
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/payroll", tags=["給与計算"])


# ---------------------------------------------------------------------------
# Inline Pydantic schemas
# ---------------------------------------------------------------------------

class CalculateRequest(BaseModel):
    payroll_period_id: int
    employee_ids: list[int] | None = None


class PayrollRecordItemResponse(BaseModel):
    id: int
    company_id: int
    payroll_record_id: int
    item_type: str
    item_code: str
    item_name: str
    amount: int
    quantity: float | None = None
    unit_price: float | None = None
    is_taxable: bool
    is_social_insurance_target: bool
    is_employment_insurance_target: bool
    display_order: int | None = None
    notes: str | None = None

    model_config = {"from_attributes": True}


class PayrollRecordResponse(BaseModel):
    id: int
    company_id: int
    payroll_record_group_id: int
    employee_id: int
    payroll_period_id: int
    version: int
    status: str
    payment_date: date
    total_earnings: int
    total_deductions: int
    net_pay: int
    calculation_details: dict | None = None
    confirmed_at: datetime | None = None
    confirmed_by: int | None = None
    cancelled_at: datetime | None = None
    cancelled_by: int | None = None
    cancellation_reason: str | None = None
    pdf_path: str | None = None

    model_config = {"from_attributes": True}


class PayrollRecordDetailResponse(PayrollRecordResponse):
    items: list[PayrollRecordItemResponse] = []


class ConfirmResponse(BaseModel):
    message: str
    record: PayrollRecordResponse


class CancelRequest(BaseModel):
    reason: str


class CancelResponse(BaseModel):
    message: str
    cancelled_record: PayrollRecordResponse
    new_record: PayrollRecordResponse


class PdfResponse(BaseModel):
    pdf_path: str


# ---------------------------------------------------------------------------
# Helper: resolve employee_id for the current user (employee role)
# ---------------------------------------------------------------------------

async def _get_employee_for_user(
    db: AsyncSession,
    user: User,
) -> Employee | None:
    """現在のユーザーに紐づく従業員レコードを取得"""
    result = await db.execute(
        select(Employee).where(
            Employee.company_id == user.company_id,
            Employee.email == user.email,
            Employee.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# POST /calculate – 給与計算
# ---------------------------------------------------------------------------

@router.post("/calculate", response_model=list[PayrollRecordResponse], status_code=status.HTTP_201_CREATED)
async def calculate_payroll(
    body: CalculateRequest,
    user: User = Depends(require_roles("super_admin", "admin", "accountant")),
    db: AsyncSession = Depends(get_db),
):
    """給与を計算し、明細レコードを作成する"""
    from app.services.payroll_calculator import PayrollCalculator

    # 給与期間の存在確認
    result = await db.execute(
        select(PayrollPeriod).where(
            PayrollPeriod.id == body.payroll_period_id,
            PayrollPeriod.company_id == user.company_id,
        )
    )
    period = result.scalar_one_or_none()
    if not period:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="給与期間が見つかりません",
        )

    # 対象従業員の取得
    emp_query = select(Employee).where(
        Employee.company_id == user.company_id,
        Employee.is_deleted == False,  # noqa: E712
    )
    if body.employee_ids:
        emp_query = emp_query.where(Employee.id.in_(body.employee_ids))
    emp_result = await db.execute(emp_query)
    employees = emp_result.scalars().all()

    if not employees:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="対象従業員が見つかりません",
        )

    calculator = PayrollCalculator(db, user.company_id)
    created_records: list[PayrollRecord] = []

    for emp in employees:
        # グループの取得または作成
        grp_result = await db.execute(
            select(PayrollRecordGroup).where(
                PayrollRecordGroup.company_id == user.company_id,
                PayrollRecordGroup.employee_id == emp.id,
                PayrollRecordGroup.payroll_period_id == body.payroll_period_id,
            )
        )
        group = grp_result.scalar_one_or_none()
        if not group:
            group = PayrollRecordGroup(
                company_id=user.company_id,
                employee_id=emp.id,
                payroll_period_id=body.payroll_period_id,
            )
            db.add(group)
            await db.flush()

        # 既存ドラフトがあればスキップ
        existing_draft = await db.execute(
            select(PayrollRecord).where(
                PayrollRecord.payroll_record_group_id == group.id,
                PayrollRecord.status == "draft",
            )
        )
        if existing_draft.scalar_one_or_none():
            continue

        # 現在の最大バージョンを取得
        max_ver_result = await db.execute(
            select(func.coalesce(func.max(PayrollRecord.version), 0)).where(
                PayrollRecord.payroll_record_group_id == group.id,
            )
        )
        max_version = max_ver_result.scalar() or 0

        # 給与計算
        calc_result = await calculator.calculate(emp, period)

        # PayrollRecord 作成
        record = PayrollRecord(
            company_id=user.company_id,
            payroll_record_group_id=group.id,
            employee_id=emp.id,
            payroll_period_id=body.payroll_period_id,
            version=max_version + 1,
            status="draft",
            payment_date=period.payment_date,
            total_earnings=calc_result["total_earnings"],
            total_deductions=calc_result["total_deductions"],
            net_pay=calc_result["net_pay"],
            calculation_details=calc_result.get("details"),
        )
        db.add(record)
        await db.flush()

        # グループの current_payroll_record_id を更新
        group.current_payroll_record_id = record.id

        # PayrollRecordItem 作成
        display_order = 0
        for item_data in calc_result.get("items", []):
            display_order += 1
            item = PayrollRecordItem(
                company_id=user.company_id,
                payroll_record_id=record.id,
                item_type=item_data["item_type"],
                item_code=item_data["item_code"],
                item_name=item_data["item_name"],
                amount=item_data["amount"],
                quantity=item_data.get("quantity"),
                unit_price=item_data.get("unit_price"),
                is_taxable=item_data.get("is_taxable", True),
                is_social_insurance_target=item_data.get("is_social_insurance_target", True),
                is_employment_insurance_target=item_data.get("is_employment_insurance_target", True),
                display_order=display_order,
                notes=item_data.get("notes"),
            )
            db.add(item)

        # PayrollHistory 作成
        history = PayrollHistory(
            company_id=user.company_id,
            payroll_record_id=record.id,
            action="calculated",
            changed_by=user.id,
            new_values={
                "status": "draft",
                "total_earnings": calc_result["total_earnings"],
                "total_deductions": calc_result["total_deductions"],
                "net_pay": calc_result["net_pay"],
            },
        )
        db.add(history)
        created_records.append(record)

    await db.flush()
    return [PayrollRecordResponse.model_validate(r) for r in created_records]


# ---------------------------------------------------------------------------
# GET /records – 給与明細一覧
# ---------------------------------------------------------------------------

@router.get("/records", response_model=PaginatedResponse[PayrollRecordResponse])
async def list_payroll_records(
    payroll_period_id: int | None = None,
    employee_id: int | None = None,
    status_filter: str | None = None,
    year_month: int | None = None,
    page: int = 1,
    limit: int = 50,
    user: User = Depends(require_roles("super_admin", "admin", "accountant", "employee")),
    db: AsyncSession = Depends(get_db),
):
    """給与明細レコード一覧を取得する"""
    user_roles = getattr(user, "_roles", [])
    is_admin = user.is_super_admin or any(
        r in user_roles for r in ("super_admin", "admin", "accountant")
    )

    query = select(PayrollRecord).where(
        PayrollRecord.company_id == user.company_id,
    )

    # 一般従業員は自身の明細のみ
    if not is_admin:
        emp = await _get_employee_for_user(db, user)
        if not emp:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="従業員情報が見つかりません",
            )
        query = query.where(PayrollRecord.employee_id == emp.id)

    if payroll_period_id is not None:
        query = query.where(PayrollRecord.payroll_period_id == payroll_period_id)
    if employee_id is not None and is_admin:
        query = query.where(PayrollRecord.employee_id == employee_id)
    if status_filter:
        query = query.where(PayrollRecord.status == status_filter)
    if year_month is not None:
        query = query.join(
            PayrollPeriod, PayrollRecord.payroll_period_id == PayrollPeriod.id
        ).where(PayrollPeriod.year_month == year_month)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(PayrollRecord.id.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[PayrollRecordResponse.model_validate(r) for r in items],
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit,
    )


# ---------------------------------------------------------------------------
# GET /records/{id} – 給与明細詳細
# ---------------------------------------------------------------------------

@router.get("/records/{record_id}", response_model=PayrollRecordDetailResponse)
async def get_payroll_record(
    record_id: int,
    user: User = Depends(require_roles("super_admin", "admin", "accountant", "employee")),
    db: AsyncSession = Depends(get_db),
):
    """給与明細レコードの詳細を取得する"""
    result = await db.execute(
        select(PayrollRecord).where(
            PayrollRecord.id == record_id,
            PayrollRecord.company_id == user.company_id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="給与明細が見つかりません",
        )

    # 従業員は自身の明細のみ閲覧可
    user_roles = getattr(user, "_roles", [])
    is_admin = user.is_super_admin or any(
        r in user_roles for r in ("super_admin", "admin", "accountant")
    )
    if not is_admin:
        emp = await _get_employee_for_user(db, user)
        if not emp or record.employee_id != emp.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="権限がありません",
            )

    # 明細項目を取得
    items_result = await db.execute(
        select(PayrollRecordItem)
        .where(PayrollRecordItem.payroll_record_id == record.id)
        .order_by(PayrollRecordItem.display_order)
    )
    items = items_result.scalars().all()

    response_data = PayrollRecordResponse.model_validate(record).model_dump()
    response_data["items"] = [PayrollRecordItemResponse.model_validate(i) for i in items]
    return PayrollRecordDetailResponse(**response_data)


# ---------------------------------------------------------------------------
# POST /records/{id}/confirm – 給与明細確定
# ---------------------------------------------------------------------------

@router.post("/records/{record_id}/confirm", response_model=ConfirmResponse)
async def confirm_payroll_record(
    record_id: int,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """給与明細を確定する"""
    result = await db.execute(
        select(PayrollRecord).where(
            PayrollRecord.id == record_id,
            PayrollRecord.company_id == user.company_id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="給与明細が見つかりません",
        )

    if record.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ステータスが '{record.status}' のため確定できません。ドラフトのみ確定可能です。",
        )

    now = datetime.now(timezone.utc)

    # ステータス更新
    record.status = "confirmed"
    record.confirmed_at = now
    record.confirmed_by = user.id

    # スナップショット作成
    items_result = await db.execute(
        select(PayrollRecordItem)
        .where(PayrollRecordItem.payroll_record_id == record.id)
        .order_by(PayrollRecordItem.display_order)
    )
    items = items_result.scalars().all()

    snapshot_data = {
        "record": {
            "id": record.id,
            "employee_id": record.employee_id,
            "version": record.version,
            "payment_date": record.payment_date.isoformat(),
            "total_earnings": record.total_earnings,
            "total_deductions": record.total_deductions,
            "net_pay": record.net_pay,
            "calculation_details": record.calculation_details,
        },
        "items": [
            {
                "item_type": item.item_type,
                "item_code": item.item_code,
                "item_name": item.item_name,
                "amount": item.amount,
                "is_taxable": item.is_taxable,
            }
            for item in items
        ],
        "confirmed_at": now.isoformat(),
        "confirmed_by": user.id,
    }

    snapshot = PayrollSnapshot(
        company_id=user.company_id,
        payroll_record_id=record.id,
        snapshot_data=snapshot_data,
    )
    db.add(snapshot)

    # 履歴作成
    history = PayrollHistory(
        company_id=user.company_id,
        payroll_record_id=record.id,
        action="confirmed",
        changed_by=user.id,
        old_values={"status": "draft"},
        new_values={"status": "confirmed", "confirmed_at": now.isoformat()},
    )
    db.add(history)

    await db.flush()
    return ConfirmResponse(
        message="給与明細を確定しました",
        record=PayrollRecordResponse.model_validate(record),
    )


# ---------------------------------------------------------------------------
# POST /records/{id}/cancel – 給与明細取消
# ---------------------------------------------------------------------------

@router.post("/records/{record_id}/cancel", response_model=CancelResponse)
async def cancel_payroll_record(
    record_id: int,
    body: CancelRequest,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """確定済みの給与明細を取り消し、新バージョンのドラフトを作成する"""
    result = await db.execute(
        select(PayrollRecord).where(
            PayrollRecord.id == record_id,
            PayrollRecord.company_id == user.company_id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="給与明細が見つかりません",
        )

    if record.status != "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ステータスが '{record.status}' のため取消できません。確定済みのみ取消可能です。",
        )

    now = datetime.now(timezone.utc)

    # 元レコードを取消
    record.status = "cancelled"
    record.cancelled_at = now
    record.cancelled_by = user.id
    record.cancellation_reason = body.reason

    # 取消履歴
    cancel_history = PayrollHistory(
        company_id=user.company_id,
        payroll_record_id=record.id,
        action="cancelled",
        changed_by=user.id,
        old_values={"status": "confirmed"},
        new_values={
            "status": "cancelled",
            "cancelled_at": now.isoformat(),
            "cancellation_reason": body.reason,
        },
        reason=body.reason,
    )
    db.add(cancel_history)

    # 新バージョンのドラフト作成
    new_record = PayrollRecord(
        company_id=user.company_id,
        payroll_record_group_id=record.payroll_record_group_id,
        employee_id=record.employee_id,
        payroll_period_id=record.payroll_period_id,
        version=record.version + 1,
        status="draft",
        payment_date=record.payment_date,
        total_earnings=record.total_earnings,
        total_deductions=record.total_deductions,
        net_pay=record.net_pay,
        calculation_details=record.calculation_details,
    )
    db.add(new_record)
    await db.flush()

    # 元レコードの明細項目をコピー
    items_result = await db.execute(
        select(PayrollRecordItem)
        .where(PayrollRecordItem.payroll_record_id == record.id)
        .order_by(PayrollRecordItem.display_order)
    )
    for old_item in items_result.scalars().all():
        new_item = PayrollRecordItem(
            company_id=user.company_id,
            payroll_record_id=new_record.id,
            item_type=old_item.item_type,
            item_code=old_item.item_code,
            item_name=old_item.item_name,
            amount=old_item.amount,
            quantity=old_item.quantity,
            unit_price=old_item.unit_price,
            is_taxable=old_item.is_taxable,
            is_social_insurance_target=old_item.is_social_insurance_target,
            is_employment_insurance_target=old_item.is_employment_insurance_target,
            display_order=old_item.display_order,
            notes=old_item.notes,
        )
        db.add(new_item)

    # グループの current_payroll_record_id を更新
    grp_result = await db.execute(
        select(PayrollRecordGroup).where(
            PayrollRecordGroup.id == record.payroll_record_group_id,
        )
    )
    group = grp_result.scalar_one_or_none()
    if group:
        group.current_payroll_record_id = new_record.id

    # 新バージョン作成履歴
    new_history = PayrollHistory(
        company_id=user.company_id,
        payroll_record_id=new_record.id,
        action="created_from_cancellation",
        changed_by=user.id,
        new_values={
            "status": "draft",
            "version": new_record.version,
            "source_record_id": record.id,
        },
        reason=f"レコード #{record.id} の取消により新規作成",
    )
    db.add(new_history)

    await db.flush()
    return CancelResponse(
        message="給与明細を取り消し、新バージョンのドラフトを作成しました",
        cancelled_record=PayrollRecordResponse.model_validate(record),
        new_record=PayrollRecordResponse.model_validate(new_record),
    )


# ---------------------------------------------------------------------------
# POST /records/{id}/pdf – PDF生成
# ---------------------------------------------------------------------------

@router.post("/records/{record_id}/pdf", response_model=PdfResponse)
async def generate_payroll_pdf(
    record_id: int,
    user: User = Depends(require_roles("super_admin", "admin", "accountant")),
    db: AsyncSession = Depends(get_db),
):
    """給与明細のPDFを生成する"""
    from app.services.pdf_generator import generate_payroll_pdf as _generate_pdf

    result = await db.execute(
        select(PayrollRecord).where(
            PayrollRecord.id == record_id,
            PayrollRecord.company_id == user.company_id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="給与明細が見つかりません",
        )

    # 明細項目を取得
    items_result = await db.execute(
        select(PayrollRecordItem)
        .where(PayrollRecordItem.payroll_record_id == record.id)
        .order_by(PayrollRecordItem.display_order)
    )
    items = items_result.scalars().all()

    # PDF生成（サービス呼び出し）
    pdf_path = await _generate_pdf(record, items)

    record.pdf_path = pdf_path
    await db.flush()

    return PdfResponse(pdf_path=pdf_path)
