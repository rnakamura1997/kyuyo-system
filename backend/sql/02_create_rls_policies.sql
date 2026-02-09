-- RLSポリシー定義
-- company_idを持つ全テーブルに適用

-- ========================================
-- companies
-- ========================================
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE companies FORCE ROW LEVEL SECURITY;

CREATE POLICY companies_tenant_isolation ON companies
    FOR ALL TO app_user
    USING (company_id = app_current_company_id())
    WITH CHECK (company_id = app_current_company_id());

CREATE POLICY companies_super_admin ON companies
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- users
-- ========================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE users FORCE ROW LEVEL SECURITY;

CREATE POLICY users_tenant_isolation ON users
    FOR ALL TO app_user
    USING (company_id = app_current_company_id())
    WITH CHECK (company_id = app_current_company_id());

CREATE POLICY users_super_admin ON users
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- user_roles
-- ========================================
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_roles FORCE ROW LEVEL SECURITY;

CREATE POLICY user_roles_tenant_isolation ON user_roles
    FOR ALL TO app_user
    USING (company_id = app_current_company_id())
    WITH CHECK (company_id = app_current_company_id());

CREATE POLICY user_roles_super_admin ON user_roles
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- employees
-- ========================================
ALTER TABLE employees ENABLE ROW LEVEL SECURITY;
ALTER TABLE employees FORCE ROW LEVEL SECURITY;

CREATE POLICY employees_tenant_isolation ON employees
    FOR ALL TO app_user
    USING (company_id = app_current_company_id())
    WITH CHECK (company_id = app_current_company_id());

CREATE POLICY employees_super_admin ON employees
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- allowance_types
-- ========================================
ALTER TABLE allowance_types ENABLE ROW LEVEL SECURITY;
ALTER TABLE allowance_types FORCE ROW LEVEL SECURITY;

CREATE POLICY allowance_types_tenant_isolation ON allowance_types
    FOR ALL TO app_user
    USING (company_id = app_current_company_id())
    WITH CHECK (company_id = app_current_company_id());

CREATE POLICY allowance_types_super_admin ON allowance_types
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- employee_allowances
-- ========================================
ALTER TABLE employee_allowances ENABLE ROW LEVEL SECURITY;
ALTER TABLE employee_allowances FORCE ROW LEVEL SECURITY;

CREATE POLICY employee_allowances_tenant_isolation ON employee_allowances
    FOR ALL TO app_user
    USING (company_id = app_current_company_id())
    WITH CHECK (company_id = app_current_company_id());

CREATE POLICY employee_allowances_super_admin ON employee_allowances
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- commute_details
-- ========================================
ALTER TABLE commute_details ENABLE ROW LEVEL SECURITY;
ALTER TABLE commute_details FORCE ROW LEVEL SECURITY;

CREATE POLICY commute_details_tenant_isolation ON commute_details
    FOR ALL TO app_user
    USING (company_id = app_current_company_id())
    WITH CHECK (company_id = app_current_company_id());

CREATE POLICY commute_details_super_admin ON commute_details
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- attendance_records
-- ========================================
ALTER TABLE attendance_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance_records FORCE ROW LEVEL SECURITY;

CREATE POLICY attendance_records_tenant_isolation ON attendance_records
    FOR ALL TO app_user
    USING (company_id = app_current_company_id())
    WITH CHECK (company_id = app_current_company_id());

CREATE POLICY attendance_records_super_admin ON attendance_records
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- payroll_periods
-- ========================================
ALTER TABLE payroll_periods ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll_periods FORCE ROW LEVEL SECURITY;

CREATE POLICY payroll_periods_tenant_isolation ON payroll_periods
    FOR ALL TO app_user
    USING (company_id = app_current_company_id())
    WITH CHECK (company_id = app_current_company_id());

CREATE POLICY payroll_periods_super_admin ON payroll_periods
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- payroll_record_groups
-- ========================================
ALTER TABLE payroll_record_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll_record_groups FORCE ROW LEVEL SECURITY;

CREATE POLICY payroll_record_groups_tenant_isolation ON payroll_record_groups
    FOR ALL TO app_user
    USING (company_id = app_current_company_id())
    WITH CHECK (company_id = app_current_company_id());

CREATE POLICY payroll_record_groups_super_admin ON payroll_record_groups
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- payroll_records
-- ========================================
ALTER TABLE payroll_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll_records FORCE ROW LEVEL SECURITY;

CREATE POLICY payroll_records_tenant_isolation ON payroll_records
    FOR ALL TO app_user
    USING (company_id = app_current_company_id())
    WITH CHECK (company_id = app_current_company_id());

CREATE POLICY payroll_records_super_admin ON payroll_records
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- payroll_record_items
-- ========================================
ALTER TABLE payroll_record_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll_record_items FORCE ROW LEVEL SECURITY;

CREATE POLICY payroll_record_items_tenant_isolation ON payroll_record_items
    FOR ALL TO app_user
    USING (company_id = app_current_company_id())
    WITH CHECK (company_id = app_current_company_id());

CREATE POLICY payroll_record_items_super_admin ON payroll_record_items
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- payroll_snapshots
-- ========================================
ALTER TABLE payroll_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll_snapshots FORCE ROW LEVEL SECURITY;

CREATE POLICY payroll_snapshots_tenant_isolation ON payroll_snapshots
    FOR ALL TO app_user
    USING (company_id = app_current_company_id())
    WITH CHECK (company_id = app_current_company_id());

CREATE POLICY payroll_snapshots_super_admin ON payroll_snapshots
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- payroll_histories
-- ========================================
ALTER TABLE payroll_histories ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll_histories FORCE ROW LEVEL SECURITY;

CREATE POLICY payroll_histories_tenant_isolation ON payroll_histories
    FOR ALL TO app_user
    USING (company_id = app_current_company_id())
    WITH CHECK (company_id = app_current_company_id());

CREATE POLICY payroll_histories_super_admin ON payroll_histories
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- bonus_events
-- ========================================
ALTER TABLE bonus_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE bonus_events FORCE ROW LEVEL SECURITY;

CREATE POLICY bonus_events_tenant_isolation ON bonus_events
    FOR ALL TO app_user
    USING (company_id = app_current_company_id())
    WITH CHECK (company_id = app_current_company_id());

CREATE POLICY bonus_events_super_admin ON bonus_events
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- bonus_records
-- ========================================
ALTER TABLE bonus_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE bonus_records FORCE ROW LEVEL SECURITY;

CREATE POLICY bonus_records_tenant_isolation ON bonus_records
    FOR ALL TO app_user
    USING (company_id = app_current_company_id())
    WITH CHECK (company_id = app_current_company_id());

CREATE POLICY bonus_records_super_admin ON bonus_records
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- year_end_adjustments
-- ========================================
ALTER TABLE year_end_adjustments ENABLE ROW LEVEL SECURITY;
ALTER TABLE year_end_adjustments FORCE ROW LEVEL SECURITY;

CREATE POLICY year_end_adjustments_tenant_isolation ON year_end_adjustments
    FOR ALL TO app_user
    USING (company_id = app_current_company_id())
    WITH CHECK (company_id = app_current_company_id());

CREATE POLICY year_end_adjustments_super_admin ON year_end_adjustments
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- year_end_adjustment_histories
-- ========================================
ALTER TABLE year_end_adjustment_histories ENABLE ROW LEVEL SECURITY;
ALTER TABLE year_end_adjustment_histories FORCE ROW LEVEL SECURITY;

CREATE POLICY year_end_adjustment_histories_tenant_isolation ON year_end_adjustment_histories
    FOR ALL TO app_user
    USING (company_id = app_current_company_id())
    WITH CHECK (company_id = app_current_company_id());

CREATE POLICY year_end_adjustment_histories_super_admin ON year_end_adjustment_histories
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- deduction_certificates
-- ========================================
ALTER TABLE deduction_certificates ENABLE ROW LEVEL SECURITY;
ALTER TABLE deduction_certificates FORCE ROW LEVEL SECURITY;

CREATE POLICY deduction_certificates_tenant_isolation ON deduction_certificates
    FOR ALL TO app_user
    USING (company_id = app_current_company_id())
    WITH CHECK (company_id = app_current_company_id());

CREATE POLICY deduction_certificates_super_admin ON deduction_certificates
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- tax_withholding_slips
-- ========================================
ALTER TABLE tax_withholding_slips ENABLE ROW LEVEL SECURITY;
ALTER TABLE tax_withholding_slips FORCE ROW LEVEL SECURITY;

CREATE POLICY tax_withholding_slips_tenant_isolation ON tax_withholding_slips
    FOR ALL TO app_user
    USING (company_id = app_current_company_id())
    WITH CHECK (company_id = app_current_company_id());

CREATE POLICY tax_withholding_slips_super_admin ON tax_withholding_slips
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- payroll_notification_tokens
-- ========================================
ALTER TABLE payroll_notification_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll_notification_tokens FORCE ROW LEVEL SECURITY;

CREATE POLICY payroll_notification_tokens_tenant_isolation ON payroll_notification_tokens
    FOR ALL TO app_user
    USING (company_id = app_current_company_id())
    WITH CHECK (company_id = app_current_company_id());

CREATE POLICY payroll_notification_tokens_super_admin ON payroll_notification_tokens
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- accounting_mappings
-- ========================================
ALTER TABLE accounting_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounting_mappings FORCE ROW LEVEL SECURITY;

CREATE POLICY accounting_mappings_tenant_isolation ON accounting_mappings
    FOR ALL TO app_user
    USING (company_id = app_current_company_id())
    WITH CHECK (company_id = app_current_company_id());

CREATE POLICY accounting_mappings_super_admin ON accounting_mappings
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- bank_transfer_exports
-- ========================================
ALTER TABLE bank_transfer_exports ENABLE ROW LEVEL SECURITY;
ALTER TABLE bank_transfer_exports FORCE ROW LEVEL SECURITY;

CREATE POLICY bank_transfer_exports_tenant_isolation ON bank_transfer_exports
    FOR ALL TO app_user
    USING (company_id = app_current_company_id())
    WITH CHECK (company_id = app_current_company_id());

CREATE POLICY bank_transfer_exports_super_admin ON bank_transfer_exports
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- audit_logs
-- ========================================
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY;

CREATE POLICY audit_logs_tenant_isolation ON audit_logs
    FOR ALL TO app_user
    USING (company_id = app_current_company_id() OR company_id IS NULL)
    WITH CHECK (true);

CREATE POLICY audit_logs_super_admin ON audit_logs
    FOR ALL TO app_user
    USING (app_is_super_admin());

-- ========================================
-- insurance_rates（company_id nullable）
-- ========================================
ALTER TABLE insurance_rates ENABLE ROW LEVEL SECURITY;
ALTER TABLE insurance_rates FORCE ROW LEVEL SECURITY;

CREATE POLICY insurance_rates_tenant_isolation ON insurance_rates
    FOR ALL TO app_user
    USING (company_id IS NULL OR company_id = app_current_company_id());

CREATE POLICY insurance_rates_super_admin ON insurance_rates
    FOR ALL TO app_user
    USING (app_is_super_admin());
