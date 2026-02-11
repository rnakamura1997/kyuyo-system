"""所得税計算サービス"""
import math
from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.globals import IncomeTaxTable


class TaxCalculator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_income_tax(
        self,
        taxable_income: int,
        tax_category: str,
        dependents_count: int,
        target_date: date,
        is_monthly: bool = True,
    ) -> int:
        """所得税を計算する

        Args:
            taxable_income: 課税対象額（社会保険料控除後）
            tax_category: 税区分 (kou/otsu/hei)
            dependents_count: 扶養親族数
            target_date: 対象日付
            is_monthly: 月額計算かどうか

        Returns:
            所得税額（円）
        """
        # テーブルタイプの決定
        if tax_category == "kou":
            table_type = "monthly_kou" if is_monthly else "daily_kou"
        elif tax_category == "otsu":
            table_type = "otsu"
        else:
            table_type = "hei"

        # 税額表から検索
        query = select(IncomeTaxTable).where(
            IncomeTaxTable.table_type == table_type,
            IncomeTaxTable.valid_from <= target_date,
            IncomeTaxTable.income_from <= taxable_income,
            IncomeTaxTable.dependents_count == dependents_count,
        ).where(
            (IncomeTaxTable.valid_to.is_(None)) | (IncomeTaxTable.valid_to >= target_date)
        ).where(
            (IncomeTaxTable.income_to.is_(None)) | (IncomeTaxTable.income_to > taxable_income)
        ).order_by(IncomeTaxTable.income_from.desc()).limit(1)

        result = await self.db.execute(query)
        tax_row = result.scalar_one_or_none()

        if tax_row:
            return tax_row.tax_amount

        # 税額表にない場合（高額所得者等）の概算計算
        if tax_category == "otsu":
            return math.floor(taxable_income * 0.0358)  # 乙欄概算3.58%
        elif tax_category == "hei":
            return math.floor(taxable_income * 0.0358)  # 丙欄概算

        # 甲欄で税額表にない場合
        return 0
