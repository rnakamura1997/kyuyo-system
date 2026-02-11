"""給与計算メインサービス"""
import math
from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee, EmployeeAllowance, AllowanceType, CommuteDetail
from app.models.attendance import AttendanceRecord, PayrollPeriod
from app.models.company import Company
from app.services.tax_calculator import TaxCalculator
from app.services.insurance_calculator import InsuranceCalculator
from app.services.overtime_calculator import OvertimeCalculator


class PayrollCalculator:
    DEFAULT_MONTHLY_HOURS = 160  # デフォルト月所定労働時間

    def __init__(self, db: AsyncSession, company_id: int):
        self.db = db
        self.company_id = company_id
        self.tax_calc = TaxCalculator(db)
        self.ins_calc = InsuranceCalculator(db, company_id)
        self.ot_calc = OvertimeCalculator()

    async def _get_company(self) -> Company:
        result = await self.db.execute(
            select(Company).where(Company.company_id == self.company_id)
        )
        return result.scalar_one()

    async def calculate(self, employee: Employee, period: PayrollPeriod) -> dict:
        """従業員1名分の給与を計算する"""
        company = await self._get_company()
        items: list[dict] = []
        total_earnings = 0
        total_deductions = 0

        # 勤怠データ取得
        att_result = await self.db.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.company_id == self.company_id,
                AttendanceRecord.employee_id == employee.id,
                AttendanceRecord.year_month == period.year_month,
            )
        )
        attendance = att_result.scalar_one_or_none()

        work_days = attendance.work_days or 0 if attendance else 0
        total_work_minutes = attendance.total_work_minutes or 0 if attendance else 0

        attendance_dict = {}
        if attendance:
            for field in [
                "overtime_within_statutory_minutes", "overtime_statutory_minutes",
                "night_minutes", "statutory_holiday_minutes", "non_statutory_holiday_minutes",
                "night_overtime_minutes", "night_holiday_minutes", "night_overtime_holiday_minutes",
            ]:
                attendance_dict[field] = getattr(attendance, field, 0)

        # ── 1. 基本給計算 ──
        salary_settings = employee.salary_settings or {}
        salary_type = employee.salary_type
        base_salary = 0

        if salary_type == "monthly":
            base_salary = salary_settings.get("monthly_salary", 0)
            # 欠勤控除
            if attendance and attendance.absence_days and attendance.absence_days > 0:
                statutory_days = attendance.statutory_work_days or 20
                daily_rate = math.floor(base_salary / statutory_days)
                absence_deduction = daily_rate * attendance.absence_days
                base_salary -= absence_deduction
        elif salary_type == "daily":
            daily_rate = salary_settings.get("daily_rate", 0)
            base_salary = daily_rate * work_days
        elif salary_type == "hourly":
            hourly_rate = salary_settings.get("hourly_rate", 0)
            base_salary = math.floor(hourly_rate * (total_work_minutes / 60))
        elif salary_type == "commission":
            base_salary = salary_settings.get("base_amount", 0) + salary_settings.get("commission_amount", 0)

        items.append({
            "item_type": "earning", "item_code": "base_salary",
            "item_name": "基本給", "amount": base_salary,
            "is_taxable": True, "is_social_insurance_target": True,
            "is_employment_insurance_target": True,
        })
        total_earnings += base_salary

        # ── 2. 時間外手当計算 ──
        monthly_hours = salary_settings.get("monthly_prescribed_hours", self.DEFAULT_MONTHLY_HOURS)

        if salary_type == "monthly":
            # 割増基礎時給 = (月給 + 割増基礎手当) / 月所定労働時間
            overtime_base_allowances = 0
            # 後で手当計算後に加算
            base_hourly = math.floor(salary_settings.get("monthly_salary", 0) / monthly_hours)
        elif salary_type == "daily":
            base_hourly = math.floor(salary_settings.get("daily_rate", 0) / 8)
        elif salary_type == "hourly":
            base_hourly = salary_settings.get("hourly_rate", 0)
        else:
            base_hourly = math.floor(base_salary / (monthly_hours if monthly_hours > 0 else 160))

        if attendance_dict:
            ot_result = self.ot_calc.calculate(base_hourly, attendance_dict)

            overtime_items = [
                ("overtime_statutory", "時間外手当", ot_result.overtime_statutory_pay),
                ("overtime_within", "法定内残業手当", ot_result.overtime_within_statutory_pay),
                ("night_work", "深夜手当", ot_result.night_pay),
                ("holiday_work", "休日手当", ot_result.statutory_holiday_pay),
                ("non_statutory_holiday", "所定休日手当", ot_result.non_statutory_holiday_pay),
                ("over60h_premium", "60時間超割増", ot_result.over60h_premium_pay),
                ("night_overtime", "深夜残業手当", ot_result.night_overtime_pay),
                ("night_holiday", "深夜休日手当", ot_result.night_holiday_pay),
            ]

            for code, name, amount in overtime_items:
                if amount > 0:
                    items.append({
                        "item_type": "earning", "item_code": code,
                        "item_name": name, "amount": amount,
                        "is_taxable": True, "is_social_insurance_target": False,
                        "is_employment_insurance_target": True,
                    })
                    total_earnings += amount

        # ── 3. 手当計算 ──
        allowance_result = await self.db.execute(
            select(EmployeeAllowance, AllowanceType)
            .join(AllowanceType, EmployeeAllowance.allowance_type_id == AllowanceType.id)
            .where(
                EmployeeAllowance.company_id == self.company_id,
                EmployeeAllowance.employee_id == employee.id,
                EmployeeAllowance.effective_from <= period.end_date,
                AllowanceType.is_active == True,
            ).where(
                (EmployeeAllowance.effective_to.is_(None)) |
                (EmployeeAllowance.effective_to >= period.start_date)
            )
        )

        for ea, at in allowance_result.all():
            items.append({
                "item_type": "earning", "item_code": f"allowance_{at.code}",
                "item_name": at.name, "amount": ea.amount,
                "is_taxable": at.is_taxable,
                "is_social_insurance_target": at.is_social_insurance_target,
                "is_employment_insurance_target": at.is_employment_insurance_target,
            })
            total_earnings += ea.amount

        # ── 4. 通勤手当 ──
        commute_result = await self.db.execute(
            select(CommuteDetail).where(
                CommuteDetail.company_id == self.company_id,
                CommuteDetail.employee_id == employee.id,
                CommuteDetail.effective_from <= period.end_date,
            ).where(
                (CommuteDetail.effective_to.is_(None)) |
                (CommuteDetail.effective_to >= period.start_date)
            ).limit(1)
        )
        commute = commute_result.scalar_one_or_none()

        commute_amount = 0
        commute_nontaxable = 0
        if commute and commute.monthly_cost:
            commute_amount = commute.monthly_cost
            commute_nontaxable = min(commute.monthly_cost, commute.non_taxable_limit or 150000)
            items.append({
                "item_type": "earning", "item_code": "commute",
                "item_name": "通勤手当", "amount": commute_amount,
                "is_taxable": False, "is_social_insurance_target": True,
                "is_employment_insurance_target": True,
                "notes": f"非課税限度額: {commute_nontaxable}円",
            })
            total_earnings += commute_amount

        # ── 5. 控除計算 ──
        gross_salary = total_earnings
        target_date = period.payment_date

        # 従業員の年齢計算
        employee_age = None
        if employee.birth_date:
            age_delta = target_date - employee.birth_date
            employee_age = age_delta.days // 365

        # 社会保険料
        social_insurance_total = 0

        if employee.social_insurance_enrolled:
            health_result = await self.ins_calc.calculate_health_insurance(
                gross_salary, target_date, employee_age
            )
            health_ins = health_result["health_insurance"]
            care_ins = health_result["care_insurance"]

            if health_ins > 0:
                items.append({
                    "item_type": "deduction", "item_code": "health_insurance",
                    "item_name": "健康保険料", "amount": health_ins,
                    "is_taxable": False, "is_social_insurance_target": False,
                    "is_employment_insurance_target": False,
                })
                total_deductions += health_ins
                social_insurance_total += health_ins

            if care_ins > 0:
                items.append({
                    "item_type": "deduction", "item_code": "care_insurance",
                    "item_name": "介護保険料", "amount": care_ins,
                    "is_taxable": False, "is_social_insurance_target": False,
                    "is_employment_insurance_target": False,
                })
                total_deductions += care_ins
                social_insurance_total += care_ins

        if employee.pension_insurance_enrolled:
            pension = await self.ins_calc.calculate_pension_insurance(gross_salary, target_date)
            if pension > 0:
                items.append({
                    "item_type": "deduction", "item_code": "pension_insurance",
                    "item_name": "厚生年金保険料", "amount": pension,
                    "is_taxable": False, "is_social_insurance_target": False,
                    "is_employment_insurance_target": False,
                })
                total_deductions += pension
                social_insurance_total += pension

        if employee.employment_insurance_enrolled:
            emp_ins = await self.ins_calc.calculate_employment_insurance(gross_salary, target_date)
            if emp_ins > 0:
                items.append({
                    "item_type": "deduction", "item_code": "employment_insurance",
                    "item_name": "雇用保険料", "amount": emp_ins,
                    "is_taxable": False, "is_social_insurance_target": False,
                    "is_employment_insurance_target": False,
                })
                total_deductions += emp_ins
                social_insurance_total += emp_ins

        # 所得税計算
        # 課税対象額 = 総支給額 - 非課税通勤手当 - 社会保険料
        taxable_earnings = total_earnings - commute_nontaxable - social_insurance_total
        taxable_earnings = max(0, taxable_earnings)

        income_tax = await self.tax_calc.calculate_income_tax(
            taxable_earnings,
            employee.tax_category,
            employee.dependents_count,
            target_date,
            is_monthly=(salary_type == "monthly"),
        )
        if income_tax > 0:
            items.append({
                "item_type": "deduction", "item_code": "income_tax",
                "item_name": "所得税", "amount": income_tax,
                "is_taxable": False, "is_social_insurance_target": False,
                "is_employment_insurance_target": False,
            })
            total_deductions += income_tax

        # 住民税
        if employee.resident_tax_monthly_amount and employee.resident_tax_monthly_amount > 0:
            items.append({
                "item_type": "deduction", "item_code": "resident_tax",
                "item_name": "住民税", "amount": employee.resident_tax_monthly_amount,
                "is_taxable": False, "is_social_insurance_target": False,
                "is_employment_insurance_target": False,
            })
            total_deductions += employee.resident_tax_monthly_amount

        # ── 6. 結果 ──
        net_pay = total_earnings - total_deductions

        return {
            "total_earnings": total_earnings,
            "total_deductions": total_deductions,
            "net_pay": net_pay,
            "items": items,
            "details": {
                "salary_type": salary_type,
                "base_salary": base_salary,
                "base_hourly_rate": base_hourly,
                "gross_salary": gross_salary,
                "social_insurance_total": social_insurance_total,
                "taxable_earnings": taxable_earnings,
                "income_tax": income_tax,
                "work_days": work_days,
                "total_work_minutes": total_work_minutes,
            },
        }
