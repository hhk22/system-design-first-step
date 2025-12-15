
test:
	cd blog-service && \
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

run-master-db:
	docker build -t mysql-blog-service -f Dockerfile.mysql .

	docker network create blog-net || true

	docker run --rm -d -p 3306:3306 --network blog-net --name mysql-master \
		-e MYSQL_DATABASE=blog_db \
		-e MYSQL_USER=blog_user \
		-e MYSQL_HOST=localhost \
		-e MYSQL_PORT=3306 \
		-e MYSQL_PASSWORD=secret \
		-e MYSQL_ROOT_PASSWORD=1234 \
		mysql-blog-service \
		--log-bin=mysql-bin \
		--binlog-format=ROW \
		--gtid-mode=ON \
		--enforce-gtid-consistency=ON \
		--server-id=1 \
		--report-host=db001

	sleep 10

	docker exec mysql-master mysql -h localhost -uroot -p1234 -e "\
		CREATE USER 'replica'@'%' IDENTIFIED WITH mysql_native_password BY 'repl';\
		GRANT REPLICATION SLAVE ON *.* TO 'replica'@'%';\
		FLUSH PRIVILEGES;"

run-replica-db:
	docker build -t mysql-blog-service -f Dockerfile.mysql.replica .

	docker network create blog-net || true

	docker run --rm -d -p 3307:3306 --network blog-net --name mysql-replica \
		-e MYSQL_DATABASE=blog_db \
		-e MYSQL_USER=blog_read \
		-e MYSQL_PASSWORD=readonly \
		-e MYSQL_ROOT_PASSWORD=1234 \
		-e MYSQL_HOST=localhost \
		-e MYSQL_PORT=3307 \
		mysql-blog-service \
		--log-bin=mysql-bin \
		--binlog-format=ROW \
		--gtid-mode=ON \
		--enforce-gtid-consistency=ON \
		--relay-log=relay-bin \
		--read-only=1 \
		--server-id=2 \
		--report-host=db002
	
	sleep 10

	docker exec mysql-replica mysql -h localhost -uroot -p1234 -e "\
		STOP SLAVE; \
		RESET SLAVE ALL; \
		DROP DATABASE IF EXISTS blog_db; \
		CREATE DATABASE blog_db;"
	
	docker exec mysql-master sh -c \
     	"mysqldump -uroot -p1234 blog_db" > /tmp/blog_dump.sql
	
	cat /tmp/blog_db_dump.sql | docker exec -i mysql-replica \
     	mysql -uroot -p1234 blog_db
	
	docker exec mysql-replica mysql -h localhost -uroot -p1234 -e "\
		CHANGE MASTER TO \
			MASTER_HOST='mysql-master', \
			MASTER_USER='replica', \
			MASTER_PASSWORD='repl', \
			MASTER_AUTO_POSITION=1;\
		START SLAVE;"

stop-db:
	docker stop mysql-master
	docker stop mysql-replica

restart-db:
	make stop-db
	make run-master-db
	make run-replica-db