import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, Optional
# from app.models import Base

load_dotenv()

def _build_db_url(
    user: str,
    password: str,
    host: str,
    port: int,
    name: str,
) -> str:
    """공통 MySQL 접속 URL 생성"""
    return (
        f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"
        "?charset=utf8mb4"
    )


def _load_db_config(prefix: Optional[str] = None) -> dict:
    """환경 변수에서 DB 접속 정보를 읽어온다."""
    normalized_prefix = (prefix or "").upper()
    if normalized_prefix and not normalized_prefix.endswith("_"):
        normalized_prefix = f"{normalized_prefix}_"

    def _get(key: str, fallback: Optional[str] = None) -> str:
        env_key = f"{normalized_prefix}{key}"
        return os.getenv(env_key, fallback)

    return {
        "user": _get("DB_USER", os.getenv("DB_USER", "test_user")),
        "password": _get("DB_PASSWORD", os.getenv("DB_PASSWORD", "1234")),
        "host": _get("DB_HOST", os.getenv("DB_HOST", "localhost")),
        "port": int(_get("DB_PORT", os.getenv("DB_PORT", 3306))),
        "name": _get("DB_NAME", os.getenv("DB_NAME", "blog_db")),
    }


primary_config = _load_db_config()
read_config = _load_db_config("READ")

print("Primary Config: ", primary_config)
print("Read Config: ", read_config)

# 데이터베이스 URL 생성
DATABASE_URL = _build_db_url(**primary_config)
READ_DATABASE_URL = _build_db_url(**read_config)

# SQLAlchemy 엔진 생성
engine = create_engine(
    DATABASE_URL,
    echo=False  # True로 설정하면 SQL 쿼리 로그 출력
)
read_engine = create_engine(
    READ_DATABASE_URL,
    echo=False
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
SessionLocalRead = sessionmaker(autocommit=False, autoflush=False, bind=read_engine)

# 데이터베이스 세션 의존성 (FastAPI에서 사용)
def get_db() -> Generator[Session, None, None]:
    """데이터베이스 세션 생성 및 관리"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_read_db() -> Generator[Session, None, None]:
    """읽기 전용 데이터베이스 세션 생성"""
    db = SessionLocalRead()
    try:
        yield db
    finally:
        db.close()


# 기존 Database 클래스 (하위 호환성을 위해 유지)
class Database:
    """레거시 코드 호환성을 위한 래퍼 클래스"""
    def __init__(self):
        self.engine = engine
        self.read_engine = read_engine
    
    def connect(self):
        """연결 확인용 (실제로는 엔진이 연결 관리)"""
        return self.engine
    
    def get_connection(self):
        """레거시 호환성"""
        return self.engine
    
    def close(self):
        """레거시 호환성 (실제로는 세션 단위로 관리)"""
        pass
    
    def get_read_connection(self):
        """읽기 전용 엔진 접근"""
        return self.read_engine

# 전역 데이터베이스 인스턴스 (레거시 호환성)
db = Database()

