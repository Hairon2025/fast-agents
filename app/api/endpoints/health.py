from fastapi import APIRouter
from app.models.schemas import HealthResponse
from datetime import datetime
from app.config import settings

router = APIRouter()

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="健康检查",
    description="检查API服务是否正常运行"
)
async def health_check():
    """健康检查端点"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version=settings.APP_VERSION
    )