from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database.mysql_db import engine, Base
from app.core.router_registry import auto_register_routers
import logging
import uvicorn

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def create_application() -> FastAPI:
    """创建FastAPI应用"""

    # 自动创建表（仅在开发环境）
    if settings.DEBUG:
        try:
            Base.metadata.create_all(bind=engine)
            print("数据库表创建/检查完成")
            logging.info("数据库表创建/检查完成")
        except Exception as e:
            logging.warning(f"数据库表创建失败: {e}")

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
    
    # 自动注册路由
    auto_register_routers(application)
    
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