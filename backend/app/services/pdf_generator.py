"""給与明細PDF生成サービス"""

import logging
import os
from datetime import date
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# Japanese font registration
# ---------------------------------------------------------------------------
_font_registered = False
for font_path in [
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJKjp-Regular.otf",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
]:
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont("JapaneseFont", font_path))
            _font_registered = True
            logger.info("Registered Japanese font from %s", font_path)
            break
        except Exception:
            continue

if not _font_registered:
    logger.warning(
        "Japanese font not found. PDF output will fall back to Helvetica and "
        "Japanese characters may not render correctly."
    )

FONT_NAME = "JapaneseFont" if _font_registered else "Helvetica"

# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 15 * mm


def _get_styles() -> dict[str, ParagraphStyle]:
    """Return a dictionary of ParagraphStyle objects used across PDF pages."""
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "PDFTitle",
            parent=base["Title"],
            fontName=FONT_NAME,
            fontSize=18,
            leading=22,
            alignment=1,  # center
            spaceAfter=4 * mm,
        ),
        "subtitle": ParagraphStyle(
            "PDFSubtitle",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=11,
            leading=14,
            alignment=1,
            spaceAfter=2 * mm,
        ),
        "heading": ParagraphStyle(
            "PDFHeading",
            parent=base["Heading2"],
            fontName=FONT_NAME,
            fontSize=12,
            leading=15,
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
        ),
        "normal": ParagraphStyle(
            "PDFNormal",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=9,
            leading=12,
        ),
        "small": ParagraphStyle(
            "PDFSmall",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=8,
            leading=10,
        ),
        "right": ParagraphStyle(
            "PDFRight",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=9,
            leading=12,
            alignment=2,  # right
        ),
        "net_pay": ParagraphStyle(
            "PDFNetPay",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=14,
            leading=18,
            alignment=2,
        ),
    }


# ---------------------------------------------------------------------------
# Formatting utilities
# ---------------------------------------------------------------------------

def _format_currency(amount: int) -> str:
    """Format an integer yen amount as '¥1,234,567'."""
    if amount < 0:
        return f"-¥{abs(amount):,}"
    return f"¥{amount:,}"


def _format_year_month(year_month: int) -> str:
    """Convert YYYYMM integer to 'YYYY年MM月' string."""
    year = year_month // 100
    month = year_month % 100
    return f"{year}年{month:02d}月"


def _format_hours_from_minutes(minutes: int | float | None) -> str:
    """Convert minutes to 'HH:MM' display string."""
    if minutes is None or minutes == 0:
        return "0:00"
    total = int(minutes)
    h = total // 60
    m = total % 60
    return f"{h}:{m:02d}"


def _format_date_jp(d: date) -> str:
    """Format a date as 'YYYY年MM月DD日'."""
    return f"{d.year}年{d.month:02d}月{d.day:02d}日"


# ---------------------------------------------------------------------------
# Common table style builders
# ---------------------------------------------------------------------------

def _base_table_style() -> list:
    """Return a base list of TableStyle commands shared by earnings/deductions."""
    return [
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
        ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]


def _total_row_style(row_index: int) -> list:
    """Return additional style commands for the total row."""
    return [
        ("BACKGROUND", (0, row_index), (-1, row_index), colors.HexColor("#D9E2F3")),
        ("FONTSIZE", (0, row_index), (-1, row_index), 10),
    ]


# ---------------------------------------------------------------------------
# Payroll slip PDF generation
# ---------------------------------------------------------------------------

async def generate_payroll_pdf(
    record_data: dict,
    company_name: str,
    employee_name: str,
    employee_code: str,
    department: str | None,
    year_month: int,
    payment_date: date,
) -> str:
    """Generate a payroll slip (給与明細書) PDF and save it to disk.

    Parameters
    ----------
    record_data : dict
        Must contain:
        - items: list[dict] with keys ``item_type``, ``item_name``, ``amount``
        - total_earnings: int
        - total_deductions: int
        - net_pay: int
        - calculation_details: dict (optional, may contain attendance info)
        - company_id: int
        - employee_id: int
    company_name : str
    employee_name : str
    employee_code : str
    department : str | None
    year_month : int  (YYYYMM)
    payment_date : date

    Returns
    -------
    str – absolute file path where the PDF was saved.
    """
    company_id = record_data["company_id"]
    employee_id = record_data["employee_id"]
    items = record_data.get("items", [])
    total_earnings = record_data.get("total_earnings", 0)
    total_deductions = record_data.get("total_deductions", 0)
    net_pay = record_data.get("net_pay", 0)
    calc_details = record_data.get("calculation_details") or {}

    # --- Prepare output directory and path -----------------------------------
    dir_path = Path(settings.FILE_STORAGE_PATH) / "payroll" / str(company_id) / str(year_month)
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / f"{employee_id}.pdf"

    # --- Build document elements ---------------------------------------------
    styles = _get_styles()
    elements: list = []

    # 1. Header – company name, title, payment date / period
    elements.append(Paragraph(company_name, styles["subtitle"]))
    elements.append(Paragraph("給与明細書", styles["title"]))

    period_text = f"対象期間: {_format_year_month(year_month)}　　支給日: {_format_date_jp(payment_date)}"
    elements.append(Paragraph(period_text, styles["subtitle"]))
    elements.append(Spacer(1, 3 * mm))

    # 2. Employee information table
    dept_display = department if department else "―"
    emp_info_data = [
        ["社員番号", employee_code, "氏名", employee_name],
        ["部署", dept_display, "", ""],
    ]
    emp_info_table = Table(
        emp_info_data,
        colWidths=[25 * mm, 55 * mm, 20 * mm, 70 * mm],
    )
    emp_info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E2EFDA")),
        ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#E2EFDA")),
        ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
        ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("SPAN", (1, 1), (3, 1)),
    ]))
    elements.append(emp_info_table)
    elements.append(Spacer(1, 5 * mm))

    # --- Separate items into earnings and deductions -------------------------
    earnings = [i for i in items if i.get("item_type") == "earning"]
    deductions = [i for i in items if i.get("item_type") == "deduction"]

    # Sort by display_order if available, otherwise keep original order
    earnings.sort(key=lambda x: (x.get("display_order") or 9999, x.get("item_name", "")))
    deductions.sort(key=lambda x: (x.get("display_order") or 9999, x.get("item_name", "")))

    # 3. Earnings table (支給)
    elements.append(Paragraph("支給", styles["heading"]))
    earn_data = [["項目名", "金額"]]
    for item in earnings:
        earn_data.append([
            item.get("item_name", ""),
            _format_currency(item.get("amount", 0)),
        ])
    earn_data.append(["支給額合計", _format_currency(total_earnings)])

    earn_table = Table(earn_data, colWidths=[100 * mm, 70 * mm])
    style_cmds = _base_table_style() + _total_row_style(len(earn_data) - 1)
    earn_table.setStyle(TableStyle(style_cmds))
    elements.append(earn_table)
    elements.append(Spacer(1, 5 * mm))

    # 4. Deductions table (控除)
    elements.append(Paragraph("控除", styles["heading"]))
    ded_data = [["項目名", "金額"]]
    for item in deductions:
        ded_data.append([
            item.get("item_name", ""),
            _format_currency(item.get("amount", 0)),
        ])
    ded_data.append(["控除額合計", _format_currency(total_deductions)])

    ded_table = Table(ded_data, colWidths=[100 * mm, 70 * mm])
    style_cmds = _base_table_style() + _total_row_style(len(ded_data) - 1)
    ded_table.setStyle(TableStyle(style_cmds))
    elements.append(ded_table)
    elements.append(Spacer(1, 6 * mm))

    # 5. Net pay summary (差引支給額)
    net_data = [["差引支給額", _format_currency(net_pay)]]
    net_table = Table(net_data, colWidths=[100 * mm, 70 * mm])
    net_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 13),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#FFC000")),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#FFF2CC")),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
        ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
    ]))
    elements.append(net_table)
    elements.append(Spacer(1, 6 * mm))

    # 6. Attendance summary (勤怠)
    attendance = calc_details.get("attendance") or {}
    if attendance:
        elements.append(Paragraph("勤怠", styles["heading"]))
        att_rows = _build_attendance_rows(attendance)
        att_table = Table(att_rows, colWidths=[42 * mm, 28 * mm, 42 * mm, 28 * mm])
        att_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E2EFDA")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#E2EFDA")),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("ALIGN", (3, 0), (3, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 1.5 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
            ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        ]))
        elements.append(att_table)

    # --- Render PDF ----------------------------------------------------------
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title="給与明細書",
        author=company_name,
    )
    doc.build(elements)

    file_path.write_bytes(buf.getvalue())
    logger.info("Payroll PDF saved to %s", file_path)
    return str(file_path)


def _build_attendance_rows(attendance: dict) -> list[list[str]]:
    """Build the two-column key/value rows for the attendance summary table.

    Returned as a flat list of 4-column rows so that two key-value pairs sit
    side by side on each line.
    """
    pairs: list[tuple[str, str]] = []

    mapping = [
        ("work_days", "出勤日数", "日"),
        ("statutory_work_days", "所定労働日数", "日"),
        ("absence_days", "欠勤日数", "日"),
        ("paid_leave_days", "有給取得日数", "日"),
        ("late_count", "遅刻回数", "回"),
        ("early_leave_count", "早退回数", "回"),
        ("substitute_holiday_days", "代休日数", "日"),
    ]

    for key, label, unit in mapping:
        val = attendance.get(key)
        if val is not None:
            pairs.append((label, f"{val}{unit}"))

    # Time-based fields (stored in minutes)
    time_mapping = [
        ("total_work_minutes", "総労働時間"),
        ("regular_minutes", "所定内時間"),
        ("overtime_statutory_minutes", "法定時間外"),
        ("overtime_within_statutory_minutes", "法定内残業"),
        ("night_minutes", "深夜時間"),
        ("statutory_holiday_minutes", "法定休日時間"),
        ("non_statutory_holiday_minutes", "法定外休日時間"),
    ]

    for key, label in time_mapping:
        val = attendance.get(key)
        if val is not None and val != 0:
            pairs.append((label, _format_hours_from_minutes(val)))

    # Pad to even count so two-column layout works
    if len(pairs) % 2 != 0:
        pairs.append(("", ""))

    rows: list[list[str]] = []
    for i in range(0, len(pairs), 2):
        left = pairs[i]
        right = pairs[i + 1] if i + 1 < len(pairs) else ("", "")
        rows.append([left[0], left[1], right[0], right[1]])

    # Ensure at least one row exists
    if not rows:
        rows.append(["", "", "", ""])

    return rows


# ---------------------------------------------------------------------------
# Withholding slip (源泉徴収票) PDF generation
# ---------------------------------------------------------------------------

async def generate_withholding_slip_pdf(
    slip_data: dict,
    company_name: str,
    employee_name: str,
    target_year: int,
) -> str:
    """Generate a tax withholding slip (源泉徴収票) PDF and save it to disk.

    Parameters
    ----------
    slip_data : dict
        Must contain:
        - company_id: int
        - employee_id: int
        - employee_code: str
        - address: str | None
        - annual_income: int
        - income_deduction: int
        - taxable_income: int
        - annual_tax: int
        - social_insurance_total: int
        - life_insurance_deduction: int
        - earthquake_insurance_deduction: int
        - housing_loan_deduction: int
        - spouse_deduction: int
        - dependent_deduction: int
        - basic_deduction: int
        - other_deductions: dict | None
        - dependents: list[dict] | None
    company_name : str
    employee_name : str
    target_year : int (e.g. 2026)

    Returns
    -------
    str – absolute file path where the PDF was saved.
    """
    company_id = slip_data["company_id"]
    employee_id = slip_data["employee_id"]

    # --- Output path ---------------------------------------------------------
    dir_path = (
        Path(settings.FILE_STORAGE_PATH) / "withholding" / str(company_id) / str(target_year)
    )
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / f"{employee_id}.pdf"

    # --- Build elements ------------------------------------------------------
    styles = _get_styles()
    elements: list = []

    # Header
    elements.append(Paragraph(
        f"令和{target_year - 2018}年分　給与所得の源泉徴収票",
        styles["title"],
    ))
    elements.append(Spacer(1, 4 * mm))

    # Company / employee info
    address = slip_data.get("address") or "―"
    employee_code = slip_data.get("employee_code", "")
    info_data = [
        ["支払者", company_name, "受給者", employee_name],
        ["社員番号", employee_code, "住所", address],
    ]
    info_table = Table(info_data, colWidths=[25 * mm, 60 * mm, 25 * mm, 60 * mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E2EFDA")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#E2EFDA")),
        ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
        ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 6 * mm))

    # Main amounts table
    annual_income = slip_data.get("annual_income", 0)
    income_deduction = slip_data.get("income_deduction", 0)
    taxable_income = slip_data.get("taxable_income", 0)
    annual_tax = slip_data.get("annual_tax", 0)

    main_data = [
        ["項目", "金額"],
        ["支払金額", _format_currency(annual_income)],
        ["給与所得控除後の金額", _format_currency(income_deduction)],
        ["所得控除の額の合計額", _format_currency(taxable_income)],
        ["源泉徴収税額", _format_currency(annual_tax)],
    ]
    main_table = Table(main_data, colWidths=[85 * mm, 85 * mm])
    main_style = _base_table_style()
    main_table.setStyle(TableStyle(main_style))
    elements.append(main_table)
    elements.append(Spacer(1, 6 * mm))

    # Social insurance & deductions table
    elements.append(Paragraph("社会保険料等・各種控除", styles["heading"]))

    social_total = slip_data.get("social_insurance_total", 0)
    life_ins = slip_data.get("life_insurance_deduction", 0)
    earthquake_ins = slip_data.get("earthquake_insurance_deduction", 0)
    housing_loan = slip_data.get("housing_loan_deduction", 0)
    spouse_ded = slip_data.get("spouse_deduction", 0)
    dependent_ded = slip_data.get("dependent_deduction", 0)
    basic_ded = slip_data.get("basic_deduction", 0)

    ded_rows = [
        ["項目", "金額"],
        ["社会保険料等の金額", _format_currency(social_total)],
        ["生命保険料の控除額", _format_currency(life_ins)],
        ["地震保険料の控除額", _format_currency(earthquake_ins)],
        ["住宅借入金等特別控除の額", _format_currency(housing_loan)],
        ["配偶者控除額", _format_currency(spouse_ded)],
        ["扶養控除額", _format_currency(dependent_ded)],
        ["基礎控除額", _format_currency(basic_ded)],
    ]

    # Append optional other deductions
    other_ded = slip_data.get("other_deductions") or {}
    for label, amount in other_ded.items():
        ded_rows.append([str(label), _format_currency(int(amount))])

    ded_table = Table(ded_rows, colWidths=[85 * mm, 85 * mm])
    ded_style = _base_table_style()
    ded_table.setStyle(TableStyle(ded_style))
    elements.append(ded_table)
    elements.append(Spacer(1, 6 * mm))

    # Dependents section
    dependents = slip_data.get("dependents") or []
    if dependents:
        elements.append(Paragraph("扶養親族", styles["heading"]))
        dep_header = ["続柄", "氏名", "生年月日", "区分"]
        dep_data = [dep_header]
        for dep in dependents:
            dep_data.append([
                dep.get("relationship", ""),
                dep.get("name", ""),
                dep.get("birth_date", ""),
                dep.get("category", ""),
            ])
        dep_table = Table(dep_data, colWidths=[30 * mm, 55 * mm, 40 * mm, 45 * mm])
        dep_style = _base_table_style()
        dep_table.setStyle(TableStyle(dep_style))
        elements.append(dep_table)
        elements.append(Spacer(1, 4 * mm))

    # Footer note
    elements.append(Spacer(1, 6 * mm))
    footer_text = (
        f"上記の通り、令和{target_year - 2018}年分の給与所得の源泉徴収票を交付します。"
    )
    elements.append(Paragraph(footer_text, styles["normal"]))

    # --- Render PDF ----------------------------------------------------------
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title="源泉徴収票",
        author=company_name,
    )
    doc.build(elements)

    file_path.write_bytes(buf.getvalue())
    logger.info("Withholding slip PDF saved to %s", file_path)
    return str(file_path)
