from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database.mysql_db import get_db
from app.services.user_service import UserService

# HTTPBearer 是一个安全方案，自动从请求头中提取 Bearer token
# 它会检查 Authorization 头，格式应该是: Bearer <token>
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    获取当前用户依赖项

    这个依赖项会在每个需要认证的路由中被调用，它的作用是：
    1. 从请求头中提取 token
    2. 验证 token 的有效性
    3. 根据 token 中的用户信息从数据库获取用户
    4. 如果验证失败，自动返回 401 错误

    参数:
        credentials: 包含 token 的认证凭证
        db: 数据库会话
        
    返回:
        User: 当前用户对象
        
    异常:
        HTTPException: 如果 token 无效或用户不存在
    """
    token = credentials.credentials
    user = await UserService.get_current_user(db, token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的token或用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def get_current_active_user(current_user = Depends(get_current_user)):
    """
    获取当前活跃用户
    
    这个依赖项在 get_current_user 基础上增加了活跃状态检查
    用于确保用户账户是激活状态

    参数:
        current_user: 通过 get_current_user 获取的当前用户对象
    
    返回:
        User: 当前活跃用户对象

    异常:
        HTTPException: 如果用户未激活
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户未激活")
    return current_user

async def get_current_admin_user(current_user = Depends(get_current_active_user)):
    """
    获取当前管理员用户依赖项
    
    这个依赖项在 get_current_active_user 基础上增加了管理员权限检查
    用于确保当前用户具有管理员权限

    参数:
        current_user: 通过 get_current_active_user 获取的当前活跃用户对象
    
    返回:
        User: 当前管理员用户对象

    异常:
        HTTPException: 如果用户没有管理员权限
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user