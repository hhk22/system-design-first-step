from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, Index
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func

# SQLAlchemy Base 클래스 (2.0 스타일)
class Base(DeclarativeBase):
    pass

# SQLAlchemy 모델 (데이터베이스 테이블과 매핑)
class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        Index("idx_posts_created_at", "created_at"),
        Index("idx_posts_view_count", "view_count"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    author = Column(String(100), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    view_count = Column(Integer, default=0)

class PostCreate(BaseModel):
    title: str
    content: str
    author: str

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
  
class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    author: str
    created_at: datetime
    updated_at: datetime
    view_count: int
    
    class Config:
        from_attributes = True  # SQLAlchemy 모델에서 변환 가능하게 함

