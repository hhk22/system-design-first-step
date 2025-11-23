FROM mysql:8.0

ENV MYSQL_DATABASE=blog_db
ENV MYSQL_USER=test_user
ENV MYSQL_PASSWORD=1234
ENV MYSQL_ROOT_PASSWORD=1234

COPY ./blog-service/database.sql /docker-entrypoint-initdb.d/init.sql

EXPOSE 3306
