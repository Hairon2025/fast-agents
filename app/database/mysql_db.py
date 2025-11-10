from sqlalchemy import create_engine
from app.config import settings
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,      # 3600秒后回收连接，防止数据库连接超时
    echo=settings.DEBUG     # 在调试模式下输出SQL语句
)

# 创建数据库会话工厂
SessionLocal = sessionmaker(
    autocommit=False,   # 不自动提交，需要手动调用commit()
    autoflush=False,    # 不自动flush，手动控制何时同步到数据库
    bind=engine         # 绑定到上面创建的引擎
)

Base = declarative_base()

def get_db():
    """数据库会话生成器"""
    db = SessionLocal()  # 创建新的数据库会话
    try:
        yield db    # 使用yield生成器返回会话，将会话提供给请求使用
    finally:
        db.close()  # 请求结束后关闭会话，释放连接