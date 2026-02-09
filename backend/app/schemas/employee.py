"""従業員関連スキーマ"""

from datetime import date
from pydantic import BaseModel


class EmployeeCreate(BaseModel):
    employee_code: str
    first_name: str
    last_name: str
    first_name_kana: str | None = None
    last_name_kana: str | None = None
    email: str | None = None
    birth_date: date | None = None
    gender: str | None = None
    address: str | None = None
    phone: str | None = None
    hire_date: date
    employment_type: str
    department: str | None = None
    position: str | None = None
    salary_type: str
    salary_settings: dict
    tax_category: str
    dependents_count: int = 0
    social_insurance_enrolled: bool = False
    pension_insurance_enrolled: bool = False
    employment_insurance_enrolled: bool = False
    resident_tax_type: str | None = None
    resident_tax_monthly_amount: int | None = None
    bank_name: str | None = None
    branch_name: str | None = None
    account_type: str | None = None
    account_number: str | None = None
    account_holder: str | None = None


class EmployeeUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    first_name_kana: str | None = None
    last_name_kana: str | None = None
    email: str | None = None
    birth_date: date | None = None
    gender: str | None = None
    address: str | None = None
    phone: str | None = None
    termination_date: date | None = None
    employment_type: str | None = None
    department: str | None = None
    position: str | None = None
    salary_type: str | None = None
    salary_settings: dict | None = None
    tax_category: str | None = None
    dependents_count: int | None = None
    social_insurance_enrolled: bool | None = None
    pension_insurance_enrolled: bool | None = None
    employment_insurance_enrolled: bool | None = None
    resident_tax_type: str | None = None
    resident_tax_monthly_amount: int | None = None
    bank_name: str | None = None
    branch_name: str | None = None
    account_type: str | None = None
    account_number: str | None = None
    account_holder: str | None = None


class EmployeeResponse(BaseModel):
    id: int
    company_id: int
    employee_code: str
    first_name: str
    last_name: str
    first_name_kana: str | None = None
    last_name_kana: str | None = None
    email: str | None = None
    birth_date: date | None = None
    hire_date: date
    termination_date: date | None = None
    employment_type: str
    department: str | None = None
    position: str | None = None
    salary_type: str
    tax_category: str
    dependents_count: int

    model_config = {"from_attributes": True}
