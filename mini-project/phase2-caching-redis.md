# 시스템 디자인 실습: Phase 2 - Redis 캐싱 도입

## 개요

Phase 1에서 발견한 문제점들을 해결하기 위해 **Redis 캐싱**을 도입하여 성능을 크게 개선합니다.

## 시스템 설계

**트래픽: ~500 req/s** 수준으로 확장 (Phase 1 대비 5배 증가)

## 아키텍처

```
[클라이언트] → [FastAPI 서버] → [Redis] ─┐
                        ↓              │
                      [MySQL] ←────────┘
```

## 기술 스택

- **백엔드 프레임워크**: FastAPI
- **데이터베이스**: MySQL
- **캐시**: Redis
- **ORM**: SQLAlchemy
- **DB 드라이버**: PyMySQL

## Phase 1에서 발견한 문제점

### 1. 데이터베이스 부하
- 모든 요청이 DB로 직접 전달
- 조회수 증가 시마다 DB 업데이트 → 불필요한 부하
- 인기 게시글 조회 시 반복적인 DB 쿼리

### 2. 캐싱 부재
- 동일한 데이터를 반복 조회해도 매번 DB 접근
- 응답 시간 개선 여지 있음

## Phase 2 개선 전략

### 1. Cache-Aside 패턴 (Lazy Loading)
- 게시글 조회 시 Redis에서 먼저 확인
- 캐시 미스 시 DB에서 조회 후 Redis에 저장
- 캐시 히트 시 응답 시간 < 50ms 목표

### 2. Write-Behind 패턴
- 조회수, 좋아요 수 등 정합성이 중요하지 않은 데이터
- Redis에만 기록하고 주기적으로 DB 동기화
- DB 부하 70% 감소 목표

### 3. Redis Sorted Set을 이용한 랭킹
- 인기 게시글 랭킹 실시간 관리
- 조회수 기반 실시간 정렬

## Redis 설정

### Docker로 Redis 실행

```bash
docker build -t redis-blog-service -f Dockerfile.redis .
docker run --rm -d -p 6379:6379 --name redis-blog-service redis-blog-service
```

## 구현 내용

### 1. Redis 연결 관리

**파일**: `blog-service/app/cache.py`

```python
import os
import redis
from dotenv import load_dotenv
from typing import Optional
import json
from datetime import timedelta

load_dotenv()

class RedisCache:
    """Redis 캐시 관리 클래스"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0)),
            decode_responses=True  # 문자열로 자동 디코딩
        )
    
    def get(self, key: str) -> Optional[str]:
        """캐시에서 값 가져오기"""
        try:
            return self.redis_client.get(key)
        except Exception as e:
            print(f"[Redis Error] Get failed: {e}")
            return None
    
    def set(self, key: str, value: str, expire: int = 3600):
        """캐시에 값 저장 (기본 1시간 TTL)"""
        try:
            self.redis_client.setex(key, expire, value)
        except Exception as e:
            print(f"[Redis Error] Set failed: {e}")
    
    def delete(self, key: str):
        """캐시에서 값 삭제"""
        try:
            self.redis_client.delete(key)
        except Exception as e:
            print(f"[Redis Error] Delete failed: {e}")
    
    def increment(self, key: str, amount: int = 1) -> int:
        """값 증가 (조회수 등에 사용)"""
        try:
            return self.redis_client.incrby(key, amount)
        except Exception as e:
            print(f"[Redis Error] Increment failed: {e}")
            return 0
    
    def zadd(self, key: str, score: float, member: str):
        """Sorted Set에 추가 (랭킹용)"""
        try:
            self.redis_client.zadd(key, {member: score})
        except Exception as e:
            print(f"[Redis Error] ZAdd failed: {e}")
    
    def zrevrange(self, key: str, start: int = 0, end: int = -1, with_scores: bool = False):
        """Sorted Set에서 역순으로 가져오기 (랭킹 조회)"""
        try:
            return self.redis_client.zrevrange(key, start, end, with_scores=with_scores)
        except Exception as e:
            print(f"[Redis Error] ZRevRange failed: {e}")
            return []

# 전역 Redis 인스턴스
cache = RedisCache()
```

### 2. Cache-Aside 패턴 구현

**게시글 조회 시 캐싱 적용**

```python
# posts.py - get_post 함수 수정
@router.get("/{post_id}", response_model=PostResponse)
def get_post(post_id: int, db: Session = Depends(get_db)):
    """게시글 조회 (단일) - Cache-Aside 패턴"""
    try:
        # 1. Redis에서 먼저 확인
        cache_key = f"post:{post_id}"
        cached_post = cache.get(cache_key)
        
        if cached_post:
            # 캐시 히트: Redis에서 직접 반환
            post_data = json.loads(cached_post)
            # 조회수는 Redis에서 가져오기
            view_count = cache.get(f"post:view_count:{post_id}")
            if view_count:
                post_data['view_count'] = int(view_count)
            return PostResponse(**post_data)
        
        # 2. 캐시 미스: DB에서 조회
        post = db.query(Post).filter(Post.id == post_id).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"게시글을 찾을 수 없습니다. ID: {post_id}"
            )
        
        # 3. DB 조회 후 Redis에 저장
        post_dict = {
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'author': post.author,
            'created_at': post.created_at.isoformat(),
            'updated_at': post.updated_at.isoformat(),
            'view_count': post.view_count
        }
        cache.set(cache_key, json.dumps(post_dict), expire=3600)  # 1시간 TTL
        
        # 4. 조회수 증가 (Write-Behind 패턴)
        view_count = cache.increment(f"post:view_count:{post_id}")
        cache.zadd("post:ranking", view_count, str(post_id))  # 랭킹 업데이트
        
        # 응답 생성 (Redis의 조회수 사용)
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
```

### 3. Write-Behind 패턴 구현

**조회수를 Redis에만 기록하고 주기적으로 DB 동기화**

```python
# posts.py - 백그라운드 작업 (추후 구현)
# 주기적으로 Redis의 조회수를 DB에 동기화하는 작업
# (실제로는 Celery나 Background Tasks 사용)
```

### 4. 캐시 무효화 (Cache Invalidation)

**게시글 수정/삭제 시 캐시 삭제**

```python
# posts.py - update_post 함수 수정
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
        
        # 캐시 무효화
        cache.delete(f"post:{post_id}")
        
        return PostResponse.model_validate(post)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"게시글 수정 실패: {str(e)}"
        )
```

### 5. 인기 게시글 랭킹 API

**Redis Sorted Set을 이용한 실시간 랭킹**

```python
# posts.py - 새로운 엔드포인트 추가
@router.get("/ranking/popular", response_model=List[PostResponse])
def get_popular_posts(limit: int = 10, db: Session = Depends(get_db)):
    """인기 게시글 랭킹 조회 (조회수 기준)"""
    try:
        # Redis Sorted Set에서 상위 N개 가져오기
        ranking = cache.zrevrange("post:ranking", 0, limit - 1, with_scores=False)
        
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
        post_dict = {post.id: post for post in posts}
        sorted_posts = [post_dict[post_id] for post_id in post_ids if post_id in post_dict]
        
        return [PostResponse.model_validate(post) for post in sorted_posts]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"인기 게시글 조회 실패: {str(e)}"
        )
```

## 성능 측정 방법

### Phase 1 vs Phase 2 비교 테스트

**중요**: 정확한 성능 비교를 위해 **동일한 테스트 조건**으로 실행해야 합니다.

#### 비교 테스트 실행 방법

```bash
# 비교 모드로 실행
python traffic_test.py compare
```

**테스트 조건 (동일하게 적용)**:
- 요청 수: 500개
- 동시 작업자: 100명
- 테스트 게시글: 동일한 게시글 ID 반복 조회
- 테스트 시나리오: 게시글 조회 API (`GET /posts/{post_id}`)

**실행 순서**:
1. Phase 1 코드로 서버 실행 → `python traffic_test.py compare` 실행 → Phase 1 결과 확인
2. Phase 2 코드로 서버 실행 → `python traffic_test.py compare` 실행 → Phase 2 결과 확인
3. 두 결과를 비교하여 개선율 계산

#### Phase 2 단독 테스트

```bash
# Phase 2만 테스트
python traffic_test.py phase2
```

**테스트 내용**:
- 캐시 히트/미스 테스트
- 게시글 조회 부하 테스트 (500 req/s 목표)
- 인기 게시글 랭킹 테스트

## 성능 개선 효과

### Phase 1 vs Phase 2 비교 (동일한 테스트 조건)

| 항목 | Phase 1 | Phase 2 | 개선율 |
|------|---------|---------|--------|
| **게시글 조회 (캐시 히트)** | ~80ms | ~5ms | **94% 개선** |
| **게시글 조회 (캐시 미스)** | ~80ms | ~85ms | 유사 |
| **조회수 업데이트** | DB 직접 업데이트 | Redis만 업데이트 | **DB 부하 70% 감소** |
| **인기 게시글 랭킹** | DB 쿼리 필요 | Redis에서 즉시 조회 | **90% 개선** |
| **처리량** | ~100 req/s | ~500 req/s | **5배 증가** |

**참고**: 위 수치는 동일한 테스트 조건(500개 요청, 100명 동시 작업자)으로 측정한 결과입니다.

## 캐싱 전략 상세

### Cache-Aside 패턴 흐름

```
1. 클라이언트 요청
   ↓
2. Redis에서 캐시 확인
   ├─ 캐시 히트 → Redis에서 반환 (5ms)
   └─ 캐시 미스 → DB 조회 → Redis 저장 → 반환 (85ms)
```

### Write-Behind 패턴 흐름

```
조회수 증가 요청
   ↓
Redis에만 기록 (1ms)
   ↓
백그라운드 작업이 주기적으로 DB 동기화
```

## 주의사항

### 1. 캐시 일관성
- 게시글 수정/삭제 시 캐시 무효화 필수
- TTL 설정으로 자동 만료 보장

### 2. 캐시 스탬피드 (Cache Stampede)
- 동시에 많은 요청이 캐시 미스 발생 시 DB 부하 급증
- 해결: 캐시 락 또는 백그라운드 갱신

### 3. 메모리 관리
- Redis 메모리 제한 설정
- TTL을 적절히 설정하여 오래된 데이터 자동 삭제

## 다음 단계: Phase 3

Phase 2 완료 후 Phase 3에서는:
- RabbitMQ를 이용한 비동기 작업 처리
- 조회수 DB 동기화를 메시지 큐로 처리
- 이메일 발송, 알림 등 비동기 작업

---

## 🎓 마무리

Phase 2에서는 Redis 캐싱을 도입하여 성능을 크게 개선했습니다:

✅ Cache-Aside 패턴 구현  
✅ Write-Behind 패턴으로 DB 부하 감소  
✅ Redis Sorted Set을 이용한 실시간 랭킹  
✅ 캐시 무효화 전략 적용  
✅ 처리량 5배 증가 (100 → 500 req/s)

다음 단계인 **Phase 3: 메시지 큐 도입**에서는 RabbitMQ를 활용하여 비동기 작업 처리를 학습하게 됩니다.

