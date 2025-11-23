-- 블로그/게시판 서비스 데이터베이스 스키마

-- 문자셋 설정 (SQL 파일 실행 시 먼저 설정)
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 데이터베이스 생성 (문자셋 명시)
CREATE DATABASE IF NOT EXISTS blog_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE blog_db;

-- 게시글 테이블
CREATE TABLE IF NOT EXISTS posts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    author VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    view_count INT DEFAULT 0,
    INDEX idx_created_at (created_at),
    INDEX idx_author (author)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 샘플 데이터
INSERT INTO posts (title, content, author) VALUES
('첫 번째 게시글', '이것은 첫 번째 게시글의 내용입니다.', 'user1'),
('두 번째 게시글', '이것은 두 번째 게시글의 내용입니다.', 'user2'),
('세 번째 게시글', '이것은 세 번째 게시글의 내용입니다.', 'user1');

