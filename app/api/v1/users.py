from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import UserCreate, UserUpdate, UserResponse, UserListResponse, LoginRequest, Token
from app.services.user_service import UserService
from app.database.mysql_db import get_db
from app.tools.dependencies import get_current_user, get_current_active_user, get_current_admin_user


router = APIRouter()

# ==================== 公开端点（不需要认证） ====================

@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """用户注册（公开）"""
    try:
        user = await UserService.create_user(db, user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/auth/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """用户登录（公开）"""
    result = await UserService.login_user(db, login_data)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    return result

@router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: UserResponse = Depends(get_current_user)
):
    """获取当前用户信息（需要登录）"""
    return current_user

# ==================== 受保护端点（需要认证） ====================
 
@router.get("/", response_model=UserListResponse)
async def get_users(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="每页记录数"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)  # 需要登录
):
    """获取用户列表"""
    return await UserService.get_users(
        db=db,
        skip=skip,
        limit=limit,
        is_active=is_active
    )

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str, 
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)  # 需要登录
):
    """根据ID获取用户"""
    user = await UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str, 
    user_data: UserUpdate, 
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)  # 需要登录
):
    """更新用户信息（需要登录）"""
    # 普通用户只能更新自己的信息，管理员可以更新任何用户
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能更新自己的用户信息"
        )
    
    user = await UserService.update_user(user_id, db, user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user

# ==================== 管理员专用端点 ====================

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str, 
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_admin_user)  # 需要管理员权限
):
    """删除用户（需要管理员权限）"""
    success = await UserService.delete_user(user_id, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return None

@router.patch("/{user_id}/deactivate", status_code=status.HTTP_200_OK)
async def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_admin_user)  # 需要管理员权限
):
    """停用用户（软删除，需要管理员权限）"""
    success = await UserService.pseudo_delete_user(user_id, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return {"message": "用户已停用"}

@router.patch("/{user_id}/activate", status_code=status.HTTP_200_OK)
async def activate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_admin_user)  # 需要管理员权限
):
    """激活用户（需要管理员权限）"""
    user = await UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 更新用户为激活状态
    update_data = UserUpdate(is_active=True)
    await UserService.update_user(user_id, db, update_data)
    
    return {"message": "用户已激活"}

# 初始化示例数据
@router.post("/init/sample-data", status_code=status.HTTP_201_CREATED)
async def init_sample_data(db: Session = Depends(get_db)):
    """初始化示例用户数据（仅用于测试）"""
    await UserService.init_sample_data(db)
    return {"message": "示例数据初始化成功"}