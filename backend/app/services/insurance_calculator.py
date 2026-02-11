"""社会保険料計算サービス"""
import math
from datetime import date
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.insurance import InsuranceRate
from app.models.company import Company


class InsuranceCalculator:
    def __init__(self, db: AsyncSession, company_id: int):
        self.db = db
        self.company_id = company_id
        self._company: Company | None = None

    async def _get_company(self) -> Company:
        if self._company is None:
            result = await self.db.execute(
                select(Company).where(Company.company_id == self.company_id)
            )
            self._company = result.scalar_one()
        return self._company

    async def _get_rate(
        self, insurance_type: str, target_date: date, prefecture: str | None = None
    ) -> InsuranceRate | None:
        """保険料率を取得（会社固有 → グローバルの順で検索）"""
        # 会社固有の料率を検索
        query = select(InsuranceRate).where(
            InsuranceRate.insurance_type == insurance_type,
            InsuranceRate.valid_from <= target_date,
            (InsuranceRate.valid_to.is_(None)) | (InsuranceRate.valid_to >= target_date),
        )

        if insurance_type == "health" and prefecture:
            query = query.where(InsuranceRate.prefecture == prefecture)

        # 会社固有を優先
        company_query = query.where(InsuranceRate.company_id == self.company_id)
        result = await self.db.execute(company_query.order_by(InsuranceRate.valid_from.desc()).limit(1))
        rate = result.scalar_one_or_none()
        if rate:
            return rate

        # グローバル料率
        global_query = query.where(InsuranceRate.company_id.is_(None))
        result = await self.db.execute(global_query.order_by(InsuranceRate.valid_from.desc()).limit(1))
        return result.scalar_one_or_none()

    async def calculate_health_insurance(
        self, gross_salary: int, target_date: date, employee_age: int | None = None
    ) -> dict:
        """健康保険料を計算

        Returns: {"health_insurance": int, "care_insurance": int}
        """
        company = await self._get_company()
        prefecture = company.health_insurance_prefecture or "東京都"

        rate = await self._get_rate("health", target_date, prefecture)
        if not rate:
            return {"health_insurance": 0, "care_insurance": 0}

        health = math.floor(gross_salary * float(rate.employee_rate))

        # 介護保険（40歳以上65歳未満）
        care = 0
        if (employee_age and 40 <= employee_age < 65 and
            company.care_insurance_applicable and rate.care_insurance_rate):
            care = math.floor(gross_salary * float(rate.care_insurance_rate))

        return {"health_insurance": health, "care_insurance": care}

    async def calculate_pension_insurance(
        self, gross_salary: int, target_date: date
    ) -> int:
        """厚生年金保険料を計算"""
        rate = await self._get_rate("pension", target_date)
        if not rate:
            return 0
        return math.floor(gross_salary * float(rate.employee_rate))

    async def calculate_employment_insurance(
        self, gross_salary: int, target_date: date
    ) -> int:
        """雇用保険料を計算"""
        company = await self._get_company()
        rate = await self._get_rate("employment", target_date)
        if not rate:
            return 0
        return math.floor(gross_salary * float(rate.employee_rate))
