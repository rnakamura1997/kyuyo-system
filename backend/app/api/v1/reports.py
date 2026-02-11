"""帳票出力API"""

import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.api.deps import require_roles
from app.models.company import User, Company
from app.models.payroll import PayrollRecord, PayrollRecordItem
from app.models.attendance import PayrollPeriod
from app.models.employee import Employee
from app.models.notification import AccountingMapping, BankTransferExport

router = APIRouter(prefix="/reports", tags=["帳票出力"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PayrollLedgerEntry(BaseModel):
    employee_id: int
    employee_code: str
    employee_name: str
    department: str | None = None
    total_earnings: int
    total_deductions: int
    net_pay: int

    model_config = {"from_attributes": True}


class PayrollLedgerResponse(BaseModel):
    year_month: int
    entries: list[PayrollLedgerEntry]
    grand_total_earnings: int
    grand_total_deductions: int
    grand_total_net_pay: int


class MonthlySummaryResponse(BaseModel):
    year_month: int
    total_employees: int
    total_earnings: int
    total_deductions: int
    total_net_pay: int
    by_status: dict


# ---------------------------------------------------------------------------
# GET /payroll-ledger – 賃金台帳
# ---------------------------------------------------------------------------

@router.get("/payroll-ledger")
async def payroll_ledger(
    year_month: int,
    format: str = "json",
    user: User = Depends(require_roles("super_admin", "admin", "accountant")),
    db: AsyncSession = Depends(get_db),
):
    """賃金台帳を生成する"""
    # 給与期間を取得
    period_result = await db.execute(
        select(PayrollPeriod).where(
            PayrollPeriod.company_id == user.company_id,
            PayrollPeriod.year_month == year_month,
        )
    )
    period = period_result.scalar_one_or_none()

    # 給与明細を取得（確定済みのみ）
    query = select(PayrollRecord, Employee).join(
        Employee, PayrollRecord.employee_id == Employee.id
    ).where(
        PayrollRecord.company_id == user.company_id,
        PayrollRecord.status == "confirmed",
    )

    if period:
        query = query.where(PayrollRecord.payroll_period_id == period.id)
    else:
        # 期間がない場合はyear_monthでPayrollPeriodをJOIN
        query = query.join(
            PayrollPeriod, PayrollRecord.payroll_period_id == PayrollPeriod.id
        ).where(PayrollPeriod.year_month == year_month)

    result = await db.execute(query.order_by(Employee.employee_code))
    rows = result.all()

    entries = []
    grand_earnings = 0
    grand_deductions = 0
    grand_net = 0

    for record, emp in rows:
        entry = PayrollLedgerEntry(
            employee_id=emp.id,
            employee_code=emp.employee_code,
            employee_name=f"{emp.last_name} {emp.first_name}",
            department=emp.department,
            total_earnings=record.total_earnings,
            total_deductions=record.total_deductions,
            net_pay=record.net_pay,
        )
        entries.append(entry)
        grand_earnings += record.total_earnings
        grand_deductions += record.total_deductions
        grand_net += record.net_pay

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["社員コード", "氏名", "部署", "支給額合計", "控除額合計", "差引支給額"])
        for e in entries:
            writer.writerow([
                e.employee_code, e.employee_name, e.department or "",
                e.total_earnings, e.total_deductions, e.net_pay,
            ])
        writer.writerow(["合計", "", "", grand_earnings, grand_deductions, grand_net])
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=payroll_ledger_{year_month}.csv"},
        )

    return PayrollLedgerResponse(
        year_month=year_month,
        entries=entries,
        grand_total_earnings=grand_earnings,
        grand_total_deductions=grand_deductions,
        grand_total_net_pay=grand_net,
    )


# ---------------------------------------------------------------------------
# GET /bank-transfer – 全銀フォーマット振込データ
# ---------------------------------------------------------------------------

@router.get("/bank-transfer")
async def bank_transfer(
    payroll_period_id: int,
    user: User = Depends(require_roles("super_admin", "admin", "accountant")),
    db: AsyncSession = Depends(get_db),
):
    """全銀フォーマットの振込データを生成する"""
    # 会社情報取得
    company_result = await db.execute(
        select(Company).where(Company.company_id == user.company_id)
    )
    company = company_result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="会社情報が見つかりません")

    # 確定済み給与明細を取得
    records_result = await db.execute(
        select(PayrollRecord, Employee)
        .join(Employee, PayrollRecord.employee_id == Employee.id)
        .where(
            PayrollRecord.company_id == user.company_id,
            PayrollRecord.payroll_period_id == payroll_period_id,
            PayrollRecord.status == "confirmed",
        )
        .order_by(Employee.employee_code)
    )
    rows = records_result.all()

    if not rows:
        raise HTTPException(status_code=404, detail="確定済み給与明細が見つかりません")

    # 全銀フォーマット生成（固定長120バイト）
    lines = []
    payment_date = rows[0][0].payment_date

    # ヘッダーレコード（レコード区分1）
    header = "1"                                    # 区分
    header += "21"                                  # 種別（総合振込）
    header += "0"                                   # コード区分（JIS）
    header += " " * 10                              # 委託者コード
    header += (company.name or "")[:40].ljust(40)  # 委託者名
    header += payment_date.strftime("%m%d")         # 振込日
    header += " " * 15                              # 仕向銀行
    header += " " * 15                              # 仕向支店
    header += " " * 4                               # 預金種目
    header += " " * 7                               # 口座番号
    header += " " * 17                              # ダミー
    lines.append(header[:120].ljust(120))

    # データレコード（レコード区分2）
    total_amount = 0
    record_count = 0

    for record, emp in rows:
        data = "2"                                           # 区分
        data += " " * 4                                      # 銀行コード
        data += (emp.bank_name or "")[:15].ljust(15)        # 銀行名
        data += " " * 3                                      # 支店コード
        data += (emp.branch_name or "")[:15].ljust(15)      # 支店名
        data += " " * 4                                      # ダミー

        account_type_code = "1" if emp.account_type == "savings" else "2"
        data += account_type_code                            # 預金種目
        data += (emp.account_number or "")[:7].ljust(7)     # 口座番号
        data += (emp.account_holder or f"{emp.last_name}{emp.first_name}")[:30].ljust(30)  # 受取人名
        data += str(record.net_pay).rjust(10, "0")           # 金額
        data += "0"                                          # 新規コード
        data += " " * 20                                     # ダミー
        lines.append(data[:120].ljust(120))
        total_amount += record.net_pay
        record_count += 1

    # トレーラーレコード（レコード区分8）
    trailer = "8"
    trailer += str(record_count).rjust(6, "0")               # 合計件数
    trailer += str(total_amount).rjust(12, "0")               # 合計金額
    trailer += " " * 101                                       # ダミー
    lines.append(trailer[:120].ljust(120))

    # エンドレコード（レコード区分9）
    lines.append("9" + " " * 119)

    content = "\r\n".join(lines) + "\r\n"

    # BankTransferExportレコード作成
    export = BankTransferExport(
        company_id=user.company_id,
        export_date=date.today(),
        payment_date=payment_date,
        file_path=f"bank_transfer_{payroll_period_id}_{date.today().isoformat()}.txt",
        record_count=record_count,
        total_amount=total_amount,
        created_by=user.id,
    )
    db.add(export)
    await db.flush()

    return StreamingResponse(
        io.BytesIO(content.encode("shift_jis", errors="replace")),
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=zengin_{payroll_period_id}.txt",
        },
    )


# ---------------------------------------------------------------------------
# GET /accounting-journal – 会計仕訳データ
# ---------------------------------------------------------------------------

@router.get("/accounting-journal")
async def accounting_journal(
    payroll_period_id: int,
    user: User = Depends(require_roles("super_admin", "admin", "accountant")),
    db: AsyncSession = Depends(get_db),
):
    """会計仕訳CSVを生成する"""
    # マッピング取得
    mapping_result = await db.execute(
        select(AccountingMapping).where(
            AccountingMapping.company_id == user.company_id
        )
    )
    mappings = {(m.item_type, m.item_code): m for m in mapping_result.scalars().all()}

    # 給与明細項目を集計
    items_result = await db.execute(
        select(
            PayrollRecordItem.item_type,
            PayrollRecordItem.item_code,
            PayrollRecordItem.item_name,
            func.sum(PayrollRecordItem.amount).label("total_amount"),
        )
        .join(PayrollRecord, PayrollRecordItem.payroll_record_id == PayrollRecord.id)
        .where(
            PayrollRecord.company_id == user.company_id,
            PayrollRecord.payroll_period_id == payroll_period_id,
            PayrollRecord.status == "confirmed",
        )
        .group_by(
            PayrollRecordItem.item_type,
            PayrollRecordItem.item_code,
            PayrollRecordItem.item_name,
        )
        .order_by(PayrollRecordItem.item_type, PayrollRecordItem.item_code)
    )
    aggregated = items_result.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["借方科目コード", "借方科目名", "貸方科目コード", "貸方科目名", "金額", "摘要"])

    for row in aggregated:
        mapping = mappings.get((row.item_type, row.item_code))
        if mapping:
            if row.item_type == "earning":
                writer.writerow([
                    mapping.account_code, mapping.account_name,
                    "", "", row.total_amount, row.item_name,
                ])
            else:
                writer.writerow([
                    "", "",
                    mapping.account_code, mapping.account_name,
                    row.total_amount, row.item_name,
                ])
        else:
            debit_code = "給与手当" if row.item_type == "earning" else ""
            credit_code = "" if row.item_type == "earning" else "預り金"
            writer.writerow([
                debit_code, debit_code, credit_code, credit_code,
                row.total_amount, row.item_name,
            ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=journal_{payroll_period_id}.csv"},
    )


# ---------------------------------------------------------------------------
# GET /monthly-summary – 月次集計
# ---------------------------------------------------------------------------

@router.get("/monthly-summary", response_model=MonthlySummaryResponse)
async def monthly_summary(
    year_month: int,
    user: User = Depends(require_roles("super_admin", "admin", "accountant")),
    db: AsyncSession = Depends(get_db),
):
    """月次給与集計を取得する"""
    query = (
        select(PayrollRecord)
        .join(PayrollPeriod, PayrollRecord.payroll_period_id == PayrollPeriod.id)
        .where(
            PayrollRecord.company_id == user.company_id,
            PayrollPeriod.year_month == year_month,
        )
    )
    result = await db.execute(query)
    records = result.scalars().all()

    total_employees = len(set(r.employee_id for r in records))
    total_earnings = sum(r.total_earnings for r in records)
    total_deductions = sum(r.total_deductions for r in records)
    total_net = sum(r.net_pay for r in records)

    by_status = {}
    for r in records:
        by_status[r.status] = by_status.get(r.status, 0) + 1

    return MonthlySummaryResponse(
        year_month=year_month,
        total_employees=total_employees,
        total_earnings=total_earnings,
        total_deductions=total_deductions,
        total_net_pay=total_net,
        by_status=by_status,
    )
