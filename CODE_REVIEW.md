# コードレビュー報告（2026-02-11）

## 対象
- バックエンド: FastAPI (`backend/app`)
- フロントエンド: React + TypeScript (`frontend/src`)
- インストーラー/設計書: `installer/`, `kyuuyomeisai-design-docs/`

## 実施内容
- 設計書（要件/セキュリティ）と実装の整合性確認
- ビルド/静的チェック実行
- 重要APIの認可・認証・入力検証の目視確認

---

## 指摘事項（重要度順）

### 1) [High] フロントエンドがビルド不能（型定義不整合 + noUnused 系エラー）

**事象**
- `npm run build` が失敗し、デプロイ可能なフロントエンド成果物が生成できません。
- 主因は `ExtendedRouteObject extends RouteObject` の型定義不整合により、`path`/`element` が型として認識されないこと。
- さらに `noUnusedLocals` により未使用importが複数ファイルでエラー化。

**影響**
- CI/CD でフロントエンドのビルドが常時失敗。
- 本番反映ができない（リリースブロッカー）。

**根拠ファイル**
- `frontend/src/routes/routes.tsx`
- `frontend/src/App.tsx`
- `frontend/src/utils/menuGenerator.ts`
- `frontend/tsconfig.json`

**推奨対応**
- `RouteObject` 継承を見直し、`type ExtendedRouteObject = Omit<RouteObject, "children"> & { ... }` 等で明示定義。
- あるいは `path`/`element` 必須の独自Route型を作成。
- 未使用importを削除し、ビルドを通す。

---

### 2) [High] CSRF対策が設計書要件に対して未実装

**事象**
- 設計書では `CSRF Token` と `Origin/Referer チェック` を明記。
- 実装は `SameSite=strict` Cookie まではあるが、サーバー側CSRFトークン検証ミドルウェア/依存関係が存在しません。

**影響**
- ブラウザ挙動や将来のSameSite要件変更次第でCSRF耐性が不足。
- 設計準拠・監査観点でギャップ。

**根拠ファイル**
- `kyuuyomeisai-design-docs/09_security_design.md`
- `backend/app/main.py`
- `backend/app/api/v1/auth.py`

**推奨対応**
- `fastapi-csrf-protect` などでCSRFトークン発行/検証を導入。
- 変更系APIで `Origin/Referer` バリデーションを追加。

---

### 3) [Medium] ファイルアップロードに対するセキュリティ検証不足

**事象**
- 設計書ではアップロード時に拡張子/MIME/サイズ制限を要求。
- `attendance/import` はCSV読込のみで、ファイルサイズ・Content-Type・ヘッダ検証が不足。

**影響**
- 想定外入力による障害・DoSリスク（巨大ファイル、壊れたCSVなど）。
- セキュリティ設計との不一致。

**根拠ファイル**
- `kyuuyomeisai-design-docs/09_security_design.md`
- `backend/app/api/v1/attendance.py`

**推奨対応**
- `UploadFile.content_type` と拡張子を許可リスト化。
- リクエストサイズ上限（Nginx/FastAPI）と行数上限を実装。
- 例外時の行単位エラーレポートを追加。

---

### 4) [Medium] セキュリティ設定のデフォルト値が開発寄り（本番誤設定リスク）

**事象**
- `Settings` のデフォルトが `DEBUG=True`、プレースホルダ秘密鍵。
- インストーラでは本番値を書き込む前提だが、環境変数未設定時の安全側デフォルトではない。

**影響**
- 誤デプロイ時にデバッグ有効・弱い秘密値で起動するリスク。

**根拠ファイル**
- `backend/app/core/config.py`
- `backend/.env.example`
- `installer/config/env.template`

**推奨対応**
- `DEBUG=False` をデフォルト化。
- `JWT_SECRET` / `ENCRYPTION_KEY` 未設定時は起動エラーにする。

---

## 総評
- 現状は **設計資料が充実している一方、実装品質はPoC/初期構築段階** です。
- 最優先は **フロントビルドエラー解消（Issue #1）** と **CSRF実装（Issue #2）**。
- これら解消後に、入力検証強化・本番安全デフォルト化を進めることを推奨します。


## 追記（修正反映）
- フロントエンドのTypeScriptビルドエラー（ルート型不整合・未使用import）については、`fix: resolve frontend TypeScript build blockers` で修正済み。
- 再ビルド確認で `npm run build` は成功。
