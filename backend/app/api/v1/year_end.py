"""年末調整API"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import date, datetime, timezone

from app.core.database import get_db
from app.api.deps import require_roles
from app.models.company import User
from app.models.year_end import (
    YearEndAdjustment,
    YearEndAdjustmentHistory,
    DeductionCertificate,
    TaxWithholdingSlip,
)
from app.models.employee import Employee
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/year-end", tags=["年末調整"])


# ---------------------------------------------------------------------------
# Inline Pydantic schemas
# ---------------------------------------------------------------------------

class AdjustmentCreateRequest(BaseModel):
    employee_id: int
    target_year: int
    basic_deduction: int = 0
    spouse_deduction: int = 0
    dependent_deduction: int = 0
    disability_deduction: int = 0
    widow_deduction: int = 0
    working_student_deduction: int = 0
    social_insurance_premium: int = 0
    small_business_mutual_aid: int = 0
    life_insurance_premium: int = 0
    earthquake_insurance_premium: int = 0
    housing_loan_deduction: int = 0
    spouse_info: dict | None = None
    dependent_info: dict | None = None
    insurance_info: dict | None = None


class AdjustmentUpdateRequest(BaseModel):
    basic_deduction: int | None = None
    spouse_deduction: int | None = None
    dependent_deduction: int | None = None
    disability_deduction: int | None = None
    widow_deduction: int | None = None
    working_student_deduction: int | None = None
    social_insurance_premium: int | None = None
    small_business_mutual_aid: int | None = None
    life_insurance_premium: int | None = None
    earthquake_insurance_premium: int | None = None
    housing_loan_deduction: int | None = None
    annual_income: int | None = None
    annual_withheld_tax: int | None = None
    annual_calculated_tax: int | None = None
    spouse_info: dict | None = None
    dependent_info: dict | None = None
    insurance_info: dict | None = None


class CertificateResponse(BaseModel):
    id: int
    company_id: int
    year_end_adjustment_id: int
    certificate_type: str
    file_path: str
    file_name: str
    file_size: int | None = None
    uploaded_at: datetime | None = None

    model_config = {"from_attributes": True}


class WithholdingSlipResponse(BaseModel):
    id: int
    company_id: int
    year_end_adjustment_id: int
    employee_id: int
    target_year: int
    issue_date: date
    slip_data: dict
    pdf_path: str | None = None

    model_config = {"from_attributes": True}


class AdjustmentResponse(BaseModel):
    id: int
    company_id: int
    employee_id: int
    target_year: int
    status: str
    basic_deduction: int
    spouse_deduction: int
    dependent_deduction: int
    disability_deduction: int
    widow_deduction: int
    working_student_deduction: int
    social_insurance_premium: int
    small_business_mutual_aid: int
    life_insurance_premium: int
    earthquake_insurance_premium: int
    housing_loan_deduction: int
    annual_income: int | None = None
    annual_withheld_tax: int | None = None
    annual_calculated_tax: int | None = None
    adjustment_amount: int | None = None
    spouse_info: dict | None = None
    dependent_info: dict | None = None
    insurance_info: dict | None = None
    submitted_at: datetime | None = None
    returned_at: datetime | None = None
    return_reason: str | None = None
    approved_at: datetime | None = None
    approved_by: int | None = None
    confirmed_at: datetime | None = None
    confirmed_by: int | None = None

    model_config = {"from_attributes": True}


class AdjustmentDetailResponse(AdjustmentResponse):
    certificates: list[CertificateResponse] = []
    withholding_slip: WithholdingSlipResponse | None = None


class ReturnRequest(BaseModel):
    reason: str


class StatusChangeResponse(BaseModel):
    message: str
    adjustment: AdjustmentResponse


# ---------------------------------------------------------------------------
# Helper: resolve employee_id for the current user
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


def _is_admin_user(user: User) -> bool:
    """ユーザーが管理者権限を持つか判定"""
    user_roles = getattr(user, "_roles", [])
    return user.is_super_admin or any(
        r in user_roles for r in ("super_admin", "admin", "accountant")
    )


# ---------------------------------------------------------------------------
# GET /adjustments – 年末調整一覧
# ---------------------------------------------------------------------------

@router.get("/adjustments", response_model=PaginatedResponse[AdjustmentResponse])
async def list_adjustments(
    target_year: int | None = None,
    status_filter: str | None = None,
    employee_id: int | None = None,
    page: int = 1,
    limit: int = 50,
    user: User = Depends(require_roles("super_admin", "admin", "accountant")),
    db: AsyncSession = Depends(get_db),
):
    """年末調整の一覧を取得する"""
    query = select(YearEndAdjustment).where(
        YearEndAdjustment.company_id == user.company_id,
    )

    if target_year is not None:
        query = query.where(YearEndAdjustment.target_year == target_year)
    if status_filter:
        query = query.where(YearEndAdjustment.status == status_filter)
    if employee_id is not None:
        query = query.where(YearEndAdjustment.employee_id == employee_id)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(YearEndAdjustment.id.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[AdjustmentResponse.model_validate(a) for a in items],
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit,
    )


# ---------------------------------------------------------------------------
# POST /adjustments – 年末調整作成
# ---------------------------------------------------------------------------

@router.post("/adjustments", response_model=AdjustmentResponse, status_code=status.HTTP_201_CREATED)
async def create_adjustment(
    body: AdjustmentCreateRequest,
    user: User = Depends(require_roles("super_admin", "admin", "accountant", "employee")),
    db: AsyncSession = Depends(get_db),
):
    """年末調整を新規作成する"""
    is_admin = _is_admin_user(user)

    # 従業員の権限チェック（従業員は自分自身のみ）
    if not is_admin:
        emp = await _get_employee_for_user(db, user)
        if not emp or emp.id != body.employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="自分以外の年末調整は作成できません",
            )

    # 対象従業員の存在確認
    emp_result = await db.execute(
        select(Employee).where(
            Employee.id == body.employee_id,
            Employee.company_id == user.company_id,
            Employee.is_deleted == False,  # noqa: E712
        )
    )
    if not emp_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="従業員が見つかりません",
        )

    # ユニーク制約チェック (company_id + employee_id + target_year)
    existing = await db.execute(
        select(YearEndAdjustment).where(
            YearEndAdjustment.company_id == user.company_id,
            YearEndAdjustment.employee_id == body.employee_id,
            YearEndAdjustment.target_year == body.target_year,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"この従業員の{body.target_year}年度の年末調整は既に存在します",
        )

    adjustment = YearEndAdjustment(
        company_id=user.company_id,
        status="draft",
        **body.model_dump(),
    )
    db.add(adjustment)
    await db.flush()

    # 作成履歴
    history = YearEndAdjustmentHistory(
        company_id=user.company_id,
        year_end_adjustment_id=adjustment.id,
        action="created",
        changed_by=user.id,
        new_status="draft",
    )
    db.add(history)
    await db.flush()

    return AdjustmentResponse.model_validate(adjustment)


# ---------------------------------------------------------------------------
# GET /adjustments/{id} – 年末調整詳細
# ---------------------------------------------------------------------------

@router.get("/adjustments/{adjustment_id}", response_model=AdjustmentDetailResponse)
async def get_adjustment(
    adjustment_id: int,
    user: User = Depends(require_roles("super_admin", "admin", "accountant", "employee")),
    db: AsyncSession = Depends(get_db),
):
    """年末調整の詳細を証明書一覧と共に取得する"""
    result = await db.execute(
        select(YearEndAdjustment).where(
            YearEndAdjustment.id == adjustment_id,
            YearEndAdjustment.company_id == user.company_id,
        )
    )
    adjustment = result.scalar_one_or_none()
    if not adjustment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="年末調整が見つかりません",
        )

    # 従業員は自身のもののみ閲覧可
    is_admin = _is_admin_user(user)
    if not is_admin:
        emp = await _get_employee_for_user(db, user)
        if not emp or adjustment.employee_id != emp.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="権限がありません",
            )

    # 証明書一覧
    certs_result = await db.execute(
        select(DeductionCertificate).where(
            DeductionCertificate.year_end_adjustment_id == adjustment.id,
        )
    )
    certificates = certs_result.scalars().all()

    # 源泉徴収票
    slip_result = await db.execute(
        select(TaxWithholdingSlip).where(
            TaxWithholdingSlip.year_end_adjustment_id == adjustment.id,
        )
    )
    withholding_slip = slip_result.scalar_one_or_none()

    response_data = AdjustmentResponse.model_validate(adjustment).model_dump()
    response_data["certificates"] = [CertificateResponse.model_validate(c) for c in certificates]
    response_data["withholding_slip"] = (
        WithholdingSlipResponse.model_validate(withholding_slip) if withholding_slip else None
    )
    return AdjustmentDetailResponse(**response_data)


# ---------------------------------------------------------------------------
# PUT /adjustments/{id} – 年末調整更新
# ---------------------------------------------------------------------------

@router.put("/adjustments/{adjustment_id}", response_model=AdjustmentResponse)
async def update_adjustment(
    adjustment_id: int,
    body: AdjustmentUpdateRequest,
    user: User = Depends(require_roles("super_admin", "admin", "accountant", "employee")),
    db: AsyncSession = Depends(get_db),
):
    """年末調整を更新する（draft / returned のみ）"""
    result = await db.execute(
        select(YearEndAdjustment).where(
            YearEndAdjustment.id == adjustment_id,
            YearEndAdjustment.company_id == user.company_id,
        )
    )
    adjustment = result.scalar_one_or_none()
    if not adjustment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="年末調整が見つかりません",
        )

    if adjustment.status not in ("draft", "returned"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ステータスが '{adjustment.status}' のため更新できません。draft または returned のみ更新可能です。",
        )

    # 従業員は自身のもののみ（かつ draft/returned のみ）
    is_admin = _is_admin_user(user)
    if not is_admin:
        emp = await _get_employee_for_user(db, user)
        if not emp or adjustment.employee_id != emp.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="権限がありません",
            )

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(adjustment, key, value)

    await db.flush()
    return AdjustmentResponse.model_validate(adjustment)


# ---------------------------------------------------------------------------
# POST /adjustments/{id}/submit – 提出
# ---------------------------------------------------------------------------

@router.post("/adjustments/{adjustment_id}/submit", response_model=StatusChangeResponse)
async def submit_adjustment(
    adjustment_id: int,
    user: User = Depends(require_roles("super_admin", "admin", "accountant", "employee")),
    db: AsyncSession = Depends(get_db),
):
    """年末調整を提出する"""
    result = await db.execute(
        select(YearEndAdjustment).where(
            YearEndAdjustment.id == adjustment_id,
            YearEndAdjustment.company_id == user.company_id,
        )
    )
    adjustment = result.scalar_one_or_none()
    if not adjustment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="年末調整が見つかりません",
        )

    if adjustment.status not in ("draft", "returned"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ステータスが '{adjustment.status}' のため提出できません。draft または returned のみ提出可能です。",
        )

    # 従業員は自身のもののみ
    is_admin = _is_admin_user(user)
    if not is_admin:
        emp = await _get_employee_for_user(db, user)
        if not emp or adjustment.employee_id != emp.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="権限がありません",
            )

    now = datetime.now(timezone.utc)
    old_status = adjustment.status

    adjustment.status = "submitted"
    adjustment.submitted_at = now

    history = YearEndAdjustmentHistory(
        company_id=user.company_id,
        year_end_adjustment_id=adjustment.id,
        action="submitted",
        changed_by=user.id,
        old_status=old_status,
        new_status="submitted",
    )
    db.add(history)

    await db.flush()
    return StatusChangeResponse(
        message="年末調整を提出しました",
        adjustment=AdjustmentResponse.model_validate(adjustment),
    )


# ---------------------------------------------------------------------------
# POST /adjustments/{id}/approve – 承認
# ---------------------------------------------------------------------------

@router.post("/adjustments/{adjustment_id}/approve", response_model=StatusChangeResponse)
async def approve_adjustment(
    adjustment_id: int,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """年末調整を承認する"""
    result = await db.execute(
        select(YearEndAdjustment).where(
            YearEndAdjustment.id == adjustment_id,
            YearEndAdjustment.company_id == user.company_id,
        )
    )
    adjustment = result.scalar_one_or_none()
    if not adjustment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="年末調整が見つかりません",
        )

    if adjustment.status != "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ステータスが '{adjustment.status}' のため承認できません。submitted のみ承認可能です。",
        )

    now = datetime.now(timezone.utc)
    adjustment.status = "approved"
    adjustment.approved_at = now
    adjustment.approved_by = user.id

    history = YearEndAdjustmentHistory(
        company_id=user.company_id,
        year_end_adjustment_id=adjustment.id,
        action="approved",
        changed_by=user.id,
        old_status="submitted",
        new_status="approved",
    )
    db.add(history)

    await db.flush()
    return StatusChangeResponse(
        message="年末調整を承認しました",
        adjustment=AdjustmentResponse.model_validate(adjustment),
    )


# ---------------------------------------------------------------------------
# POST /adjustments/{id}/return – 差戻し
# ---------------------------------------------------------------------------

@router.post("/adjustments/{adjustment_id}/return", response_model=StatusChangeResponse)
async def return_adjustment(
    adjustment_id: int,
    body: ReturnRequest,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """年末調整を差し戻す"""
    result = await db.execute(
        select(YearEndAdjustment).where(
            YearEndAdjustment.id == adjustment_id,
            YearEndAdjustment.company_id == user.company_id,
        )
    )
    adjustment = result.scalar_one_or_none()
    if not adjustment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="年末調整が見つかりません",
        )

    if adjustment.status != "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ステータスが '{adjustment.status}' のため差戻しできません。submitted のみ差戻し可能です。",
        )

    now = datetime.now(timezone.utc)
    adjustment.status = "returned"
    adjustment.returned_at = now
    adjustment.return_reason = body.reason

    history = YearEndAdjustmentHistory(
        company_id=user.company_id,
        year_end_adjustment_id=adjustment.id,
        action="returned",
        changed_by=user.id,
        old_status="submitted",
        new_status="returned",
        reason=body.reason,
    )
    db.add(history)

    await db.flush()
    return StatusChangeResponse(
        message="年末調整を差し戻しました",
        adjustment=AdjustmentResponse.model_validate(adjustment),
    )


# ---------------------------------------------------------------------------
# POST /adjustments/{id}/confirm – 最終確定
# ---------------------------------------------------------------------------

@router.post("/adjustments/{adjustment_id}/confirm", response_model=StatusChangeResponse)
async def confirm_adjustment(
    adjustment_id: int,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """年末調整を最終確定する（調整額を計算）"""
    result = await db.execute(
        select(YearEndAdjustment).where(
            YearEndAdjustment.id == adjustment_id,
            YearEndAdjustment.company_id == user.company_id,
        )
    )
    adjustment = result.scalar_one_or_none()
    if not adjustment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="年末調整が見つかりません",
        )

    if adjustment.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ステータスが '{adjustment.status}' のため確定できません。approved のみ確定可能です。",
        )

    # 年間算出税額と年間源泉徴収税額が必要
    if adjustment.annual_calculated_tax is None or adjustment.annual_withheld_tax is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="年間算出税額 (annual_calculated_tax) と年間源泉徴収税額 (annual_withheld_tax) を設定してから確定してください。",
        )

    now = datetime.now(timezone.utc)

    # 調整額 = 年間算出税額 - 年間源泉徴収税額
    # 正の値 → 追加徴収、負の値 → 還付
    adjustment.adjustment_amount = adjustment.annual_calculated_tax - adjustment.annual_withheld_tax
    adjustment.status = "confirmed"
    adjustment.confirmed_at = now
    adjustment.confirmed_by = user.id

    history = YearEndAdjustmentHistory(
        company_id=user.company_id,
        year_end_adjustment_id=adjustment.id,
        action="confirmed",
        changed_by=user.id,
        old_status="approved",
        new_status="confirmed",
    )
    db.add(history)

    await db.flush()
    return StatusChangeResponse(
        message=f"年末調整を確定しました。調整額: {adjustment.adjustment_amount:,}円",
        adjustment=AdjustmentResponse.model_validate(adjustment),
    )


# ---------------------------------------------------------------------------
# POST /adjustments/{id}/certificates – 証明書アップロード
# ---------------------------------------------------------------------------

@router.post(
    "/adjustments/{adjustment_id}/certificates",
    response_model=CertificateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_certificate(
    adjustment_id: int,
    certificate_type: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(require_roles("super_admin", "admin", "accountant", "employee")),
    db: AsyncSession = Depends(get_db),
):
    """控除証明書をアップロードする"""
    result = await db.execute(
        select(YearEndAdjustment).where(
            YearEndAdjustment.id == adjustment_id,
            YearEndAdjustment.company_id == user.company_id,
        )
    )
    adjustment = result.scalar_one_or_none()
    if not adjustment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="年末調整が見つかりません",
        )

    # 従業員は自身のもののみ
    is_admin = _is_admin_user(user)
    if not is_admin:
        emp = await _get_employee_for_user(db, user)
        if not emp or adjustment.employee_id != emp.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="権限がありません",
            )

    # ファイルサイズの取得
    content = await file.read()
    file_size = len(content)

    # ファイル保存パスの生成
    import os
    upload_dir = f"uploads/certificates/{user.company_id}/{adjustment.target_year}"
    os.makedirs(upload_dir, exist_ok=True)

    safe_filename = f"{adjustment.id}_{certificate_type}_{file.filename}"
    file_path = os.path.join(upload_dir, safe_filename)

    with open(file_path, "wb") as f:
        f.write(content)

    certificate = DeductionCertificate(
        company_id=user.company_id,
        year_end_adjustment_id=adjustment.id,
        certificate_type=certificate_type,
        file_path=file_path,
        file_name=file.filename or safe_filename,
        file_size=file_size,
    )
    db.add(certificate)
    await db.flush()

    return CertificateResponse.model_validate(certificate)


# ---------------------------------------------------------------------------
# POST /adjustments/{id}/withholding-slip – 源泉徴収票生成
# ---------------------------------------------------------------------------

@router.post(
    "/adjustments/{adjustment_id}/withholding-slip",
    response_model=WithholdingSlipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_withholding_slip(
    adjustment_id: int,
    user: User = Depends(require_roles("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """源泉徴収票を生成する"""
    result = await db.execute(
        select(YearEndAdjustment).where(
            YearEndAdjustment.id == adjustment_id,
            YearEndAdjustment.company_id == user.company_id,
        )
    )
    adjustment = result.scalar_one_or_none()
    if not adjustment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="年末調整が見つかりません",
        )

    if adjustment.status != "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="確定済みの年末調整のみ源泉徴収票を生成できます。",
        )

    # 既存の源泉徴収票がある場合はエラー
    existing = await db.execute(
        select(TaxWithholdingSlip).where(
            TaxWithholdingSlip.year_end_adjustment_id == adjustment.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="この年末調整の源泉徴収票は既に存在します",
        )

    # 従業員情報の取得
    emp_result = await db.execute(
        select(Employee).where(
            Employee.id == adjustment.employee_id,
            Employee.company_id == user.company_id,
        )
    )
    employee = emp_result.scalar_one_or_none()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="従業員情報が見つかりません",
        )

    # 源泉徴収票データの組み立て
    today = date.today()
    slip_data = {
        "employee_name": f"{employee.last_name} {employee.first_name}",
        "employee_name_kana": f"{employee.last_name_kana or ''} {employee.first_name_kana or ''}",
        "address": employee.address,
        "birth_date": employee.birth_date.isoformat() if employee.birth_date else None,
        "target_year": adjustment.target_year,
        "annual_income": adjustment.annual_income,
        "income_deduction": None,
        "taxable_income": None,
        "annual_withheld_tax": adjustment.annual_withheld_tax,
        "annual_calculated_tax": adjustment.annual_calculated_tax,
        "adjustment_amount": adjustment.adjustment_amount,
        "deductions": {
            "basic_deduction": adjustment.basic_deduction,
            "spouse_deduction": adjustment.spouse_deduction,
            "dependent_deduction": adjustment.dependent_deduction,
            "disability_deduction": adjustment.disability_deduction,
            "widow_deduction": adjustment.widow_deduction,
            "working_student_deduction": adjustment.working_student_deduction,
            "social_insurance_premium": adjustment.social_insurance_premium,
            "small_business_mutual_aid": adjustment.small_business_mutual_aid,
            "life_insurance_premium": adjustment.life_insurance_premium,
            "earthquake_insurance_premium": adjustment.earthquake_insurance_premium,
            "housing_loan_deduction": adjustment.housing_loan_deduction,
        },
        "spouse_info": adjustment.spouse_info,
        "dependent_info": adjustment.dependent_info,
        "insurance_info": adjustment.insurance_info,
        "social_insurance_enrolled": employee.social_insurance_enrolled,
        "pension_insurance_enrolled": employee.pension_insurance_enrolled,
        "employment_insurance_enrolled": employee.employment_insurance_enrolled,
    }

    slip = TaxWithholdingSlip(
        company_id=user.company_id,
        year_end_adjustment_id=adjustment.id,
        employee_id=employee.id,
        target_year=adjustment.target_year,
        issue_date=today,
        slip_data=slip_data,
    )
    db.add(slip)
    await db.flush()

    return WithholdingSlipResponse.model_validate(slip)
