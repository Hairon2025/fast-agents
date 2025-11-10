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
    
    # # Agent配置
    # AGENT_MODEL_NAME: str = "gpt-3.5-turbo"
    # AGENT_TEMPERATURE: float = 0.7
    # AGENT_MAX_TOKENS: int = 1000
    # OPENAI_API_KEY: Optional[str] = None
    
    # # 其他LLM配置（可选）
    # ANTHROPIC_API_KEY: Optional[str] = None
    # GROQ_API_KEY: Optional[str] = None

    # 数据库配置
    # DATABASE_HOST: str = "localhost"
    DATABASE_HOST: str = "YOUR_DB_HOST"
    DATABASE_PORT: int = 3306
    DATABASE_USER: str = "YOUR_DB_USER"
    DATABASE_PASSWORD: str = "YOUR_DB_PASSWORD"
    DATABASE_NAME: str = "YOUR_DB_NAME"

    # 数据库URL（可选，如果设置了会覆盖上面的配置）
    DATABASE_URL: Optional[str] = None
    
    # 安全配置
    CORS_ORIGINS: list = ["*"]

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