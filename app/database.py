from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# SQLite 数据库文件路径
SQLALCHEMY_DATABASE_URL = "sqlite:///./blog.db"

# 创建引擎，connect_args 是 SQLite 必须的（支持多线程检查）
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 创建 Session 工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类（所有模型都继承它）
class Base(DeclarativeBase):
    pass

# 获取数据库会话的依赖项（FastAPI 的 Depends 会用这个）
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()