# Blog Service - Phase 1

간단한 블로그/게시판 서비스의 Phase 1 구현입니다.

## 🚀 설치 및 실행

### 1. 프로젝트 클론 및 이동

```bash
cd blog-service
```

### 2. 가상환경 생성 및 활성화

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. 패키지 설치

```bash
pip install -r requirements.txt
```

### 4. MySQL 데이터베이스 설정

```bash
# MySQL에 접속하여 데이터베이스 생성
mysql -u root -p < database.sql
```

또는 MySQL 클라이언트에서 직접 실행:

```sql
CREATE DATABASE IF NOT EXISTS blog_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE blog_db;
-- database.sql 파일의 내용 실행
```

### 5. 환경 변수 설정

`.env.example` 파일을 복사하여 `.env` 파일 생성:

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

`.env` 파일을 열어서 데이터베이스 정보 수정:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=blog_db

HOST=0.0.0.0
PORT=8000
```

### 6. 서버 실행

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

서버가 실행되면 다음 URL에서 접근 가능합니다:

- **API 문서**: http://localhost:8000/docs
- **대체 문서**: http://localhost:8000/redoc
- **루트**: http://localhost:8000/
- **헬스 체크**: http://localhost:8000/health

## 📚 API 엔드포인트

### 게시글 작성
```
POST /posts
Content-Type: application/json

{
  "title": "게시글 제목",
  "content": "게시글 내용",
  "author": "작성자"
}
```

### 게시글 목록 조회
```
GET /posts?skip=0&limit=10
```

### 게시글 조회 (단일)
```
GET /posts/{post_id}
```

### 게시글 수정
```
PUT /posts/{post_id}
Content-Type: application/json

{
  "title": "수정된 제목",
  "content": "수정된 내용"
}
```

### 게시글 삭제
```
DELETE /posts/{post_id}
```

## 🧪 테스트

### Postman 사용

1. Postman에서 새 Collection 생성
2. 위의 API 엔드포인트들을 추가
3. 각 API를 테스트하며 응답 시간 확인

### cURL 사용

```bash
# 게시글 작성
curl -X POST "http://localhost:8000/posts" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "테스트 게시글",
    "content": "테스트 내용입니다.",
    "author": "테스트 작성자"
  }'

# 게시글 목록 조회
curl "http://localhost:8000/posts"

# 게시글 조회
curl "http://localhost:8000/posts/1"

# 게시글 수정
curl -X PUT "http://localhost:8000/posts/1" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "수정된 제목",
    "content": "수정된 내용"
  }'

# 게시글 삭제
curl -X DELETE "http://localhost:8000/posts/1"
```

## 📊 성능 목표

- 응답 시간: < 200ms
- 동시 사용자: ~50명

## 🔄 다음 단계

Phase 1 완료 후 Phase 2로 진행:
- Redis 캐싱 도입
- Write-Behind 패턴 구현 (조회수, 좋아요 등)

## 📝 프로젝트 구조

```
blog-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 애플리케이션
│   ├── database.py          # 데이터베이스 연결
│   ├── models.py            # Pydantic 모델
│   └── routers/
│       ├── __init__.py
│       └── posts.py         # 게시글 API 라우터
├── requirements.txt         # Python 패키지 의존성
├── database.sql             # 데이터베이스 스키마
├── .env.example             # 환경 변수 예시
└── README.md               # 프로젝트 문서
```

## 🐛 문제 해결

### 데이터베이스 연결 실패
- MySQL이 실행 중인지 확인
- `.env` 파일의 데이터베이스 정보 확인
- MySQL 사용자 권한 확인

### 포트 충돌
- 다른 애플리케이션이 8000 포트를 사용 중인지 확인
- `.env` 파일에서 포트 변경

### 패키지 설치 오류
- Python 버전 확인 (3.8+ 필요)
- 가상환경이 활성화되어 있는지 확인

