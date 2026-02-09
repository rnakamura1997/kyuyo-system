"""共通スキーマ"""

from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """ページネーション付きレスポンス"""
    items: list[T]
    total: int
    page: int
    limit: int
    pages: int


class ErrorResponse(BaseModel):
    """エラーレスポンス"""
    detail: str
    error_code: str | None = None
    field_errors: dict[str, list[str]] | None = None
