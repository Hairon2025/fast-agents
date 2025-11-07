from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import users, health
from app.config import settings
import logging
import uvicorn

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def create_application() -> FastAPI:
    """创建FastAPI应用"""
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # 添加CORS中间件
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 包含路由
    application.include_router(
        health.router,
        prefix=settings.API_PREFIX,
        tags=["health"]
    )
    
    application.include_router(
        users.router,
        prefix=settings.API_PREFIX + "/users",
        tags=["users"]
    )
    
    # 根路径
    @application.get("/")
    async def root():
        return {
            "message": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "running"
        }
    
    return application

app = create_application()

if __name__ == "__main__":

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )