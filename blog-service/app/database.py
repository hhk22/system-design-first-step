import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.models import Base

load_dotenv()

# 데이터베이스 URL 생성
DATABASE_URL = f"mysql+pymysql://{os.getenv('DB_USER', 'test_user')}:{os.getenv('DB_PASSWORD', '1234')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', 3306)}/{os.getenv('DB_NAME', 'blog_db')}?charset=utf8mb4"

# SQLAlchemy 엔진 생성
engine = create_engine(
    DATABASE_URL,
    echo=False  # True로 설정하면 SQL 쿼리 로그 출력
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 데이터베이스 세션 의존성 (FastAPI에서 사용)
def get_db() -> Generator[Session, None, None]:
    """데이터베이스 세션 생성 및 관리"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 기존 Database 클래스 (하위 호환성을 위해 유지)
class Database:
    """레거시 코드 호환성을 위한 래퍼 클래스"""
    def __init__(self):
        self.engine = engine
    
    def connect(self):
        """연결 확인용 (실제로는 엔진이 연결 관리)"""
        return self.engine
    
    def get_connection(self):
        """레거시 호환성"""
        return self.engine
    
    def close(self):
        """레거시 호환성 (실제로는 세션 단위로 관리)"""
        pass

# 전역 데이터베이스 인스턴스 (레거시 호환성)
db = Database()

