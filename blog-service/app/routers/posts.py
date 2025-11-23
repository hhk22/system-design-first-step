from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from sqlalchemy.orm import Session
from app.models import PostCreate, PostUpdate, PostResponse, Post
from app.database import get_db

router = APIRouter(prefix="/posts")

@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(post: PostCreate, db: Session = Depends(get_db)):
    """게시글 작성"""
    try:
        # SQLAlchemy 모델 인스턴스 생성
        db_post = Post(
            title=post.title,
            content=post.content,
            author=post.author
        )
        
        # 데이터베이스에 추가
        db.add(db_post)
        db.commit()
        db.refresh(db_post)  # 생성된 ID 등 최신 정보 가져오기
        
        # Pydantic 모델로 변환하여 반환 (from_attributes = True 덕분에 가능)
        return PostResponse.model_validate(db_post)

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"게시글 생성 실패: {str(e)}"
        )

@router.get("", response_model=List[PostResponse])
def get_posts(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """게시글 목록 조회"""
    try:
        posts = db.query(Post).order_by(Post.created_at.desc()).offset(skip).limit(limit).all()
        
        return [PostResponse.model_validate(post) for post in posts]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"게시글 목록 조회 실패: {str(e)}"
        )

@router.get("/{post_id}", response_model=PostResponse)
def get_post(post_id: int, db: Session = Depends(get_db)):
    """게시글 조회 (단일)"""
    try:
        # 게시글 조회
        post = db.query(Post).filter(Post.id == post_id).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"게시글을 찾을 수 없습니다. ID: {post_id}"
            )
        
        # 조회수 증가
        post.view_count += 1
        db.commit()
        db.refresh(post)
        
        return PostResponse.model_validate(post)
    except HTTPException:
        raise
    except Exception as e:
        print(f'[ERROR] 게시글 조회 실패: {type(e).__name__}: {str(e)}')
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"게시글 조회 실패: {str(e)}"
        )

@router.put("/{post_id}", response_model=PostResponse)
def update_post(post_id: int, post_update: PostUpdate, db: Session = Depends(get_db)):
    """게시글 수정"""
    try:
        # 기존 게시글 조회
        post = db.query(Post).filter(Post.id == post_id).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"게시글을 찾을 수 없습니다. ID: {post_id}"
            )
        
        # 업데이트할 필드만 수정
        if post_update.title is not None:
            post.title = post_update.title
        if post_update.content is not None:
            post.content = post_update.content
        
        db.commit()
        db.refresh(post)
        
        return PostResponse.model_validate(post)

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"게시글 수정 실패: {str(e)}"
        )

@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: Session = Depends(get_db)):
    """게시글 삭제"""
    try:
        # 기존 게시글 조회
        post = db.query(Post).filter(Post.id == post_id).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"게시글을 찾을 수 없습니다. ID: {post_id}"
            )
        
        # 게시글 삭제
        db.delete(post)
        db.commit()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"게시글 삭제 실패: {str(e)}"
        )
