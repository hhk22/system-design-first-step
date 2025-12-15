# 시스템 디자인 학습 미니 프로젝트

## 프로젝트 선택: **간단한 블로그/게시판 서비스**

### 선택 이유
- 읽기 중심이라 캐싱 전략 적용하기 좋음
- 쓰기도 있어서 트랜잭션/일관성 문제 경험 가능
- 기능이 직관적이라 구현이 쉬움
- 확장하기 좋은 구조

---

## 단계별 시스템 설계 개선

### 📌 Phase 1: 초기 버전 (트래픽: ~100 req/s)
**목표**: 기본 기능 구현

**아키텍처:**
```
[클라이언트] → [Flask/FastAPI 서버] → [MySQL]
```

**구현 내용:**
- Python Flask/FastAPI 서버 1대
- MySQL DB 1대
- 기본 CRUD 기능
  - 게시글 작성
  - 게시글 조회
  - 게시글 목록
  - 게시글 수정/삭제

**성능 목표:**
- 응답 시간: < 200ms
- 동시 사용자: ~50명

**테스트:**
- Postman으로 API 응답 시간 측정

---

### 📌 Phase 2: 캐싱 도입 (트래픽: ~1,000 req/s)
**문제점**: 조회 요청이 많아짐 → DB 부하 증가

**아키텍처:**
```
[클라이언트] → [Flask/FastAPI] → [Redis Cache] ┐
                                              ↓
                                           [MySQL]
```

**구현 내용:**
- Redis 캐싱 도입 (Cache-Aside 패턴)
  - 인기 게시글 캐싱 (TTL: 5분)
  - 게시글 목록 캐싱 (TTL: 1분)
  - 캐시 미스 시 DB 조회 후 캐시 저장

- **정합성이 중요하지 않은 데이터 (Write-Behind 패턴)**
  - 조회수 (View Count) → Redis에만 저장, 주기적으로 DB 동기화
  - 좋아요 수 (Like Count) → Redis 카운터 사용, 10분마다 DB 업데이트
  - 댓글 수 (Comment Count) → Redis에서 관리, 캐시 무효화 시에만 DB 동기화
  - 인기 게시글 랭킹 → Redis Sorted Set 사용, 5분마다 재계산

**성능 목표:**
- 캐시 히트 시 응답 시간: < 50ms
- DB 부하 70% 감소

**테스트:**
- JMeter로 부하 테스트 (1,000 req/s)
- 캐시 히트율 모니터링

---

### 📌 Phase 3: DB 최적화 (트래픽: ~5,000 req/s)
**문제점**: 쿼리 성능 저하, 느린 조회

**아키텍처:**
```
[클라이언트] → [Flask/FastAPI] → [Redis Cache] ┐
                                              ↓
                                    [MySQL (Master-Slave)]
                                           ↓
                                    [읽기 전용 Slave]
```

**구현 내용:**
- MySQL 인덱스 최적화
- 읽기/쓰기 분리 (Master-Slave)
- 쿼리 최적화 (N+1 문제 해결)
- Redis 이중화 (고가용성)

**성능 목표:**
- DB 쿼리 시간: < 100ms
- 응답 시간: < 150ms

**테스트:**
- 느린 쿼리 로그 분석
- 인덱스 사용률 확인

---

### 📌 Phase 4: 로드 밸런싱 (트래픽: ~10,000 req/s)
**문제점**: 단일 서버 병목

**아키텍처:**
```
[클라이언트]
    ↓
[Nginx 로드 밸런서]
    ↓
[Flask/FastAPI 서버 1] ┐
[Flask/FastAPI 서버 2] ├→ [Redis Cluster] → [MySQL Master-Slave]
[Flask/FastAPI 서버 3] ┘
```

**구현 내용:**
- Nginx 로드 밸런서 (`least_conn`, 헬스 체크, Keepalive)
- FastAPI 애플리케이션 3대 이상 가동, `/health` 엔드포인트 제공
- Redis Cluster/Sentinel로 세션 및 캐시 공유 (Stateless 보장)
- `deploy/docker-compose.phase4.yml` 기반 다중 인스턴스 실행 (혹은 Kubernetes/ECS)
- 무중단 배포 전략 (Rolling Update, 장애 인스턴스 자동 제외)
- Observability: Prometheus + Grafana 메트릭, 로그 수집, OpenTelemetry 트레이싱

**성능 목표:**
- 처리량: 10,000 req/s
- 응답 시간: < 200ms (평균)

**테스트:**
- `wrk` 또는 nGrinder로 부하 테스트 (동시 사용자 2,000명 이상)
- 장애 주입 테스트 (인스턴스 다운 시 트래픽 재분배 확인)
- 세션 일관성 검증, 서버별 CPU/메모리 모니터링

**실습 가이드**: [mini-project/phase4-load-balancing.md](../mini-project/phase4-load-balancing.md)

---

### 📌 Phase 5: 비동기 처리 (트래픽: ~20,000 req/s)
**문제점**: 무거운 작업이 API 응답을 지연시킴

**아키텍처:**
```
[클라이언트] → [Nginx] → [Flask/FastAPI 서버들]
                              ↓
                        [RabbitMQ / Redis Queue]
                              ↓
                    [비동기 Worker (Celery)]
                              ↓
                    [이메일 발송, 이미지 처리 등]
```

**구현 내용:**
- RabbitMQ 또는 Redis Queue 도입
- Celery로 비동기 작업 처리
- 이메일 알림 (비동기)
- 이미지 리사이징 (비동기)
- 파일 업로드 처리 (비동기)

**성능 목표:**
- API 응답 시간: < 100ms (비동기 작업 제외)
- 백그라운드 작업 처리량 증가

**테스트:**
- 큐 메시지 처리량 측정
- DLQ (Dead Letter Queue) 설정

---

### 📌 Phase 6: API Gateway & 서비스 분리 (트래픽: ~50,000 req/s)
**문제점**: 모놀리식 구조로 인한 확장 어려움

**아키텍처:**
```
[클라이언트]
    ↓
[API Gateway (Kong / Nginx)]
    ↓
    ├→ /posts → [게시판 서비스]
    ├→ /users → [사용자 서비스]
    └→ /comments → [댓글 서비스]
```

**구현 내용:**
- API Gateway 도입 (Nginx 또는 Kong)
- 서비스 분리
  - 게시판 서비스
  - 사용자 서비스
  - 댓글 서비스
- 각 서비스별 독립 배포
- 인증/인가 중앙화

**성능 목표:**
- 서비스별 독립 확장
- 장애 격리

**테스트:**
- 서비스별 부하 테스트
- 장애 시나리오 테스트

---

## 기술 스택

### 백엔드
- **Python**: Flask 또는 FastAPI
- **DB**: MySQL (단계적으로 Master-Slave)
- **캐시**: Redis
- **메시지 큐**: RabbitMQ 또는 Redis Queue
- **비동기 작업**: Celery

### 인프라
- **로드 밸런서**: Nginx
- **API Gateway**: Nginx 또는 Kong (간단하게는 Nginx)
- **컨테이너**: Docker (선택사항)

### 모니터링
- **성능 테스트**: Postman, JMeter, nGrinder
- **로깅**: Python logging
- **모니터링**: 간단한 메트릭 수집 (선택사항)

---

## 단계별 체크리스트

### Phase 1 ✅
- [ ] 기본 CRUD API 구현
- [ ] MySQL 스키마 설계
- [ ] Postman으로 기본 테스트

### Phase 2 ✅
- [ ] Redis 설치 및 연결
- [ ] Cache-Aside 패턴 구현 (읽기 중심 데이터)
- [ ] Write-Behind 패턴 구현 (조회수, 좋아요 등)
- [ ] Redis Sorted Set을 이용한 인기 게시글 랭킹
- [ ] 배치 동기화 작업 (주기적 DB 업데이트)
- [ ] 캐시 히트율 측정

### Phase 3 ✅
- [ ] MySQL 인덱스 추가
- [ ] 읽기/쓰기 분리 (선택사항, 복잡할 수 있음)
- [ ] 쿼리 최적화

### Phase 4 ✅
- [ ] Nginx 로드 밸런서 설정 (`least_conn` + 헬스 체크)
- [ ] FastAPI 인스턴스 3대 이상 실행 및 `/health` 확인
- [ ] Redis Cluster로 세션/캐시 공유
- [ ] 무중단 배포 전략 검증 (scale up/down)
- [ ] 부하/장애 테스트 (wrk, nGrinder)

### Phase 5 ✅
- [ ] RabbitMQ/Redis Queue 설정
- [ ] Celery Worker 구성
- [ ] 비동기 작업 구현

### Phase 6 ✅
- [ ] API Gateway 설정
- [ ] 서비스 분리
- [ ] 라우팅 규칙 설정

---

## 학습 목표

1. **캐싱 전략**: 
   - Cache-Aside (읽기 중심)
   - Write-Behind (정합성 중요하지 않은 쓰기 데이터)
   - TTL 설정 및 캐시 무효화
2. **로드 밸런싱**: 트래픽 분산
3. **비동기 처리**: 큐 시스템 활용
4. **서비스 분리**: 모놀리식 → 마이크로서비스
5. **모니터링**: 성능 측정 및 최적화

---

## 시작하기

1. **Phase 1부터 시작**: 기본 기능 구현
2. **부하 테스트 실행**: 각 단계마다 성능 측정
3. **문제점 파악**: 병목 지점 찾기
4. **해결책 적용**: 다음 Phase로 진행
5. **성능 개선 확인**: Before/After 비교

**추천**: Phase 4까지는 필수, Phase 5-6은 선택사항으로 진행!

---

## Phase 2: 정합성이 중요하지 않은 데이터 캐싱 구현 예시

### 1. 조회수 (Write-Behind 패턴)

```python
import redis
from datetime import timedelta

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def increment_view_count(post_id):
    """조회수 증가 (Redis에만 기록, 주기적으로 DB 동기화)"""
    key = f"view_count:{post_id}"
    redis_client.incr(key)
    redis_client.expire(key, timedelta(hours=24))  # 24시간 TTL
    
    # 백그라운드 작업으로 주기적으로 DB 동기화 (예: 10분마다)
    # 실제 구현은 Celery 등으로 처리

def get_view_count(post_id):
    """조회수 조회 (Redis에서만 읽기)"""
    key = f"view_count:{post_id}"
    count = redis_client.get(key)
    return int(count) if count else 0

def sync_view_count_to_db(post_id, count):
    """주기적으로 DB에 동기화 (백그라운드 작업)"""
    # UPDATE posts SET view_count = view_count + {count} WHERE id = {post_id}
    pass
```

### 2. 좋아요 수 (Redis Counter)

```python
def toggle_like(user_id, post_id):
    """좋아요 토글 (Redis Set 사용)"""
    like_key = f"likes:{post_id}"
    
    if redis_client.sismember(like_key, user_id):
        # 이미 좋아요 → 취소
        redis_client.srem(like_key, user_id)
        redis_client.decr(f"like_count:{post_id}")
    else:
        # 좋아요 추가
        redis_client.sadd(like_key, user_id)
        redis_client.incr(f"like_count:{post_id}")
    
    # 10분마다 DB에 배치 업데이트 (백그라운드 작업)

def get_like_count(post_id):
    """좋아요 수 조회"""
    count = redis_client.get(f"like_count:{post_id}")
    return int(count) if count else 0
```

### 3. 댓글 수 (캐시 무효화 방식)

```python
def add_comment(post_id, comment_data):
    """댓글 추가"""
    # DB에 댓글 저장
    comment_id = db.insert_comment(post_id, comment_data)
    
    # 댓글 수 캐시 무효화 (또는 증가)
    cache_key = f"comment_count:{post_id}"
    redis_client.incr(cache_key)
    
    # 댓글 수는 DB에서 정확히 관리하되, 조회는 캐시 사용
    return comment_id

def get_comment_count(post_id):
    """댓글 수 조회 (캐시 우선, 없으면 DB에서 로드)"""
    cache_key = f"comment_count:{post_id}"
    count = redis_client.get(cache_key)
    
    if count is None:
        # 캐시 미스 → DB에서 조회 후 캐시 저장
        count = db.get_comment_count(post_id)
        redis_client.set(cache_key, count, ex=300)  # 5분 TTL
    
    return int(count)
```

### 4. 인기 게시글 랭킹 (Redis Sorted Set)

```python
def update_post_ranking(post_id, score):
    """게시글 랭킹 업데이트 (조회수 + 좋아요 수 기반)"""
    ranking_key = "post_ranking"
    redis_client.zadd(ranking_key, {post_id: score})
    
    # 5분마다 DB에 동기화 (백그라운드 작업)

def get_popular_posts(limit=10):
    """인기 게시글 목록 (상위 N개)"""
    ranking_key = "post_ranking"
    # ZREVRANGE: 점수 높은 순으로 조회
    top_posts = redis_client.zrevrange(ranking_key, 0, limit-1, withscores=True)
    
    # post_id 리스트로 변환
    return [int(post_id) for post_id, score in top_posts]

def calculate_ranking_score(view_count, like_count):
    """랭킹 점수 계산"""
    return view_count * 1 + like_count * 10  # 좋아요는 가중치 더 높게
```

### 5. 배치 동기화 작업 (주기적 DB 업데이트)

```python
from celery import Celery

celery_app = Celery('tasks', broker='redis://localhost:6379/0')

@celery_app.task
def sync_view_counts_to_db():
    """조회수 DB 동기화 (10분마다 실행)"""
    pattern = "view_count:*"
    keys = redis_client.keys(pattern)
    
    for key in keys:
        post_id = int(key.split(':')[1])
        count = int(redis_client.get(key))
        
        # DB에 업데이트
        db.update_view_count(post_id, count)
        # Redis에서 삭제하거나 초기화
        redis_client.delete(key)

@celery_app.task
def sync_like_counts_to_db():
    """좋아요 수 DB 동기화 (10분마다 실행)"""
    pattern = "like_count:*"
    keys = redis_client.keys(pattern)
    
    for key in keys:
        post_id = int(key.split(':')[1])
        count = int(redis_client.get(key))
        db.update_like_count(post_id, count)
```

### 핵심 포인트:

1. **조회수, 좋아요**: Redis에만 기록, 주기적으로 DB 동기화
2. **댓글 수**: 캐시 무효화 방식 (쓰기 시 즉시 갱신)
3. **랭킹**: Redis Sorted Set으로 실시간 관리
4. **배치 작업**: Celery로 주기적 DB 동기화

### 장점:
- ✅ **DB 부하 대폭 감소**: 조회수 증가 시 DB 업데이트 불필요
- ✅ **빠른 응답**: Redis 인메모리 조회로 매우 빠름
- ✅ **확장성**: 높은 트래픽에도 안정적

### 주의사항:
- ⚠️ **데이터 손실 가능**: Redis 장애 시 일부 데이터 손실 가능
- ⚠️ **최종 일관성**: 실시간 정합성 보장 안 됨 (정확하지 않아도 되는 데이터만 사용!)
