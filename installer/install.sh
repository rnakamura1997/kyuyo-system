#!/usr/bin/env bash
# =============================================================================
# kyuuyomeisai (給与明細管理システム) インストーラー
# =============================================================================
#
# 使用方法:
#   sudo bash install.sh
#
# 概要:
#   Ubuntu サーバーに kyuuyomeisai 給与明細管理システムをインストールします。
#   PostgreSQL, Redis, Nginx, systemd サービスを構成し、
#   初期管理者アカウントおよび初期会社を作成します。
#
# =============================================================================

set -euo pipefail

# =============================================================================
# 定数・カラー定義
# =============================================================================
readonly INSTALL_DIR="/opt/kyuuyomeisai"
readonly VENV_DIR="${INSTALL_DIR}/venv"
readonly WEB_DIR="/var/www/kyuuyomeisai"
readonly FILE_STORAGE_DIR="/var/kyuuyomeisai/files"
readonly ENV_FILE="${INSTALL_DIR}/.env"
readonly SERVICE_NAME="kyuuyomeisai"
readonly NGINX_CONF="/etc/nginx/sites-available/${SERVICE_NAME}"
readonly SYSTEMD_UNIT="/etc/systemd/system/${SERVICE_NAME}.service"
readonly LOG_FILE="/var/log/kyuuyomeisai-install.log"

# プロジェクトルート（このスクリプトの親ディレクトリ）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# カラー出力
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly NC='\033[0m' # No Color

# =============================================================================
# ユーティリティ関数
# =============================================================================

log_info() {
    echo -e "${BLUE}[情報]${NC} $1"
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') $1" >> "${LOG_FILE}" 2>/dev/null || true
}

log_success() {
    echo -e "${GREEN}[成功]${NC} $1"
    echo "[OK]   $(date '+%Y-%m-%d %H:%M:%S') $1" >> "${LOG_FILE}" 2>/dev/null || true
}

log_warn() {
    echo -e "${YELLOW}[警告]${NC} $1"
    echo "[WARN] $(date '+%Y-%m-%d %H:%M:%S') $1" >> "${LOG_FILE}" 2>/dev/null || true
}

log_error() {
    echo -e "${RED}[エラー]${NC} $1" >&2
    echo "[ERR]  $(date '+%Y-%m-%d %H:%M:%S') $1" >> "${LOG_FILE}" 2>/dev/null || true
}

log_step() {
    echo ""
    echo -e "${CYAN}${BOLD}========================================${NC}"
    echo -e "${CYAN}${BOLD}  $1${NC}"
    echo -e "${CYAN}${BOLD}========================================${NC}"
    echo ""
}

# エラー時のクリーンアップ
cleanup_on_error() {
    log_error "インストール中にエラーが発生しました。"
    log_error "詳細は ${LOG_FILE} を確認してください。"
    log_error "部分インストールをクリーンアップするには uninstall.sh を実行してください。"
    exit 1
}

trap cleanup_on_error ERR

# プロンプトでユーザー入力を取得（デフォルト値付き）
prompt_input() {
    local prompt_msg="$1"
    local default_val="${2:-}"
    local input_val

    if [[ -n "${default_val}" ]]; then
        read -rp "$(echo -e "${YELLOW}${prompt_msg} [${default_val}]: ${NC}")" input_val
        echo "${input_val:-${default_val}}"
    else
        read -rp "$(echo -e "${YELLOW}${prompt_msg}: ${NC}")" input_val
        echo "${input_val}"
    fi
}

# パスワード入力（非表示）
prompt_password() {
    local prompt_msg="$1"
    local password

    while true; do
        read -srp "$(echo -e "${YELLOW}${prompt_msg}: ${NC}")" password
        echo ""
        if [[ -z "${password}" ]]; then
            log_error "パスワードは空にできません。再度入力してください。"
            continue
        fi
        local password_confirm
        read -srp "$(echo -e "${YELLOW}${prompt_msg} (確認): ${NC}")" password_confirm
        echo ""
        if [[ "${password}" != "${password_confirm}" ]]; then
            log_error "パスワードが一致しません。再度入力してください。"
            continue
        fi
        break
    done
    echo "${password}"
}

# =============================================================================
# Step 0: 前提条件チェック
# =============================================================================
check_prerequisites() {
    log_step "Step 0: 前提条件チェック"

    # root 権限チェック
    if [[ "${EUID}" -ne 0 ]]; then
        log_error "このスクリプトは root 権限で実行する必要があります。"
        log_error "使用方法: sudo bash install.sh"
        exit 1
    fi
    log_success "root 権限を確認しました。"

    # OS チェック
    if [[ ! -f /etc/os-release ]]; then
        log_error "/etc/os-release が見つかりません。Ubuntu が必要です。"
        exit 1
    fi

    local os_id
    os_id=$(. /etc/os-release && echo "${ID}")
    if [[ "${os_id}" != "ubuntu" ]]; then
        log_error "このインストーラーは Ubuntu 専用です。検出された OS: ${os_id}"
        exit 1
    fi

    local os_version
    os_version=$(. /etc/os-release && echo "${VERSION_ID}")
    log_success "OS を確認しました: Ubuntu ${os_version}"

    # Python 3.11+ チェック
    if ! command -v python3 &>/dev/null; then
        log_error "Python3 がインストールされていません。"
        exit 1
    fi

    local python_version
    python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    local python_major python_minor
    python_major=$(echo "${python_version}" | cut -d. -f1)
    python_minor=$(echo "${python_version}" | cut -d. -f2)

    if [[ "${python_major}" -lt 3 ]] || { [[ "${python_major}" -eq 3 ]] && [[ "${python_minor}" -lt 11 ]]; }; then
        log_error "Python 3.11 以上が必要です。現在のバージョン: ${python_version}"
        exit 1
    fi
    log_success "Python バージョンを確認しました: ${python_version}"

    # Node.js 18+ チェック
    if ! command -v node &>/dev/null; then
        log_error "Node.js がインストールされていません。"
        exit 1
    fi

    local node_version
    node_version=$(node --version | sed 's/^v//')
    local node_major
    node_major=$(echo "${node_version}" | cut -d. -f1)

    if [[ "${node_major}" -lt 18 ]]; then
        log_error "Node.js 18 以上が必要です。現在のバージョン: v${node_version}"
        exit 1
    fi
    log_success "Node.js バージョンを確認しました: v${node_version}"

    # npm チェック
    if ! command -v npm &>/dev/null; then
        log_error "npm がインストールされていません。"
        exit 1
    fi
    log_success "npm を確認しました: $(npm --version)"

    # プロジェクトディレクトリ確認
    if [[ ! -d "${PROJECT_ROOT}/backend" ]] || [[ ! -d "${PROJECT_ROOT}/frontend" ]]; then
        log_error "プロジェクトディレクトリが正しくありません。"
        log_error "backend/ と frontend/ ディレクトリが ${PROJECT_ROOT} に存在する必要があります。"
        exit 1
    fi
    log_success "プロジェクトディレクトリを確認しました: ${PROJECT_ROOT}"
}

# =============================================================================
# Step 1: システムパッケージのインストール
# =============================================================================
install_system_packages() {
    log_step "Step 1: システムパッケージのインストール"

    log_info "パッケージリストを更新しています..."
    apt-get update -qq

    local packages=(
        python3-pip
        python3-venv
        nginx
        redis-server
        postgresql
        postgresql-contrib
        libpq-dev
        build-essential
        git
    )

    log_info "必要なパッケージをインストールしています..."
    for pkg in "${packages[@]}"; do
        if dpkg -l "${pkg}" &>/dev/null 2>&1; then
            log_info "  ${pkg} ... 既にインストール済み"
        else
            log_info "  ${pkg} をインストール中..."
            apt-get install -y -qq "${pkg}"
        fi
    done

    # PostgreSQL と Redis の起動確認
    systemctl start postgresql || true
    systemctl enable postgresql
    systemctl start redis-server || true
    systemctl enable redis-server

    log_success "システムパッケージのインストールが完了しました。"
}

# =============================================================================
# Step 2: PostgreSQL セットアップ
# =============================================================================
setup_postgresql() {
    log_step "Step 2: PostgreSQL データベースセットアップ"

    log_info "データベース接続情報を入力してください。"
    echo ""

    DB_HOST=$(prompt_input "データベースホスト" "localhost")
    DB_PORT=$(prompt_input "データベースポート" "5432")
    DB_NAME=$(prompt_input "データベース名" "kyuuyomeisai")
    DB_USER=$(prompt_input "データベースユーザー名" "kyuuyomeisai_app")
    DB_PASS=$(prompt_password "データベースパスワード")

    echo ""
    log_info "データベースとユーザーを作成しています..."

    # PostgreSQL ユーザーが既に存在するか確認して作成
    if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1; then
        log_warn "ユーザー '${DB_USER}' は既に存在します。パスワードを更新します。"
        sudo -u postgres psql -c "ALTER USER \"${DB_USER}\" WITH PASSWORD '${DB_PASS}';"
    else
        sudo -u postgres psql -c "CREATE USER \"${DB_USER}\" WITH PASSWORD '${DB_PASS}';"
        log_success "データベースユーザー '${DB_USER}' を作成しました。"
    fi

    # データベースが既に存在するか確認して作成
    if sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1; then
        log_warn "データベース '${DB_NAME}' は既に存在します。"
    else
        sudo -u postgres psql -c "CREATE DATABASE \"${DB_NAME}\" OWNER \"${DB_USER}\" ENCODING 'UTF8' LC_COLLATE='ja_JP.UTF-8' LC_CTYPE='ja_JP.UTF-8' TEMPLATE=template0;" 2>/dev/null || \
        sudo -u postgres psql -c "CREATE DATABASE \"${DB_NAME}\" OWNER \"${DB_USER}\" ENCODING 'UTF8';"
        log_success "データベース '${DB_NAME}' を作成しました。"
    fi

    # 権限付与
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE \"${DB_NAME}\" TO \"${DB_USER}\";"
    sudo -u postgres psql -d "${DB_NAME}" -c "GRANT ALL ON SCHEMA public TO \"${DB_USER}\";"
    sudo -u postgres psql -d "${DB_NAME}" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO \"${DB_USER}\";"
    sudo -u postgres psql -d "${DB_NAME}" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO \"${DB_USER}\";"

    log_success "PostgreSQL のセットアップが完了しました。"
}

# =============================================================================
# Step 3: アプリケーションディレクトリ作成
# =============================================================================
setup_directories() {
    log_step "Step 3: アプリケーションディレクトリの作成"

    # システムユーザーの作成
    if id "${SERVICE_NAME}" &>/dev/null; then
        log_warn "システムユーザー '${SERVICE_NAME}' は既に存在します。"
    else
        useradd --system --no-create-home --shell /usr/sbin/nologin "${SERVICE_NAME}"
        log_success "システムユーザー '${SERVICE_NAME}' を作成しました。"
    fi

    # ディレクトリの作成
    mkdir -p "${INSTALL_DIR}"
    mkdir -p "${WEB_DIR}"
    mkdir -p "${FILE_STORAGE_DIR}"
    mkdir -p "$(dirname "${LOG_FILE}")"

    # バックエンドコードのコピー
    log_info "バックエンドコードをコピーしています..."
    cp -r "${PROJECT_ROOT}/backend/"* "${INSTALL_DIR}/"
    # backend ディレクトリ内にサブディレクトリとして配置
    # 構成: /opt/kyuuyomeisai/{app,alembic,alembic.ini,pyproject.toml,sql,scripts}

    # backend サブディレクトリとして再配置
    mkdir -p "${INSTALL_DIR}/backend"
    for item in app alembic alembic.ini pyproject.toml sql scripts; do
        if [[ -e "${INSTALL_DIR}/${item}" ]]; then
            cp -r "${INSTALL_DIR}/${item}" "${INSTALL_DIR}/backend/"
        fi
    done
    # 直下のコピーを削除（backend 以下に正規配置）
    for item in app alembic alembic.ini pyproject.toml sql scripts; do
        if [[ -e "${INSTALL_DIR}/${item}" ]] && [[ -e "${INSTALL_DIR}/backend/${item}" ]]; then
            rm -rf "${INSTALL_DIR}/${item}"
        fi
    done

    # 権限設定
    chown -R "${SERVICE_NAME}:${SERVICE_NAME}" "${INSTALL_DIR}"
    chown -R "${SERVICE_NAME}:${SERVICE_NAME}" "${FILE_STORAGE_DIR}"
    chmod 750 "${INSTALL_DIR}"

    log_success "アプリケーションディレクトリを作成しました。"
}

# =============================================================================
# Step 4: Python 仮想環境セットアップ
# =============================================================================
setup_python_venv() {
    log_step "Step 4: Python 仮想環境のセットアップ"

    log_info "仮想環境を作成しています: ${VENV_DIR}"
    python3 -m venv "${VENV_DIR}"

    log_info "pip をアップグレードしています..."
    "${VENV_DIR}/bin/pip" install --upgrade pip setuptools wheel

    # pyproject.toml からの依存関係インストール
    if [[ -f "${INSTALL_DIR}/backend/pyproject.toml" ]]; then
        log_info "Poetry の pyproject.toml から依存関係をインストールしています..."

        # pip で直接 pyproject.toml からインストールを試みる
        # poetry-core がビルドバックエンドなので、まず poetry-core をインストール
        "${VENV_DIR}/bin/pip" install poetry-core

        # pip install . を使って pyproject.toml から依存関係をインストール
        cd "${INSTALL_DIR}/backend"
        "${VENV_DIR}/bin/pip" install .
        cd "${SCRIPT_DIR}"
    fi

    # requirements.txt が存在する場合はそちらも使用
    if [[ -f "${PROJECT_ROOT}/backend/requirements.txt" ]]; then
        log_info "requirements.txt から追加の依存関係をインストールしています..."
        "${VENV_DIR}/bin/pip" install -r "${PROJECT_ROOT}/backend/requirements.txt"
    fi

    # bcrypt を明示的にインストール（初期管理者パスワードハッシュ生成用）
    "${VENV_DIR}/bin/pip" install bcrypt

    chown -R "${SERVICE_NAME}:${SERVICE_NAME}" "${VENV_DIR}"

    log_success "Python 仮想環境のセットアップが完了しました。"
}

# =============================================================================
# Step 5: フロントエンドビルド
# =============================================================================
build_frontend() {
    log_step "Step 5: フロントエンドのビルド"

    cd "${PROJECT_ROOT}/frontend"

    log_info "npm パッケージをインストールしています..."
    npm install

    log_info "フロントエンドをビルドしています..."
    npm run build

    # Vite のビルド出力は dist/ ディレクトリ
    if [[ -d "${PROJECT_ROOT}/frontend/dist" ]]; then
        log_info "ビルド出力を ${WEB_DIR} にコピーしています..."
        rm -rf "${WEB_DIR:?}/"*
        cp -r "${PROJECT_ROOT}/frontend/dist/"* "${WEB_DIR}/"
    else
        log_error "フロントエンドのビルド出力が見つかりません: ${PROJECT_ROOT}/frontend/dist"
        exit 1
    fi

    chown -R www-data:www-data "${WEB_DIR}"

    cd "${SCRIPT_DIR}"
    log_success "フロントエンドのビルドが完了しました。"
}

# =============================================================================
# Step 6: 設定ファイルの生成
# =============================================================================
generate_configuration() {
    log_step "Step 6: 設定ファイルの生成"

    # JWT シークレットの生成
    log_info "JWT シークレットを生成しています..."
    JWT_SECRET=$(openssl rand -hex 32)

    # Fernet 暗号化キーの生成
    log_info "暗号化キーを生成しています..."
    ENCRYPTION_KEY=$("${VENV_DIR}/bin/python3" -c "
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key.decode())
")

    # ドメイン設定
    DOMAIN=$(prompt_input "サーバーのドメイン名またはIPアドレス" "localhost")

    # .env ファイルの生成
    log_info ".env ファイルを生成しています..."

    # テンプレートから .env を生成
    if [[ -f "${SCRIPT_DIR}/config/env.template" ]]; then
        export DB_HOST DB_PORT DB_NAME DB_USER DB_PASS JWT_SECRET ENCRYPTION_KEY DOMAIN
        envsubst '${DB_HOST} ${DB_PORT} ${DB_NAME} ${DB_USER} ${DB_PASS} ${JWT_SECRET} ${ENCRYPTION_KEY} ${DOMAIN}' \
            < "${SCRIPT_DIR}/config/env.template" \
            > "${ENV_FILE}"
    else
        # テンプレートがない場合は直接生成
        cat > "${ENV_FILE}" <<ENVEOF
APP_ENV=production
DEBUG=false
DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}
DATABASE_SYNC_URL=postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}
JWT_SECRET=${JWT_SECRET}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
REDIS_URL=redis://localhost:6379/0
FILE_STORAGE_PATH=${FILE_STORAGE_DIR}
CORS_ORIGINS=["https://${DOMAIN}"]
ENCRYPTION_KEY=${ENCRYPTION_KEY}
ENVEOF
    fi

    # .env ファイルのパーミッション設定（機密情報保護）
    chown "${SERVICE_NAME}:${SERVICE_NAME}" "${ENV_FILE}"
    chmod 600 "${ENV_FILE}"

    # alembic.ini のデータベース URL を更新
    local alembic_ini="${INSTALL_DIR}/backend/alembic.ini"
    if [[ -f "${alembic_ini}" ]]; then
        log_info "alembic.ini のデータベース URL を更新しています..."
        sed -i "s|^sqlalchemy.url = .*|sqlalchemy.url = postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}|" "${alembic_ini}"
        chown "${SERVICE_NAME}:${SERVICE_NAME}" "${alembic_ini}"
    fi

    log_success "設定ファイルの生成が完了しました。"
}

# =============================================================================
# Step 7: データベース初期化
# =============================================================================
initialize_database() {
    log_step "Step 7: データベースの初期化"

    local sql_dir="${INSTALL_DIR}/backend/sql"
    local db_conn="postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

    # Alembic マイグレーション実行
    if [[ -d "${INSTALL_DIR}/backend/alembic" ]]; then
        log_info "Alembic マイグレーションを実行しています..."
        cd "${INSTALL_DIR}/backend"
        sudo -u "${SERVICE_NAME}" "${VENV_DIR}/bin/alembic" upgrade head || {
            log_warn "Alembic マイグレーションに失敗しました。テーブルが既に存在する可能性があります。"
        }
        cd "${SCRIPT_DIR}"
    fi

    # SQL ファイルを順番に実行
    local sql_files=(
        "01_create_rls_functions.sql"
        "02_create_rls_policies.sql"
        "03_initial_data.sql"
    )

    for sql_file in "${sql_files[@]}"; do
        local sql_path="${sql_dir}/${sql_file}"
        if [[ -f "${sql_path}" ]]; then
            log_info "SQL ファイルを実行しています: ${sql_file}"
            PGPASSWORD="${DB_PASS}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -f "${sql_path}" 2>&1 || {
                log_warn "SQL ファイル ${sql_file} の一部でエラーが発生しました（既存データの可能性があります）。"
            }
        else
            log_warn "SQL ファイルが見つかりません: ${sql_path}"
        fi
    done

    log_success "データベースの初期化が完了しました。"
}

# =============================================================================
# Step 8: Nginx セットアップ
# =============================================================================
setup_nginx() {
    log_step "Step 8: Nginx の設定"

    # Nginx 設定ファイルのコピー
    if [[ -f "${SCRIPT_DIR}/config/nginx.conf.template" ]]; then
        log_info "Nginx 設定ファイルをコピーしています..."
        cp "${SCRIPT_DIR}/config/nginx.conf.template" "${NGINX_CONF}"
    else
        log_info "Nginx 設定ファイルを生成しています..."
        cat > "${NGINX_CONF}" <<'NGINXEOF'
server {
    listen 80;
    server_name _;
    client_max_body_size 50M;

    root /var/www/kyuuyomeisai;
    index index.html;

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
NGINXEOF
    fi

    # サイトを有効化
    if [[ -L "/etc/nginx/sites-enabled/${SERVICE_NAME}" ]]; then
        rm "/etc/nginx/sites-enabled/${SERVICE_NAME}"
    fi
    ln -s "${NGINX_CONF}" "/etc/nginx/sites-enabled/${SERVICE_NAME}"

    # デフォルトサイトを無効化
    if [[ -L /etc/nginx/sites-enabled/default ]]; then
        log_info "デフォルトの Nginx サイトを無効化しています..."
        rm /etc/nginx/sites-enabled/default
    fi

    # Nginx 設定テスト
    log_info "Nginx 設定をテストしています..."
    if nginx -t 2>&1; then
        log_success "Nginx 設定は正常です。"
    else
        log_error "Nginx 設定にエラーがあります。"
        exit 1
    fi

    log_success "Nginx の設定が完了しました。"
}

# =============================================================================
# Step 9: systemd サービスセットアップ
# =============================================================================
setup_systemd() {
    log_step "Step 9: systemd サービスの設定"

    # systemd ユニットファイルのコピー
    if [[ -f "${SCRIPT_DIR}/config/systemd.service" ]]; then
        log_info "systemd ユニットファイルをコピーしています..."
        cp "${SCRIPT_DIR}/config/systemd.service" "${SYSTEMD_UNIT}"
    else
        log_info "systemd ユニットファイルを生成しています..."
        cat > "${SYSTEMD_UNIT}" <<SERVICEEOF
[Unit]
Description=kyuuyomeisai Payroll Management System
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=${SERVICE_NAME}
Group=${SERVICE_NAME}
WorkingDirectory=${INSTALL_DIR}/backend
Environment=PATH=${VENV_DIR}/bin
EnvironmentFile=${ENV_FILE}
ExecStart=${VENV_DIR}/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICEEOF
    fi

    # systemd リロード
    systemctl daemon-reload
    log_success "systemd サービスの設定が完了しました。"
}

# =============================================================================
# Step 10: 初期管理者アカウントの作成
# =============================================================================
create_admin_account() {
    log_step "Step 10: 初期管理者アカウントの作成"

    log_info "管理者アカウント情報を入力してください。"
    echo ""

    ADMIN_USERNAME=$(prompt_input "管理者ユーザー名" "admin")
    ADMIN_EMAIL=$(prompt_input "管理者メールアドレス" "admin@example.com")
    ADMIN_FULLNAME=$(prompt_input "管理者氏名" "システム管理者")
    ADMIN_PASSWORD=$(prompt_password "管理者パスワード")

    echo ""
    log_info "管理者アカウントを作成しています..."

    # bcrypt でパスワードハッシュを生成
    local password_hash
    password_hash=$("${VENV_DIR}/bin/python3" -c "
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
print(pwd_context.hash('${ADMIN_PASSWORD}'))
")

    # SQL でユーザーを挿入（company_id は Step 11 で作成する会社の ID を使用）
    # まず一時的に company_id=1 で作成し、後で更新する
    # super_admin なので全社横断アクセスが可能
    PGPASSWORD="${DB_PASS}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" <<SQLEOF
DO \$\$
DECLARE
    v_user_id BIGINT;
    v_role_id BIGINT;
BEGIN
    -- 管理者ユーザーの挿入（company_id は後で更新）
    INSERT INTO users (company_id, username, email, password_hash, full_name, is_super_admin, is_active, created_at, updated_at)
    VALUES (1, '${ADMIN_USERNAME}', '${ADMIN_EMAIL}', '${password_hash}', '${ADMIN_FULLNAME}', true, true, NOW(), NOW())
    ON CONFLICT (username) DO UPDATE SET
        email = EXCLUDED.email,
        password_hash = EXCLUDED.password_hash,
        full_name = EXCLUDED.full_name,
        is_super_admin = EXCLUDED.is_super_admin,
        updated_at = NOW()
    RETURNING id INTO v_user_id;

    -- super_admin ロールの ID を取得
    SELECT id INTO v_role_id FROM roles WHERE code = 'super_admin';

    -- ロール割り当て
    IF v_role_id IS NOT NULL THEN
        INSERT INTO user_roles (company_id, user_id, role_id, created_at)
        VALUES (1, v_user_id, v_role_id, NOW())
        ON CONFLICT (user_id, role_id) DO NOTHING;
    END IF;
END \$\$;
SQLEOF

    if [[ $? -eq 0 ]]; then
        log_success "管理者アカウント '${ADMIN_USERNAME}' を作成しました。"
    else
        log_error "管理者アカウントの作成に失敗しました。"
        exit 1
    fi
}

# =============================================================================
# Step 11: 初期会社の作成
# =============================================================================
create_initial_company() {
    log_step "Step 11: 初期会社の作成"

    log_info "初期会社情報を入力してください。"
    echo ""

    COMPANY_NAME=$(prompt_input "会社名" "サンプル株式会社")
    CLOSING_DAY=$(prompt_input "締め日（1-31）" "25")
    PAYMENT_DAY=$(prompt_input "支払日（1-31）" "25")

    echo ""
    log_info "初期会社を作成しています..."

    # 締め日・支払日のバリデーション
    if [[ "${CLOSING_DAY}" -lt 1 ]] || [[ "${CLOSING_DAY}" -gt 31 ]]; then
        log_error "締め日は 1-31 の範囲で指定してください。"
        exit 1
    fi

    if [[ "${PAYMENT_DAY}" -lt 1 ]] || [[ "${PAYMENT_DAY}" -gt 31 ]]; then
        log_error "支払日は 1-31 の範囲で指定してください。"
        exit 1
    fi

    PGPASSWORD="${DB_PASS}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" <<SQLEOF
DO \$\$
DECLARE
    v_company_id BIGINT;
BEGIN
    -- 会社の挿入
    INSERT INTO companies (company_id, name, closing_day, payment_day, payment_month_offset, created_at, updated_at)
    VALUES (1, '${COMPANY_NAME}', ${CLOSING_DAY}, ${PAYMENT_DAY}, 1, NOW(), NOW())
    ON CONFLICT (company_id) DO UPDATE SET
        name = EXCLUDED.name,
        closing_day = EXCLUDED.closing_day,
        payment_day = EXCLUDED.payment_day,
        updated_at = NOW()
    RETURNING id INTO v_company_id;

    -- 管理者ユーザーの company_id を更新
    UPDATE users SET company_id = 1 WHERE username = '${ADMIN_USERNAME}' AND company_id = 1;
    UPDATE user_roles SET company_id = 1 WHERE user_id = (SELECT id FROM users WHERE username = '${ADMIN_USERNAME}');
END \$\$;
SQLEOF

    if [[ $? -eq 0 ]]; then
        log_success "初期会社 '${COMPANY_NAME}' を作成しました。"
    else
        log_error "初期会社の作成に失敗しました。"
        exit 1
    fi
}

# =============================================================================
# Step 12: サービスの起動
# =============================================================================
start_services() {
    log_step "Step 12: サービスの起動"

    # Nginx の再起動
    log_info "Nginx を再起動しています..."
    systemctl enable nginx
    systemctl restart nginx
    log_success "Nginx を起動しました。"

    # Redis の確認
    log_info "Redis を確認しています..."
    systemctl enable redis-server
    systemctl restart redis-server
    log_success "Redis を起動しました。"

    # kyuuyomeisai サービスの起動
    log_info "kyuuyomeisai サービスを起動しています..."
    systemctl enable "${SERVICE_NAME}"
    systemctl start "${SERVICE_NAME}"

    # 起動確認（5秒待機）
    sleep 3
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        log_success "kyuuyomeisai サービスを起動しました。"
    else
        log_warn "kyuuyomeisai サービスの起動に時間がかかっています。"
        log_warn "状態確認: systemctl status ${SERVICE_NAME}"
    fi

    log_success "全てのサービスが起動しました。"
}

# =============================================================================
# インストール完了サマリー
# =============================================================================
show_summary() {
    echo ""
    echo -e "${GREEN}${BOLD}=============================================${NC}"
    echo -e "${GREEN}${BOLD}  インストールが完了しました${NC}"
    echo -e "${GREEN}${BOLD}=============================================${NC}"
    echo ""
    echo -e "${BOLD}  システム情報:${NC}"
    echo -e "    アプリケーション:  kyuuyomeisai 給与明細管理システム v1.0.0"
    echo -e "    インストール先:    ${INSTALL_DIR}"
    echo -e "    Web ルート:        ${WEB_DIR}"
    echo -e "    ファイル保存先:    ${FILE_STORAGE_DIR}"
    echo -e "    環境設定:          ${ENV_FILE}"
    echo -e "    ログファイル:      ${LOG_FILE}"
    echo ""
    echo -e "${BOLD}  データベース:${NC}"
    echo -e "    ホスト:            ${DB_HOST}:${DB_PORT}"
    echo -e "    データベース名:    ${DB_NAME}"
    echo -e "    ユーザー:          ${DB_USER}"
    echo ""
    echo -e "${BOLD}  管理者アカウント:${NC}"
    echo -e "    ユーザー名:        ${ADMIN_USERNAME}"
    echo -e "    メール:            ${ADMIN_EMAIL}"
    echo ""
    echo -e "${BOLD}  アクセス URL:${NC}"
    if [[ "${DOMAIN}" == "localhost" ]]; then
        echo -e "    ${CYAN}http://localhost/${NC}"
    else
        echo -e "    ${CYAN}http://${DOMAIN}/${NC}"
    fi
    echo -e "    API ヘルスチェック: ${CYAN}http://${DOMAIN}/api/health${NC}"
    echo ""
    echo -e "${BOLD}  サービス管理コマンド:${NC}"
    echo -e "    起動:   ${YELLOW}sudo systemctl start ${SERVICE_NAME}${NC}"
    echo -e "    停止:   ${YELLOW}sudo systemctl stop ${SERVICE_NAME}${NC}"
    echo -e "    再起動: ${YELLOW}sudo systemctl restart ${SERVICE_NAME}${NC}"
    echo -e "    状態:   ${YELLOW}sudo systemctl status ${SERVICE_NAME}${NC}"
    echo -e "    ログ:   ${YELLOW}sudo journalctl -u ${SERVICE_NAME} -f${NC}"
    echo ""
    echo -e "${BOLD}  次のステップ:${NC}"
    echo -e "    1. HTTPS の設定（Let's Encrypt 推奨）"
    echo -e "       ${YELLOW}sudo apt install certbot python3-certbot-nginx${NC}"
    echo -e "       ${YELLOW}sudo certbot --nginx -d ${DOMAIN}${NC}"
    echo -e "    2. .env ファイルの CORS_ORIGINS を本番ドメインに更新"
    echo -e "    3. ファイアウォールの設定（80, 443 ポートの開放）"
    echo -e "    4. 定期バックアップの設定"
    echo ""
    echo -e "${GREEN}${BOLD}=============================================${NC}"
    echo ""
}

# =============================================================================
# メイン処理
# =============================================================================
main() {
    echo ""
    echo -e "${CYAN}${BOLD}=============================================${NC}"
    echo -e "${CYAN}${BOLD}  kyuuyomeisai 給与明細管理システム${NC}"
    echo -e "${CYAN}${BOLD}  インストーラー v1.0.0${NC}"
    echo -e "${CYAN}${BOLD}=============================================${NC}"
    echo ""
    echo -e "  このスクリプトは以下をインストール・設定します:"
    echo -e "    - PostgreSQL データベース"
    echo -e "    - Python バックエンド (FastAPI + Uvicorn)"
    echo -e "    - React フロントエンド"
    echo -e "    - Nginx リバースプロキシ"
    echo -e "    - Redis キャッシュ"
    echo -e "    - systemd サービス"
    echo ""

    read -rp "$(echo -e "${YELLOW}インストールを開始しますか？ [Y/n]: ${NC}")" confirm
    if [[ "${confirm,,}" == "n" ]]; then
        log_info "インストールを中止しました。"
        exit 0
    fi

    # ログファイルの初期化
    mkdir -p "$(dirname "${LOG_FILE}")"
    echo "=== kyuuyomeisai インストールログ ===" > "${LOG_FILE}"
    echo "開始時刻: $(date '+%Y-%m-%d %H:%M:%S')" >> "${LOG_FILE}"
    echo "" >> "${LOG_FILE}"

    check_prerequisites
    install_system_packages
    setup_postgresql
    setup_directories
    setup_python_venv
    build_frontend
    generate_configuration
    initialize_database
    setup_nginx
    setup_systemd
    create_admin_account
    create_initial_company
    start_services

    echo "完了時刻: $(date '+%Y-%m-%d %H:%M:%S')" >> "${LOG_FILE}"
    show_summary
}

# スクリプト実行
main "$@"
