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