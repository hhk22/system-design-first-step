
# 시스템 디자인 실습: Phase 1 - 기본 블로그 서비스 구현

해당 시스템 설계에 대한 코드는 [깃헙코드](https://github.com/hhk22/system-design-first-step/tree/feature/phase1)에 있습니다.

## 시스템 설계

**트래픽: ~100 req/s** 수준에서 동작하는 기본적인 블로그/게시판 서비스를 구현

## 아키텍처

```
[클라이언트] → [FastAPI 서버] → [MySQL]
```

## 기술 스택

- **백엔드 프레임워크**: FastAPI
- **데이터베이스**: MySQL
- **ORM/DB 드라이버**: PyMySQL

### 데이터베이스 스키마

```sql
-- database.sql
CREATE TABLE IF NOT EXISTS posts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    author VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    view_count INT DEFAULT 0,
    INDEX idx_created_at (created_at),
    INDEX idx_author (author)
);
```

`Mysql` 전용 `Dockerfile`

```Dockerfile
FROM mysql:8.0

ENV MYSQL_DATABASE=blog_db
ENV MYSQL_USER=test_user
ENV MYSQL_PASSWORD=1234
ENV MYSQL_ROOT_PASSWORD=1234

COPY ./blog-service/database.sql /docker-entrypoint-initdb.d/init.sql

EXPOSE 3306
```

해당 `Dockerfile` 을 이용해 `MySQL` 실행하기

```bash
docker build -t mysql-blog-service .
docker run --rm -d -p 3306:3306 --name mysql-blog-service mysql-blog-service
```

### API 엔드포인트

**데이터베이스 구현코드**

```python
DATABASE_URL = f"mysql+pymysql://{os.getenv('DB_USER', 'test_user')}:{os.getenv('DB_PASSWORD', '1234')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', 3306)}/{os.getenv('DB_NAME', 'blog_db')}?charset=utf8mb4"

engine = create_engine(
    DATABASE_URL,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


```

**데이터 모델 코드**

```python
# 데이터베이스 테이블과 맵핑되는 SqlAlchemy Class
class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    author = Column(String(100), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    view_count = Column(Integer, default=0)

# Post 게시글 작성에 사용될 Pydantic Class
class PostCreate(BaseModel):
    title: str
    content: str
    author: str

# Post 게시글 수정에 사용될 Pydantic Class
class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

# Post 게시글 조회 후 응답결과와 맵핑될 Pydantic Class
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

```

#### 1. 게시글 작성

```http
POST /posts
{
  "title": "게시글 제목",
  "content": "게시글 내용",
  "author": "작성자"
}
```

**구현 코드**
```python
@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(post: PostCreate, db: Session = Depends(get_db)):
    try:
        db_post = Post(
            title=post.title,
            content=post.content,
            author=post.author
        )
        
        db.add(db_post)
        db.commit()
        db.refresh(db_post)
        
        return PostResponse.model_validate(db_post)

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"게시글 생성 실패: {str(e)}"
        )
```

#### 2. 게시글 목록 조회

```http
GET /posts?skip=0&limit=10
```

**구현 코드**
```python
@router.get("", response_model=List[PostResponse])
def get_posts(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    try:
        posts = db.query(Post).order_by(Post.created_at.desc()).offset(skip).limit(limit).all()
        
        return [PostResponse.model_validate(post) for post in posts]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"게시글 목록 조회 실패: {str(e)}"
        )
```

### 3. 게시글 조회 (단일)

```http
GET /posts/{post_id}
```

**구현 코드**
```python
@router.get("/{post_id}", response_model=PostResponse)
def get_post(post_id: int, db: Session = Depends(get_db)):
    try:
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
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"게시글 조회 실패: {str(e)}"
        )
```

#### 4. 게시글 수정

```http
PUT /posts/{post_id}
Content-Type: application/json

{
  "title": "수정된 제목",
  "content": "수정된 내용"
}
```

**구현 코드**
```python
@router.get("/{post_id}", response_model=PostResponse)
def get_post(post_id: int, db: Session = Depends(get_db)):
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"게시글을 찾을 수 없습니다. ID: {post_id}"
            )
        
        post.view_count += 1
        db.commit()
        db.refresh(post)
        
        return PostResponse.model_validate(post)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"게시글 조회 실패: {str(e)}"
        )
```

#### 5. 게시글 삭제
```http
DELETE /posts/{post_id}
```

**구현 코드**

```python
@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: Session = Depends(get_db)):
    try:
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
```

## 📊 성능 목표 및 측정

- **응답 시간**: < 200ms (평균)
- **동시 사용자**: ~100명
- **처리량**: ~100 req/s

### `Python` 으로 간단한 부하 테스트

```python
#traffic_test.py
import requests
import time
from concurrent.futures import ThreadPoolExecutor

def test_get_post():
    start = time.time()
    response = requests.get("http://localhost:8000/posts/1")
    elapsed = time.time() - start
    return elapsed * 1000  # ms

# 전체 테스트 시작 시간
test_start = time.time()

# 50개의 동시 요청
with ThreadPoolExecutor(max_workers=50) as executor:
    results = list(executor.map(lambda _: test_get_post(), range(50)))

# 전체 테스트 종료 시간
test_end = time.time()
total_time = test_end - test_start

# req/s 계산
num_requests = len(results)
req_per_sec = num_requests / total_time

print(f"총 요청 수: {num_requests}")
print(f"총 소요 시간: {total_time:.2f}초")
print(f"처리량 (req/s): {req_per_sec:.2f} req/s")
print(f"평균 응답 시간: {sum(results) / len(results):.2f}ms")
print(f"최대 응답 시간: {max(results):.2f}ms")
print(f"최소 응답 시간: {min(results):.2f}ms")
```

### 성능 테스트 실행하기

#### Windows

```shell
python -m venv .
# (windows/powershell)
./venv/Scripts/Activate.ps1
cd blog-service
pip install -r requirements.txt

# mysql docker가 실행이 안되어있으면 실행. 
docker build -t mysql-blog-service .
docker run --rm -d -p 3306:3306 --name mysql-blog-service mysql-blog-service

# 한쪽 Terminal에서 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 다른쪽 Terminal에서 실행
python traffic_test.py
>>>
총 요청 수: 50
총 소요 시간: 2.53초
처리량 (req/s): 19.79 req/s
평균 응답 시간: 2346.56ms
최대 응답 시간: 2478.18ms
최소 응답 시간: 2211.89ms
# 중간중간 QueuePool size 부족으로 인한, timeout issue도 생김. 
# [ERROR] 게시글 조회 실패: TimeoutError: QueuePool limit of size 5 overflow 10 reached, connection timed out, timeout 30.00 (Background on this error at: https://sqlalche.me/e/20/3o7r)
# --> 해당 이슈를 해결하기 위해, python 코드에서의 database.py를 수정함으로써 해결할 수 있다. 
```

## 🔍 현재 아키텍처의 한계점

현재 Phase1 단계를 디자인했다. 단순히 1개의 DB와 1개의 애플리케이션을 구현했다. 

이러한 첫번째 시스템 디자인은 아래와 같은 문제점을 가지고있다. 

- 1개의 애플리이션, 1개의 DB로 단일 서버에 의한 `SPOF` 문제가 발생한다. 
- 데이터베이스 부하
    - 모든 요청이 DB로 직접 전달
- 캐싱 부재
    동일한 요청, 동일한 데이터 조회에도 매번 DB접근

위에서 언급한 문제들을 하나씩 해결해 나갈것이다. 


## Phase 1 구현의 문제점. 

### 1. 단일 서버 병목
- 서버 1대만 사용 → 확장 불가능
- 서버 장애 시 전체 서비스 중단

### 2. 데이터베이스 부하
- 모든 요청이 DB로 직접 전달
- 조회수 증가 시마다 DB 업데이트 → 불필요한 부하
- 인기 게시글 조회 시 반복적인 DB 쿼리

### 3. 캐싱 부재
- 동일한 데이터를 반복 조회해도 매번 DB 접근
- 응답 시간 개선 여지 있음
---

## 🚀 다음 단계: Phase 2

Phase 1에서 발견한 문제점들을 해결하기 위해 **Phase 2: 캐싱 도입**으로 진행합니다:

### Phase 2에서 개선할 내용

1. **Redis 캐싱 도입**
   - Cache-Aside 패턴으로 인기 게시글 캐싱
   - 캐시 히트 시 응답 시간 < 50ms 목표

2. **Write-Behind 패턴**
   - 조회수, 좋아요 수 등 정합성이 중요하지 않은 데이터
   - Redis에만 기록하고 주기적으로 DB 동기화
   - DB 부하 70% 감소 목표

3. **Redis Sorted Set을 이용한 랭킹**
   - 인기 게시글 랭킹 실시간 관리

## 📝 프로젝트 구조

```
blog-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 애플리케이션 진입점
│   ├── database.py          # 데이터베이스 연결 관리
│   ├── models.py            # Pydantic 모델 (요청/응답 스키마)
│   └── routers/
│       ├── __init__.py
│       └── posts.py          # 게시글 API 라우터
├── requirements.txt         # Python 패키지 의존성
├── database.sql             # 데이터베이스 스키마
└── README.md               # 프로젝트 문서
```

---

## 🎓 마무리

Phase 1에서는 가장 단순한 아키텍처로 기본 기능을 구현했습니다. 이 단계를 통해:

✅ RESTful API 설계 경험  
✅ FastAPI와 MySQL 연동 경험  
✅ 기본적인 성능 측정 경험  
✅ 점진적 개선 접근법 이해  

다음 단계인 **Phase 2: 캐싱 도입**에서는 Redis를 활용하여 성능을 크게 개선하고, Write-Behind 패턴 등 고급 캐싱 전략을 학습하게 됩니다.

