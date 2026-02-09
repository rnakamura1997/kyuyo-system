"""会社関連スキーマ"""

from pydantic import BaseModel


class CompanyCreate(BaseModel):
    name: str
    name_kana: str | None = None
    address: str | None = None
    phone: str | None = None
    representative_name: str | None = None
    legal_number: str | None = None
    closing_day: int
    payment_day: int
    payment_month_offset: int = 1
    health_insurance_type: str | None = None
    health_insurance_prefecture: str | None = None
    health_insurance_union_name: str | None = None
    business_office_symbol: str | None = None
    care_insurance_applicable: bool = True
    pension_office_number: str | None = None
    employment_office_number: str | None = None
    employment_business_type: str | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
    name_kana: str | None = None
    address: str | None = None
    phone: str | None = None
    representative_name: str | None = None
    legal_number: str | None = None
    closing_day: int | None = None
    payment_day: int | None = None
    payment_month_offset: int | None = None
    health_insurance_type: str | None = None
    health_insurance_prefecture: str | None = None
    health_insurance_union_name: str | None = None
    business_office_symbol: str | None = None
    care_insurance_applicable: bool | None = None
    pension_office_number: str | None = None
    employment_office_number: str | None = None
    employment_business_type: str | None = None


class CompanyResponse(BaseModel):
    id: int
    company_id: int
    name: str
    name_kana: str | None = None
    address: str | None = None
    phone: str | None = None
    representative_name: str | None = None
    legal_number: str | None = None
    closing_day: int
    payment_day: int
    payment_month_offset: int
    health_insurance_type: str | None = None
    health_insurance_prefecture: str | None = None

    model_config = {"from_attributes": True}
