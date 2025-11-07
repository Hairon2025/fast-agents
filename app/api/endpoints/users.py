from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional
from app.models.user import UserCreate, UserUpdate, UserResponse, UserListResponse
from app.services.user_service import UserService

router = APIRouter()

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate):
    """创建新用户"""
    try:
        user = await UserService.create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
@router.get("/", response_model=UserListResponse)
async def get_users(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="每页记录数"),
    is_active: Optional[bool] = Query(None, description="是否激活")
):
    """获取用户列表"""
    return await UserService.get_users(
        skip=skip,
        limit=limit,
        is_active=is_active
    )

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """根据ID获取用户"""
    user = await UserService.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, user_data: UserUpdate):
    """更新用户信息"""
    user = await UserService.update_user(user_id, user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str):
    """删除用户"""
    success = await UserService.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return None

# 认证端点
@router.post("/auth/login")
async def login(username: str, password: str):
    """用户登录"""
    user = await UserService.authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    return {
        "message": "登录成功",
        "user": user
    }

# 初始化示例数据
@router.post("/init/sample-data", status_code=status.HTTP_201_CREATED)
async def init_sample_data():
    """初始化示例用户数据（仅用于测试）"""
    await UserService.init_sample_data()
    return {"message": "示例数据初始化成功"}