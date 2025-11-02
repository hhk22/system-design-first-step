

# Load balancing & API Gateway & Service Discovery

API Gateway에 따라, 각 서버별로 부하 분산처리

/product -> 상품서버

/board -> 게시판서버


# DB설계

DB caching

Cache-asdie  
    - 가장 일반적

Write-behind  
    - 빠른 응답이 필요한 데이터, 정합성은 항상 맞지는 않음. 

Cache-only  
    - DB에 저장할 필요없이, 유실되어도 괜찮은 데이터.
    - 이메일 인증 토큰, 장바구니

Caching - TTL, LRU,  LFU

캐시도입시 문제  
- 특정 키 접근 부하 병목 -> Redis 병목
- Big Key: 너무 많은 데이터를 담으면 조회/수정 시 성능저하 
- 최신 데이터 보장
    - 중요하지 않은 데이터: TTL짧게 설정, 주기적 동기화
    - 중요 데이터: 캐시 무효화 또는 즉시 동기화
- 캐시 실패 대비
    - 캐시 서버 이중화 구성
- 동시에 캐시 만료: TTL분산, 캐시미리채우기(pre-warming) 전략


# 비동기 처리

메세지 큐 & 이벤트 브로커

메세지 큐 내구성 - RAM & 디스크

이벤트브로커 - 다수의 consumer, pub/sub

메세지 처리 방식
- At-Most-Once: 
- At-least-Once:
- Exactly-Once: 

DLQ도입


아키텍쳐 그림 - draw.io
성능목표치 달성 지수 보여주기. 
성능 체크 
- postman: api응답시간, 간단한 부하테스트
- apache JMeter, nGrinder 부하테스트


================================================================











