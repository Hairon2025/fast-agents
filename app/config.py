import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """应用配置"""
    # 应用配置
    APP_NAME: str = "Agent API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API配置
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"

    # RAG 相关配置
    TONYIQWEN_API_KEY: Optional[str] = "YOUR_TONYIQWEN_API_KEY"
    OPENAI_BASE_URL: Optional[str] = "YOUR_OPENAI_BASE_URL"  # 如果用第三方代理
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_MODEL_KEY: Optional[str] = "YOUR_EMBEDDING_MODEL_KEY"
    LLM_MODEL: str = "YOUR_LLM_MODEL"

    # 向量数据库配置
    VECTOR_STORE_PATH: str = "./data/vector_store"
    PDF_STORAGE_PATH: str = "./data/pdfs"
    
    # RAG 参数
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    SIMILARITY_TOP_K: int = 5
    
    # # Agent配置
    # AGENT_MODEL_NAME: str = "gpt-3.5-turbo"
    # AGENT_TEMPERATURE: float = 0.7
    # AGENT_MAX_TOKENS: int = 1000
    # OPENAI_API_KEY: Optional[str] = None
    
    # # 其他LLM配置（可选）
    # ANTHROPIC_API_KEY: Optional[str] = None
    # GROQ_API_KEY: Optional[str] = None

    # 数据库配置
    DATABASE_HOST: str = "localhost"
    DATABASE_HOST: str = "YOUR_DB_HOST"
    DATABASE_PORT: int = 3306
    DATABASE_USER: str = "YOUR_DB_USER"
    DATABASE_PASSWORD: str = "YOUR_DB_PASSWORD"
    DATABASE_NAME: str = "YOUR_DB_NAME"

    # 数据库URL（可选，如果设置了会覆盖上面的配置）
    DATABASE_URL: Optional[str] = None
    
    # 安全配置
    CORS_ORIGINS: list = ["*"]

    # JWT配置
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"  # 生产环境要修改
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # token过期时间（分钟）

    @property
    def database_url(self) -> str:
        """获取数据库连接URL"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"mysql+pymysql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}?charset=utf8mb4"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()