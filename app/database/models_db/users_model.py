from sqlalchemy import Column, String, Boolean, DateTime, Enum as SqlEnum
from sqlalchemy.sql import func
from app.database import Base
from app.models.user import UserRole
import uuid

class UserDB(Base):
    """用户数据库模型"""
    __tablename__ = "users" # 指定数据库表名为 "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(100))
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    role = Column(SqlEnum(UserRole), default=UserRole.USER, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"