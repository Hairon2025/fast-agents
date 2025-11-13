from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
from sqlalchemy.orm import Session
# from app.config import settings
from app.database.models_db.users_model import UserDB
from app.models.user import UserCreate, UserUpdate, UserResponse, UserListResponse, LoginRequest
from app.tools.security import PasswordManager, JWTManager

class UserService:
    """用户服务类，处理用户相关操作"""

    @classmethod
    def _generate_user_id(cls) -> str:
        """生成唯一用户ID"""
        return str(uuid.uuid4())

    @classmethod
    def _get_current_time(cls) -> datetime:
        """获取当前时间"""
        return datetime.now()

    @classmethod
    async def create_user(cls, db: Session, user_data: UserCreate) -> UserResponse:
        """创建新用户"""

        # 检查用户名是否已存在
        existing_user = db.query(UserDB).filter(
            (UserDB.username == user_data.username) | 
            (UserDB.email == user_data.email)
        ).first()

        if existing_user:
            if existing_user.email == user_data.email:
                raise ValueError("邮箱已存在")
            else:
                raise ValueError("用户名已存在")

        
        # 哈希密码
        hashed_password = PasswordManager.get_password_hash(user_data.password)

        user_in_db = UserDB(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password,  # 存储哈希后的密码
            is_active=user_data.is_active,
            role=user_data.role,
        )

        db.add(user_in_db)
        db.commit()
        db.refresh(user_in_db)

        return cls._db_to_response(user_in_db)

    @classmethod
    async def get_user_by_id(cls,db:Session, user_id: str) -> Optional[UserResponse]:
        """根据ID获取用户"""
        user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if user:
            return cls._db_to_response(user)
        return None
    
    @classmethod
    async def get_user_by_username(cls, db: Session, username: str) -> Optional[UserDB]:
        """根据用户名获取用户（内部使用，返回完整数据库模型）"""
        return db.query(UserDB).filter(UserDB.username == username).first()
    
    @classmethod
    async def authenticate_user(cls, db: Session, login_data: LoginRequest) -> Optional[UserDB]:
        """用户认证"""
        db_user = await cls.get_user_by_username(db, login_data.username)
        if not db_user:
            return None
        if not PasswordManager.verify_password(login_data.password, db_user.hashed_password):
            return None
        return db_user
    
    @classmethod
    async def login_user(cls, db: Session, login_data: LoginRequest) -> Optional[dict]:
        """用户登录，返回token"""
        db_user = await cls.authenticate_user(db, login_data)
        if not db_user:
            return None
        
        # 创建access token
        access_token_expires = timedelta(minutes=30)
        access_token = JWTManager.create_access_token(
            data={"sub": db_user.username, "user_id": db_user.id},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": access_token_expires.total_seconds(),
            "user": cls._db_to_response(db_user)
        }
    
    @classmethod
    async def get_current_user(cls, db: Session, token: str) -> Optional[UserResponse]:
        """根据token获取当前用户"""
        payload = JWTManager.verify_token(token)
        if not payload:
            return None
        
        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        if username is None or user_id is None:
            return None
        
        db_user = await cls.get_user_by_username(db, username)
        if db_user and db_user.id == user_id and db_user.is_active:
            return cls._db_to_response(db_user)
        return None

    @classmethod
    async def get_users(
        cls, 
        db: Session,
        skip: int = 0, 
        limit: int = 10,
        is_active: Optional[bool] = None
    ) -> UserListResponse:
        """获取用户列表，支持分页"""
        users = db.query(UserDB)
        
        # 过滤激活状态
        if is_active is not None:
            users = users.filter(UserDB.is_active == is_active)
        
        # 获取总数
        total = users.count()

        # 分页
        users_paginated = users.offset(skip).limit(limit).all()

        # 转换为响应模型（不包含密码）
        user_responses = [cls._db_to_response(user) for user in users_paginated]
        
        return UserListResponse(
            users=user_responses,
            total=total,
            page=(skip // limit) + 1 if limit > 0 else 1,
            size=limit
        )
    
    @classmethod
    async def update_user(cls, user_id: str, db: Session, user_data: UserUpdate) -> Optional[UserResponse]:
        """更新用户"""
        user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user:
            return None
        
        # 更新字段
        update_data = user_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == 'password':
                # 特殊处理密码更新
                setattr(user, 'hashed_password', PasswordManager.get_password_hash(value))
            else:
                setattr(user, field, value)

        user.updated_at = cls._get_current_time()
        
        # 更新存储
        db.commit()
        db.refresh(user)

        return cls._db_to_response(user)
    
    @classmethod
    async def pseudo_delete_user(cls, user_id: str, db: Session) -> bool:
        """软删除用户"""
        user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if user:
            user.is_active = False
            db.commit()
            db.refresh(user)
            return True
        return False
    
    @classmethod
    async def delete_user(cls, user_id: str, db: Session) -> bool:
        """删除用户"""
        user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if user:
            db.delete(user)
            db.commit()
            return True
        return False
    
    @staticmethod
    def _db_to_response(db_user: UserDB) -> UserResponse:
        """将数据库模型转换为响应模型"""
        return UserResponse(
            id=db_user.id,
            username=db_user.username,
            email=db_user.email,
            full_name=db_user.full_name,
            is_active=db_user.is_active,
            role=db_user.role,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at
        )

    @classmethod
    async def init_sample_data(cls, db: Session):
        """初始化示例数据"""
        sample_users = [
            UserCreate(
                username="admin",
                email="admin@example.com",
                full_name="系统管理员",
                password="admin123",
                role="admin"
            ),
            UserCreate(
                username="user1",
                email="user1@example.com",
                full_name="普通用户1",
                password="user123",
                role="user"
            ),
            UserCreate(
                username="user2",
                email="user2@example.com",
                full_name="普通用户2",
                password="user123",
                role="user"
            )
        ]
        
        for user_data in sample_users:
            # 检查用户是否已存在
            existing_user = db.query(UserDB).filter(
                (UserDB.username == user_data.username) | 
                (UserDB.email == user_data.email)
            ).first()
            
            if not existing_user:
                await cls.create_user(db, user_data)