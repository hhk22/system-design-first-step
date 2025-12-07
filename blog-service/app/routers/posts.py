from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from sqlalchemy.orm import Session
from app.models import PostCreate, PostUpdate, PostResponse, Post
from app.database import get_db
from app.cache import cache

import json

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
        # 1. First check cache data on Redis
        cache_key = f"post:{post_id}"
        cached_post = cache.get(cache_key)

        if cached_post:
            post_data = json.loads(cached_post)
            view_count = cache.increment(f"post:view_count:{post_id}")
            cache.zadd("post:ranking", view_count, str(post_id))
            if view_count:
                post_data['view_count'] = int(view_count)
            return PostResponse(**post_data)

        post: PostResponse = db.query(Post).filter(Post.id == post_id).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"게시글을 찾을 수 없습니다. ID: {post_id}"
            )
        
        post_dict = {
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "author": post.author,
            "created_at": post.created_at.isoformat(),
            "updated_at": post.updated_at.isoformat(),
            "view_count": post.view_count
        }
        cache.set(cache_key, json.dumps(post_dict), expire=3600)

        view_count = cache.increment(f"post:view_count:{post_id}")
        cache.zadd("post:ranking", view_count, str(post_id))

        post_dict['view_count'] = view_count
        return PostResponse(**post_dict)
        
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

        cache.delete(f"post:{post_id}")
        
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

@router.get("/ranking/popular", response_model=List[PostResponse])
def get_popular_posts(limit: int = 10, db: Session = Depends(get_db)):
    """인기 게시글 랭킹 조회 (조회수 기준)"""
    try:
        # Redis Sorted Set에서 상위 N개 가져오기
        ranking = cache.zrevrange("post:ranking", 0, limit - 1, with_scores=False)
        print(ranking)
        
        if not ranking:
            # 랭킹이 없으면 DB에서 조회수 기준으로 가져오기
            posts = db.query(Post)\
                .order_by(Post.view_count.desc())\
                .limit(limit)\
                .all()
            return [PostResponse.model_validate(post) for post in posts]
        
        # Redis에서 가져온 ID로 게시글 조회
        post_ids = [int(post_id) for post_id in ranking]
        posts = db.query(Post).filter(Post.id.in_(post_ids)).all()
        
        # ID 순서대로 정렬
        post_dict = {}
        for post in posts:
            post.view_count = cache.get(f"post:view_count:{post.id}")
            post_dict[post.id] = post
        sorted_posts = [post_dict[post_id] for post_id in post_ids if post_id in post_dict]
        
        return [PostResponse.model_validate(post) for post in sorted_posts]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"인기 게시글 조회 실패: {str(e)}"
        )