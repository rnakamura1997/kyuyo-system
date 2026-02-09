/** 認証関連の型定義 */

export interface UserInfo {
  id: number;
  username: string;
  email: string;
  full_name: string;
  is_super_admin: boolean;
  company_id: number;
  roles: string[];
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserInfo;
}
