from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
# from app.config import settings
from app.models.user import UserCreate, UserUpdate, UserInDB, UserResponse, UserListResponse
import hashlib

class UserService:
    """用户服务类，处理用户相关操作"""
    
     # 模拟数据存储（后续替换为真实数据库）
    _users_db: Dict[str, UserInDB] = {}

    @classmethod
    def _generate_user_id(cls) -> str:
        """生成唯一用户ID"""
        return str(uuid.uuid4())

    @classmethod
    def _get_current_time(cls) -> datetime:
        """获取当前时间"""
        return datetime.now()
    
    @classmethod
    def _hash_password(cls, password: str) -> str:
        """密码哈希函数（实际应用中应该使用更安全的如bcrypt）"""
        # 这里使用简单的哈希，实际生产环境应该使用 bcrypt 或类似库
        salt = "static_salt"  # 实际应用中应该使用随机盐
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    @classmethod
    def _verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return cls._hash_password(plain_password) == hashed_password

    @classmethod
    async def create_user(cls, user_data: UserCreate) -> UserResponse:
        """创建新用户"""
        user_id = cls._generate_user_id()
        current_time = cls._get_current_time()

        # 检查用户名是否已存在
        for existing_user in cls._users_db.values():
            if existing_user.username == user_data.username:
                raise ValueError("用户名已存在")
            if existing_user.email == user_data.email:
                raise ValueError("邮箱已存在")
        
        # 哈希密码
        hashed_password = cls._hash_password(user_data.password)

        user_in_db = UserInDB(
            id=user_id,
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            is_active=user_data.is_active,
            role=user_data.role,
            hashed_password=hashed_password,  # 存储哈希后的密码
            created_at=current_time,
            updated_at=current_time
        )
        
        # 存储用户信息
        cls._users_db[user_id] = user_in_db

        return UserResponse(**user_in_db.model_dump())

    @classmethod
    async def get_user_by_id(cls, user_id: str) -> Optional[UserResponse]:
        """根据ID获取用户"""
        user = cls._users_db.get(user_id)
        if user:
            return UserResponse(**user.model_dump())
        return None
    
    @classmethod
    async def get_user_by_username(cls, username: str) -> Optional[UserResponse]:
        """根据用户名获取用户（内部使用，返回完整用户信息）"""
        for user in cls._users_db.values():
            if user.username == username:
                return user
        return None
    
    @classmethod
    async def authenticate_user(cls, username: str, password: str) -> Optional[UserResponse]:
        """用户认证"""
        user = await cls.get_user_by_username(username)
        if not user:
            return None
        if not cls._verify_password(password, user.hashed_password):
            return None
        return UserResponse(**user.model_dump())
    
    @classmethod
    async def get_users(
        cls, 
        skip: int = 0, 
        limit: int = 10,
        is_active: Optional[bool] = None
    ) -> UserListResponse:
        """获取用户列表，支持分页"""
        users = list(cls._users_db.values())
        
        # 过滤激活状态
        if is_active is not None:
            users = [user for user in users if user.is_active == is_active]
        
        total = len(users)
        users_paginated = users[skip: skip + limit]
        
        # 转换为响应模型（不包含密码）
        user_responses = [UserResponse(**user.model_dump()) for user in users_paginated]
        
        return UserListResponse(
            users=user_responses,
            total=total,
            page=(skip // limit) + 1 if limit > 0 else 1,
            size=limit
        )
    
    @classmethod
    async def update_user(cls, user_id: str, user_data: UserUpdate) -> Optional[UserResponse]:
        """更新用户"""
        user = cls._users_db.get(user_id)
        if not user:
            return None
        
        # 更新字段
        update_data = user_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == 'password':
                # 特殊处理密码更新
                setattr(user, 'hashed_password', cls._hash_password(value))
            else:
                setattr(user, field, value)
        
        user.updated_at = cls._get_current_time()
        
        # 更新存储
        cls._users_db[user_id] = user
        
        return UserResponse(**user.model_dump())
    
    @classmethod
    async def delete_user(cls, user_id: str) -> bool:
        """删除用户"""
        if user_id in cls._users_db:
            del cls._users_db[user_id]
            return True
        return False

    @classmethod
    async def init_sample_data(cls):
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
            await cls.create_user(user_data)