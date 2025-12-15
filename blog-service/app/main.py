from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.routers import posts
from app.database import engine, read_engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: 서버 시작 시 실행
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        with read_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ 데이터베이스 연결 성공")
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        # raise
    
    yield
    
    # Shutdown: 서버 종료 시 실행
    engine.dispose()
    print("✅ 데이터베이스 연결 종료")

app = FastAPI(
    title="Blog Service API",
    description="간단한 블로그/게시판 서비스 - Phase 1",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정 (개발용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(posts.router)

@app.get("/")
def root():
    return {
        "message": "Blog Service API",
        "version": "1.0.0",
        "phase": "Phase 1",
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    """헬스 체크 엔드포인트"""
    try:
        # 데이터베이스 연결 확인
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }

