-- 初期データ投入

-- ========================================
-- ロール定義
-- ========================================
INSERT INTO roles (code, name, description) VALUES
('super_admin', 'スーパー管理者', '全社横断管理、システム設定'),
('admin', '管理者', '会社内全権限'),
('accountant', '経理担当', '給与計算・帳票出力'),
('employee', '一般従業員', '自分の明細閲覧のみ')
ON CONFLICT (code) DO NOTHING;

-- ========================================
-- システム設定
-- ========================================
INSERT INTO system_settings (setting_key, setting_value, description) VALUES
('system_version', '"1.0.0"', 'システムバージョン'),
('default_night_start', '"22:00"', '深夜時間帯開始（デフォルト）'),
('default_night_end', '"05:00"', '深夜時間帯終了（デフォルト）'),
('default_overtime_rate', '1.25', '法定時間外割増率（デフォルト）'),
('default_night_rate', '0.25', '深夜割増率（デフォルト）'),
('default_holiday_rate', '1.35', '法定休日割増率（デフォルト）'),
('default_over60h_rate', '1.50', '月60時間超割増率（デフォルト）'),
('data_retention_years', '7', 'データ保持年数')
ON CONFLICT (setting_key) DO NOTHING;

-- ========================================
-- 社会保険定数
-- ========================================
INSERT INTO insurance_constants (constant_type, valid_from, limit_amount, description) VALUES
('bonus_health_limit', '2024-04-01', 5730000, '健康保険賞与上限（年度573万円）'),
('bonus_pension_limit', '2024-04-01', 1500000, '厚生年金賞与上限（月150万円）')
ON CONFLICT DO NOTHING;

-- ========================================
-- 通勤手当非課税限度額（2024年度時点）
-- ========================================
INSERT INTO commute_tax_limits (valid_from, commute_type, distance_from, distance_to, limit_amount) VALUES
-- 交通機関のみ
('2016-01-01', 'public_transport', NULL, NULL, 150000),
-- マイカー・自転車
('2016-01-01', 'car', 0.0, 2.0, 0),
('2016-01-01', 'car', 2.0, 10.0, 4200),
('2016-01-01', 'car', 10.0, 15.0, 7100),
('2016-01-01', 'car', 15.0, 25.0, 12900),
('2016-01-01', 'car', 25.0, 35.0, 18700),
('2016-01-01', 'car', 35.0, 45.0, 24400),
('2016-01-01', 'car', 45.0, 55.0, 28000),
('2016-01-01', 'car', 55.0, NULL, 31600)
ON CONFLICT DO NOTHING;
