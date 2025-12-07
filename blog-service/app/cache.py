import os
import redis
from dotenv import load_dotenv
from typing import Optional
import json

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
            return self.redis_client.zrevrange(key, start, end, withscores=with_scores)
        except Exception as e:
            print(f"[Redis Error] ZRevRange failed: {e}")
            return []
    
    def zrem(self, key: str, member: str):
        """Sorted Set에서 멤버 제거"""
        try:
            self.redis_client.zrem(key, member)
        except Exception as e:
            print(f"[Redis Error] ZRem failed: {e}")

# 전역 Redis 인스턴스
cache = RedisCache()

