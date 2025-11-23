
run-mysql:
	docker stop mysql-blog-service
	docker rm mysql-blog-service
	docker build -t mysql-blog-service .
	docker run --rm -d -p 3306:3306 --name mysql-blog-service mysql-blog-service

test:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

upload:
	curl -X POST "http://localhost:8000/posts" \
  		-H "Content-Type: application/json" \
  		-d '{\"title\": \"게시글 제목\", \"content\": \"게시글 내용\", \"author\": \"작성자\"}'

