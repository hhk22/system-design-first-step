# 시스템 디자인 실습: Phase 4 - 로드 밸런싱 & 수평 확장

## 개요

Phase 3까지는 단일 애플리케이션 서버를 기반으로 캐싱과 데이터베이스 최적화에 집중했습니다.  
Phase 4에서는 **Nginx 기반 로드 밸런싱**과 **다중 애플리케이션 서버 구성**을 통해 트래픽을 수평으로 분산시키고, 최대 **10,000 req/s** 수준을 안정적으로 처리하도록 확장합니다.

## 시스템 설계

- **목표 트래픽**: ~10,000 req/s  
- **최대 동시 접속자**: ~2,000명  
- **SLO**: 평균 응답 시간 < 200ms, 오류율 < 0.5%

## 아키텍처

```
[클라이언트]
    ↓
[Nginx 로드 밸런서]  ──► 헬스 체크 / Keepalive
    ↓
[FastAPI 서버 #1] ┐
[FastAPI 서버 #2] ├─► [Redis Cluster] ──► [MySQL Master]
[FastAPI 서버 #3] ┘              │
                                 └─► [MySQL Read Replicas]
```

## 주요 개선 목표

1. **트래픽 분산**: Nginx `round-robin`을 기본으로, 필요 시 `least_conn`으로 전환 가능
2. **Stateless 애플리케이션**: 세션과 공유 상태는 Redis에 저장해 인스턴스 간 독립성 유지
3. **Auto Scaling 준비**: 컨테이너 혹은 VM 단위로 애플리케이션 수를 손쉽게 조정
4. **고가용성 확보**: 헬스 체크, 장애 인스턴스 제거, Redis/MySQL 복제본 활용

---

## 구현 요소

### 1. Nginx 로드 밸런서

- 설정 파일 예시: `deploy/nginx.phase4.conf`
- 기능
  - `upstream` 블록으로 FastAPI 인스턴스 등록
  - `/health` 엔드포인트를 통한 헬스 체크
  - `proxy_set_header`를 통해 원본 IP(`X-Forwarded-For`) 전달

```nginx
worker_processes auto;
events { worker_connections 1024; }

http {
    upstream blog_service_backend {
        least_conn;
        server app-1:8000 max_fails=3 fail_timeout=10s;
        server app-2:8000 max_fails=3 fail_timeout=10s;
        server app-3:8000 max_fails=3 fail_timeout=10s;
    }

    server {
        listen 80;

        location / {
            proxy_pass http://blog_service_backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 2s;
            proxy_read_timeout 5s;
        }

        location /health {
            proxy_pass http://blog_service_backend/health;
        }
    }
}
```

### 2. FastAPI 애플리케이션 서버 확장

- 컨테이너 혹은 프로세스로 3개의 인스턴스 실행 (`uvicorn --workers 4`)
- `blog-service/app/main.py`에 `/health` 엔드포인트 추가
- 모든 상태 정보(세션, 캐시, 랭킹)는 Redis를 통해 공유
- 환경 변수로 인스턴스 라벨을 노출 가능 (`APP_INSTANCE_ID`)

```python
# blog-service/app/main.py
from fastapi import FastAPI
from .routers import posts

app = FastAPI(title="Blog Service Phase 4")
app.include_router(posts.router, prefix="/posts", tags=["posts"])

@app.get("/health")
def health_check():
    return {"status": "ok"}
```

### 3. Redis Cluster & 세션 공유

- `redis.conf`에 `cluster-enabled yes` 설정
- `redis-cli --cluster`로 3 노드 구성을 생성 (1 master, 2 replica)
- 세션/로그인 같은 상태는 `redis-py` 혹은 `aioredis` 기반으로 처리

```python
# 예시: 사용자 세션 저장 (JWT 사용 시 생략 가능)
import uuid
from app.cache import cache

SESSION_TTL = 3600

def create_session(user_id: int) -> str:
    session_id = str(uuid.uuid4())
    cache.set(f"session:{session_id}", str(user_id), expire=SESSION_TTL)
    return session_id

def get_session(session_id: str) -> int | None:
    user_id = cache.get(f"session:{session_id}")
    return int(user_id) if user_id else None
```

### 4. Docker Compose (Phase 4 전용)

- 새 파일: `deploy/docker-compose.phase4.yml`
- 주요 서비스
  - `nginx-lb`: 위에서 정의한 Nginx 설정 파일 사용
  - `app-1` ~ `app-3`: 동일 이미지를 사용하는 FastAPI 인스턴스
  - `redis-master`, `redis-replica{1,2}`: Redis Cluster 구성
  - `mysql-master`, `mysql-replica`: Phase 3에서 구축한 구조 재사용

```yaml
version: "3.9"

x-app-base: &app_base
  build:
    context: ../blog-service
    dockerfile: ../Dockerfile
  depends_on:
    - mysql-master
    - redis-master

services:
  nginx-lb:
    image: nginx:1.27
    ports:
      - "80:80"
    volumes:
      - ./nginx.phase4.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - app-1
      - app-2
      - app-3

  app-1:
    <<: *app_base
    container_name: app-1
    environment:
      APP_INSTANCE_ID: app-1
      REDIS_HOST: redis-master

  app-2:
    <<: *app_base
    container_name: app-2
    environment:
      APP_INSTANCE_ID: app-2
      REDIS_HOST: redis-master

  app-3:
    <<: *app_base
    container_name: app-3
    environment:
      APP_INSTANCE_ID: app-3
      REDIS_HOST: redis-master

  mysql-master:
    image: mysql:8.0
    env_file:
      - ../blog-service/.env
    volumes:
      - mysql-master-data:/var/lib/mysql

  mysql-replica:
    image: mysql:8.0
    env_file:
      - ../blog-service/.env.replica
    volumes:
      - mysql-replica-data:/var/lib/mysql
    depends_on:
      - mysql-master

  redis-master:
    image: redis:7.4
    command: ["redis-server", "/usr/local/etc/redis/redis.conf"]
    volumes:
      - ../redis.conf:/usr/local/etc/redis/redis.conf:ro

  redis-replica1:
    image: redis:7.4
    command: ["redis-server", "--slaveof", "redis-master", "6379"]
    depends_on:
      - redis-master

  redis-replica2:
    image: redis:7.4
    command: ["redis-server", "--slaveof", "redis-master", "6379"]
    depends_on:
      - redis-master

volumes:
  mysql-master-data:
  mysql-replica-data:
```

> **Tip**: 실제 운영에서는 `docker compose` 대신 Kubernetes, AWS ECS, GCP GKE 등 매니지드 오케스트레이션을 활용하는 것이 일반적입니다.

### 5. 무중단 배포 & 헬스 체크

- Nginx는 5초 간격으로 `/health`를 호출해 장애 인스턴스를 upstream에서 제외
- 신규 버전 배포 시, `docker compose up --scale app=4`로 신규 인스턴스를 추가 후 헬스 체크 통과 시 이전 버전 제거
- 롤백: 장애 시 기존 이미지를 재배포하거나 `docker compose`로 이전 태그 실행

### 6. Observability

- **로그 수집**: Nginx access/error 로그, FastAPI 구조화된 로그
- **메트릭**: Prometheus + Grafana 조합 권장 (요청 처리량, 에러율, 인스턴스별 CPU/메모리)
- **분산 트레이싱**: OpenTelemetry를 FastAPI와 연동해 요청 경로 추적

---

## 실행 절차

```bash
# 1) 네트워크 준비
docker network create blog-phase4 || true

# 2) Phase 3에서 사용한 데이터베이스/캐시 마이그레이션
alembic upgrade head  # 필요 시

# 3) 로컬에서 로드 밸런싱 환경 실행
docker compose -f deploy/docker-compose.phase4.yml up --build

# 4) 헬스 체크
curl http://localhost/health
```

---

## 성능 테스트 시나리오

1. **기본 부하 테스트**: `wrk -t12 -c400 -d60s http://localhost/posts/1`
2. **nGrinder 시나리오**: 동시 사용자 2,000명, 초당 10,000 요청 가정
3. **장애 주입 테스트**: `app-2` 컨테이너 중지 후 로드 밸런서가 자동으로 트래픽을 재분배하는지 확인
4. **세션 일관성**: 로그인 후 세션이 다른 인스턴스로 라우팅되더라도 유지되는지 확인

테스트 결과는 `docs/performance/phase4.md`에 기록해 비교(Phase 3 대비 응답 시간, 처리량, 오류율).

---

## 장애 대응 전략

- **애플리케이션 인스턴스 장애**: Nginx 헬스 체크 실패 시 자동 제외 → 알림 발송
- **Redis 노드 장애**: Cluster 슬럿 재배치 혹은 Sentinel 기반 failover 수행
- **MySQL Master 장애**: Replica를 승격시키고 애플리케이션 환경 변수 업데이트
- **로드 밸런서 장애**: DNS 레벨 로드 밸런서(ALB, Cloud DNS)와 이중화 구성

---

## 운영 체크리스트

- [ ] Nginx 로드 밸런서를 컨테이너/VM으로 배포
- [ ] FastAPI 애플리케이션 3대 이상 가동
- [ ] Redis Cluster 구성 및 세션 저장 검증
- [ ] MySQL Master/Replica 헬스 체크
- [ ] nGrinder / wrk 부하 테스트 수행
- [ ] CPU/메모리/네트워크 대시보드 구축

---

## 다음 단계

Phase 4에서 수평 확장을 구현했으므로, **Phase 5**에서는 메시지 큐와 비동기 작업(Celery, RabbitMQ)을 도입해 무거운 작업을 분리하고 API 응답 속도를 더욱 끌어올립니다.
