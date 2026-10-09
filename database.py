from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings


# 根据数据库类型决定引擎参数
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite 不支持多线程访问同一连接，需要设置 check_same_thread=False
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL、MySQL 等其他数据库不需要此参数
    engine = create_engine(settings.DATABASE_URL)


# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM 模型基类，所有模型都要继承它
Base = declarative_base()


def get_db():
    """FastAPI 依赖函数，提供数据库会话并在请求结束后自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
