from sqlalchemy import Column, String, Boolean, DateTime, Enum as SqlEnum
from sqlalchemy.sql import func
from app.database.mysql_db import BaseModel  # 修改这里：导入 BaseModel
from app.models.user import UserRole
import uuid

class UserDB(BaseModel):
    """用户数据库模型"""
    __tablename__ = "users" # 指定数据库表名为 "users"
    
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(100))
    hashed_password = Column(String(255), nullable=False)
    role = Column(SqlEnum(UserRole), default=UserRole.USER, nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"