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
    
    # 安全配置
    CORS_ORIGINS: list = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()