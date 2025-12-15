# 시스템 디자인 실습: Phase 3 - DB 최적화 & 읽기/쓰기 분리

## 개요

Phase 2에서 Redis 캐시를 도입해 조회 성능을 크게 개선했습니다.  
이번 단계에서는 **MySQL 리플리카** 기반의 읽기/쓰기 분리와 **DB 인덱스 최적화**를 적용해 데이터베이스 병목을 줄입니다.

## 시스템 설계

**트래픽 목표: ~5,000 req/s** (Phase 2 대비 10배)

## 아키텍처

```
[클라이언트] → [FastAPI 서버] → [Redis] ─┐
                          ↓               │
                   [MySQL Master] ───▶ [MySQL Read Replica]
```

## 주요 개선 사항

- **읽기/쓰기 분리**  
  - 쓰기 요청은 `Master` 로컬 세션(`get_db`)에 연결  
  - 읽기 요청은 별도 리플리카 세션(`get_read_db`)을 통해 처리  
  - `.env`에서 `DB_READ_HOST`, `DB_READ_PORT` 등으로 리플리카 주소 지정 (미설정 시 Master와 동일)

- **DB 인덱싱**  
  - `created_at`, `view_count` 컬럼에 보조 인덱스 추가  
  - 최신 게시글 조회 및 인기 게시글 정렬 시 성능 향상

- **캐시 연동 강화**  
  - 캐시 히트 시에도 조회수 증가 및 랭킹 업데이트 유지  
  - `Redis Sorted Set` 점수를 그대로 응답에 사용하여 실시간 랭킹 제공  
  - 게시글 삭제 시 캐시/랭킹 키 정리

- **헬스 체크 개선**  
  - 애플리케이션 시작 시 Master/Replica 모두 연결 확인

## 구현 파일

- `blog-service/app/database.py`  
  - Master/Replica 엔진 및 세션 분리
  - `get_db`, `get_read_db` 의존성 제공 (FastAPI 라우터에서 주입)

- `blog-service/app/models.py`  
  - `Post` 모델에 인덱스 추가 (`idx_posts_created_at`, `idx_posts_view_count`)

- `blog-service/app/routers/posts.py`  
  - 조회 계열 API에 `get_read_db` 적용  
  - 랭킹 API가 Redis 점수를 그대로 활용  
  - 삭제 시 캐시/랭킹 정리

- `blog-service/app/main.py`  
  - 서버 시작 시 Master/Replica 연결 검증

## 환경 변수 예시

```bash
# Master
DB_HOST=master-db
DB_PORT=3306
DB_USER=blog_user
DB_PASSWORD=secret
DB_NAME=blog_db

# Replica (없으면 Master 설정을 그대로 사용)
DB_READ_HOST=replica-db
DB_READ_PORT=3306
DB_READ_USER=blog_read
DB_READ_PASSWORD=readonly
DB_READ_NAME=blog_db
```

## 테스트

### 자동화 테스트

```
cd blog-service
pytest
```

테스트는 SQLite + FakeRedis 환경에서 아래 사항을 검증합니다.

- `GET /posts/{id}`가 리플리카 세션을 통해 데이터를 읽는지  
- `GET /posts/ranking/popular` 응답이 Redis 점수(조회수)에 따라 정렬되는지

### 수동 체크리스트

- `.env`에 Replica 접속 정보가 없을 때도 서비스가 정상 기동되는가?  
- Replica 장애 시 캐시 경로로 조회가 가능한가?  
- Master/Replica 간 데이터 동기화 주기(예: MySQL binlog) 확인

## 성능 기대 효과

| 항목 | Phase 2 | Phase 3 | 개선 효과 |
|------|---------|---------|-----------|
| **읽기 처리량** | Redis 캐시 의존 | 캐시 + Replica | 안정적인 5,000 req/s |
| **DB 부하** | 단일 Master 집중 | 읽기 트래픽 Replica 분산 | Master CPU 사용률 감소 |
| **랭킹 응답** | Redis + DB 조회 | Redis 점수 즉시 사용 | 응답 속도 최소화 |

## 다음 단계

- Replica 지연(Replication Lag) 모니터링 추가
- 읽기 장애 시 Failover 전략 설계
- Phase 4: 로드 밸런싱 및 다중 애플리케이션 서버 확장


