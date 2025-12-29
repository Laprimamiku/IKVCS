-- ============================================
-- IKVCS 数据库初始化脚本
-- 基于 design.md 中的数据模型设计
-- ============================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS ikvcs CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ikvcs;

-- ============================================
-- 1. 用户表 (users)
-- 需求：1.1-1.5, 2.1-2.4
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    nickname VARCHAR(50) NOT NULL,
    avatar VARCHAR(255),
    intro VARCHAR(500),
    role ENUM('user', 'admin') DEFAULT 'user',
    status INT DEFAULT 1 COMMENT '0=封禁, 1=正常',
    last_login_time DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 2. 分类表 (categories)
-- 需求：6.1-6.3
-- ============================================
CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 3. 视频表 (videos)
-- 需求：4.1-4.5, 5.1-5.5
-- ============================================
CREATE TABLE IF NOT EXISTS videos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uploader_id INT NOT NULL,
    category_id INT NOT NULL,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    cover_url VARCHAR(255),
    video_url VARCHAR(255) COMMENT 'm3u8 路径',
    subtitle_url VARCHAR(255),
    outline TEXT COMMENT '视频内容大纲（JSON格式）',
    duration INT DEFAULT 0,
    status INT DEFAULT 0 COMMENT '0=转码中, 1=审核中, 2=已发布, 3=拒绝, 4=软删除',
    view_count INT DEFAULT 0,
    like_count INT DEFAULT 0,
    collect_count INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (uploader_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT,
    INDEX idx_status (status),
    INDEX idx_category (category_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 4. 上传会话表 (upload_sessions)
-- 需求：3.1-3.6
-- ============================================
CREATE TABLE IF NOT EXISTS upload_sessions (
    file_hash VARCHAR(64) PRIMARY KEY COMMENT 'SHA-256',
    user_id INT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    total_chunks INT NOT NULL,
    uploaded_chunks TEXT COMMENT '已上传分片索引，如: 1,2,3,5',
    is_completed BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 5. 弹幕表 (danmakus)
-- 需求：7.1-7.5, 8.1-8.5
-- ============================================
CREATE TABLE IF NOT EXISTS danmakus (
    id INT AUTO_INCREMENT PRIMARY KEY,
    video_id INT NOT NULL,
    user_id INT NOT NULL,
    content VARCHAR(255) NOT NULL,
    video_time FLOAT NOT NULL COMMENT '视频时间轴位置（秒）',
    color VARCHAR(20) DEFAULT '#FFFFFF',
    ai_score INT COMMENT 'AI 评分 0-100',
    ai_category VARCHAR(50) COMMENT 'AI 分类',
    is_highlight BOOLEAN DEFAULT FALSE COMMENT '是否高亮显示',
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_video_time (video_id, video_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 6. 评论表 (comments)
-- 需求：9.1-9.5, 10.1-10.4
-- ============================================
CREATE TABLE IF NOT EXISTS comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    video_id INT NOT NULL,
    user_id INT NOT NULL,
    parent_id INT COMMENT '父评论ID，NULL表示顶级评论',
    content TEXT NOT NULL,
    ai_score INT COMMENT 'AI 评分 0-100',
    ai_label VARCHAR(50) COMMENT 'AI 标签',
    like_count INT DEFAULT 0,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES comments(id) ON DELETE CASCADE,
    INDEX idx_video (video_id),
    INDEX idx_parent (parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 7. 点赞表 (user_likes)
-- 需求：11.1-11.5
-- ============================================
CREATE TABLE IF NOT EXISTS user_likes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    target_type ENUM('VIDEO', 'COMMENT') NOT NULL,
    target_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uq_user_like (user_id, target_type, target_id),
    INDEX idx_target (target_type, target_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 8. 收藏表 (user_collections)
-- 需求：12.1-12.4
-- ============================================
CREATE TABLE IF NOT EXISTS user_collections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    video_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
    UNIQUE KEY uq_user_collection (user_id, video_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 9. 用户兴趣表 (user_interests)
-- 需求：13.1-13.5
-- ============================================
CREATE TABLE IF NOT EXISTS user_interests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    category_id INT NOT NULL,
    weight INT DEFAULT 0 COMMENT '兴趣权重：观看+1，点赞+3，收藏+5',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
    UNIQUE KEY uq_user_category (user_id, category_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 10. 观看历史表 (watch_history)
-- ============================================
CREATE TABLE IF NOT EXISTS watch_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    video_id INT NOT NULL,
    watched_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '观看时间',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
    UNIQUE KEY uq_user_video_watch (user_id, video_id),
    INDEX idx_user_watched (user_id, watched_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 11. 举报表 (reports)
-- 需求：16.1-16.5
-- ============================================
CREATE TABLE IF NOT EXISTS reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    reporter_id INT NOT NULL,
    target_type ENUM('VIDEO', 'COMMENT', 'DANMAKU') NOT NULL,
    target_id INT NOT NULL,
    reason VARCHAR(100) NOT NULL,
    description TEXT,
    status INT DEFAULT 0 COMMENT '0=待处理, 1=已处理, 2=已忽略',
    handler_id INT COMMENT '处理人ID',
    admin_note TEXT COMMENT '管理员备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    handled_at DATETIME,
    FOREIGN KEY (reporter_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (handler_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 初始化数据
-- ============================================

-- 插入默认分类
INSERT INTO categories (name, description) VALUES
('科学', '自然科学、物理、化学等'),
('技术', '编程、工程、IT技术等'),
('数学', '数学知识和应用'),
('历史', '历史事件和人物'),
('生物', '生物学、生态学等'),
('其他', '其他科普内容');

-- 插入管理员账户（密码：admin123，需要在应用中修改）
-- 注意：password_hash 需要通过应用的密码哈希函数生成
INSERT INTO users (username, password_hash, nickname, role, status) VALUES
('admin', '$2b$12$placeholder_hash_change_this', '系统管理员', 'admin', 1);

-- ============================================
-- 完成
-- ============================================
SELECT '数据库初始化完成！' AS message;
