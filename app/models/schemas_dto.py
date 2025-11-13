from pydantic import BaseModel, Field
from datetime import datetime


class HealthResponse(BaseModel):
    status: str = Field(..., description="服务状态")
    timestamp: datetime = Field(..., description="检查时间")
    version: str = Field(..., description="API版本")