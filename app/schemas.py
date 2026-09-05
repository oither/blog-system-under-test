from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# ========== User Schemas ==========
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True  # SQLAlchemy 2.0 兼容

class Token(BaseModel):
    access_token: str
    token_type: str

# ✅ 新增：登录请求 Schema（用于 JSON Body）
class LoginRequest(BaseModel):
    username: str
    password: str

# ========== Article Schemas ==========
class ArticleCreate(BaseModel):
    title: str
    content: str

class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class ArticleResponse(BaseModel):
    id: int
    title: str
    content: str
    author_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ========== Comment Schemas ==========
class CommentCreate(BaseModel):
    content: str

class CommentResponse(BaseModel):
    id: int
    content: str
    article_id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True