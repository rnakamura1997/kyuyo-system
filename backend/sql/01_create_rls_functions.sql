-- RLS用共通関数

-- 現在の会社IDを取得
CREATE OR REPLACE FUNCTION app_current_company_id()
RETURNS BIGINT AS $$
BEGIN
    RETURN current_setting('app.current_company_id', true)::BIGINT;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

-- スーパー管理者判定
CREATE OR REPLACE FUNCTION app_is_super_admin()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN COALESCE(current_setting('app.is_super_admin', true)::BOOLEAN, false);
EXCEPTION WHEN OTHERS THEN
    RETURN false;
END;
$$ LANGUAGE plpgsql STABLE;
