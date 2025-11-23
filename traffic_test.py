import requests
import time
from concurrent.futures import ThreadPoolExecutor

def test_get_post():
    start = time.time()
    response = requests.get("http://localhost:8000/posts/1")
    elapsed = time.time() - start
    return elapsed * 1000  # ms

# 50개의 동시 요청
with ThreadPoolExecutor(max_workers=100) as executor:
    results = list(executor.map(lambda _: test_get_post(), range(100)))

print(f"평균 응답 시간: {sum(results) / len(results):.2f}ms")
print(f"최대 응답 시간: {max(results):.2f}ms")
print(f"최소 응답 시간: {min(results):.2f}ms")