"""認証関連スキーマ"""

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserInfo"


class UserInfo(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    is_super_admin: bool
    company_id: int
    roles: list[str]

    model_config = {"from_attributes": True}


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str
