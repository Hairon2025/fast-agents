from pydantic import BaseModel, Field, field_validator # , EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="用户邮箱")
    full_name: Optional[str] = Field(None, description="用户全名")
    is_active: bool = Field(True, description="用户是否激活")
    role: UserRole = Field(UserRole.USER, description="用户角色")

class UserCreate(UserBase):
    """创建用户模型"""
    password: str = Field(..., description="用户密码")

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """密码验证"""
        if len(v) < 6:
            raise ValueError('密码长度至少6位')
        return v

class UserUpdate(BaseModel):
    """更新用户模型"""
    email: Optional[str] = Field(None, description="用户邮箱")
    full_name: Optional[str] = Field(None, description="用户全名")
    is_active: Optional[bool] = Field(None, description="用户是否激活")
    role: Optional[UserRole] = Field(None, description="用户角色")
    password: Optional[str] = Field(None, description="用户密码")

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """密码验证（可选）"""
        if v is not None and len(v) < 6:
            raise ValueError('密码长度至少6位')
        return v

class UserInDB(UserBase):
    """数据库中的用户模型"""
    id: str = Field(..., description="用户ID")
    hashed_password: str = Field(..., description="哈希密码") # 存储哈希后的密码，不是明文
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True

class UserResponse(UserBase):
    """API响应用户模型（不包含密码信息）"""
    id: str = Field(..., description="用户ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

class UserListResponse(BaseModel):
    """用户列表响应模型"""
    users: List[UserResponse] = Field(..., description="用户列表")
    total: int = Field(..., description="用户总数")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")