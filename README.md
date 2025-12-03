# IKVCS - 智能知识型视频社区系统

> Intelligent Knowledge-based Video Community System

基于 FastAPI + Vue 3 构建的科普视频社区平台，利用 LLM 对用户生成内容进行智能价值评分。

---

## 📋 项目简介

IKVCS 是面向科普学习的智能视频社区，通过 AI 技术筛选优质教育内容。

### 核心特性

- 🎥 **视频分片上传**：支持大文件上传、秒传、断点续传（SHA-256 哈希）
- 🔄 **自动转码**：FFmpeg 自动转码为 HLS 流媒体格式
- 💬 **实时弹幕**：WebSocket + Redis Pub/Sub 实现跨进程实时推送
- 🤖 **AI 智能评分**：LLM 对弹幕和评论进行价值评分（0-100分）
- 👍 **社交互动**：点赞、收藏、评论、嵌套回复
- 📊 **用户画像**：基于行为的兴趣权重模型（观看+1，点赞+3，收藏+5）
- 🛡️ **管理后台**：视频审核、用户管理、举报处理、数据统计

---

## 🛠️ 技术栈

### 后端
- **Web 框架**：FastAPI 0.104.1 + uvicorn 0.24.0
- **数据库**：MySQL 8.0 + SQLAlchemy 2.0.23
- **缓存**：Redis 5.0+ (Python redis 5.0.1)
- **认证**：JWT (python-jose 3.3.0)
- **视频处理**：FFmpeg
- **异步任务**：APScheduler 3.10.4

### 前端
- **框架**：Vue 3 + Vite
- **状态管理**：Pinia
- **UI 组件**：Element Plus
- **HTTP 客户端**：Axios
- **路由**：Vue Router 4
- **视频播放**：video.js + hls.js
- **实时通信**：WebSocket (socket.io-client)
- **数据可视化**：ECharts

---

## 📁 项目结构

```
IKVCS/
├── backend/              # 后端 FastAPI 应用
│   ├── app/
│   │   ├── api/         # API 路由层（8个路由文件）
│   │   ├── core/        # 核心配置（数据库、Redis、JWT）
│   │   ├── models/      # SQLAlchemy ORM 模型（10张表）
│   │   ├── services/    # 业务逻辑层
│   │   ├── schemas/     # Pydantic 数据验证
│   │   └── main.py      # FastAPI 应用入口
│   ├── logs/            # 日志目录
│   ├── uploads/         # 上传文件临时目录
│   ├── videos/          # 视频存储目录
│   ├── .env.example     # 环境变量示例
│   ├── requirements.txt # Python 依赖
│   ├── init_database.sql # 数据库初始化脚本
│   └── README.md        # 后端文档
│
├── frontend/            # 前端 Vue 3 应用
│   ├── src/
│   │   ├── views/       # 页面组件
│   │   ├── components/  # 公共组件
│   │   ├── stores/      # Pinia 状态管理
│   │   ├── router/      # 路由配置
│   │   ├── api/         # API 请求封装
│   │   ├── utils/       # 工具函数
│   │   ├── App.vue      # 根组件
│   │   └── main.js      # 应用入口
│   ├── public/          # 静态资源
│   ├── .env.development # 开发环境变量
│   ├── .env.production  # 生产环境变量
│   ├── package.json     # npm 依赖
│   ├── vite.config.js   # Vite 配置
│   └── README.md        # 前端文档
│
├── .gitignore           # Git 忽略规则
├── README.md            # 项目总览（本文档）
└── SETUP.md             # 环境搭建指南
```

---

## 🚀 快速开始

### 环境要求

详细安装步骤请查看 [SETUP.md](SETUP.md)

- **Python**: 3.10+
- **Node.js**: 16.x+
- **MySQL**: 8.0
- **Redis**: 5.0+
- **FFmpeg**: 最新稳定版

### 1. 克隆项目

```bash
git clone https://github.com/你的用户名/ikvcs.git
cd ikvcs
```

### 2. 数据库初始化

```bash
# 创建数据库并初始化表结构
mysql -u root -p < backend/init_database.sql
```

### 3. 后端启动

```bash
cd backend

# 创建虚拟环境（首次）
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
copy .env.example .env
notepad .env  # 编辑配置（数据库密码、API 密钥等）

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档

### 4. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 http://localhost:5173

---

## 🗄️ 数据库设计

### 10 张核心表

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| **users** | 用户表 | username, password_hash, role, status |
| **categories** | 分类表 | name, description |
| **videos** | 视频表 | title, video_url, status, view_count |
| **upload_sessions** | 上传会话表 | file_hash, uploaded_chunks, is_completed |
| **danmakus** | 弹幕表 | content, video_time, ai_score, is_highlight |
| **comments** | 评论表 | content, parent_id, ai_score, ai_label |
| **user_likes** | 点赞表 | user_id, target_type, target_id |
| **user_collections** | 收藏表 | user_id, video_id |
| **user_interests** | 用户兴趣表 | user_id, category_id, weight |
| **reports** | 举报表 | target_type, target_id, status |

---

## 🔗 核心 API 接口

### 认证接口
```
POST   /api/v1/auth/register      # 用户注册
POST   /api/v1/auth/login         # 用户登录
POST   /api/v1/auth/logout        # 用户登出
```

### 视频接口
```
GET    /api/v1/videos              # 视频列表（分页、搜索、筛选）
GET    /api/v1/videos/{id}         # 视频详情
POST   /api/v1/videos              # 创建视频记录
```

### 上传接口
```
POST   /api/v1/upload/init         # 初始化上传（秒传检测）
POST   /api/v1/upload/chunk        # 分片上传
POST   /api/v1/upload/finish       # 完成上传（触发转码）
```

### 弹幕接口
```
WS     /api/v1/ws/videos/{id}      # WebSocket 连接
POST   /api/v1/videos/{id}/danmakus  # 发送弹幕
GET    /api/v1/videos/{id}/danmakus  # 获取历史弹幕
```

### 互动接口
```
POST   /api/v1/likes               # 点赞
POST   /api/v1/collections         # 收藏
POST   /api/v1/videos/{id}/comments    # 发表评论
POST   /api/v1/comments/{id}/reply     # 回复评论
```

### 管理接口
```
GET    /api/v1/admin/videos/pending    # 待审核视频
POST   /api/v1/admin/videos/{id}/approve  # 通过审核
GET    /api/v1/admin/users             # 用户列表
POST   /api/v1/admin/users/{id}/ban    # 封禁用户
GET    /api/v1/admin/reports           # 举报列表
GET    /api/v1/admin/statistics/overview  # 统计概览
```

完整 API 文档请启动后端服务后访问 `/docs`

---

## 🎯 核心技术实现

### 1. 分片上传 + 秒传

- 前端计算文件 SHA-256 哈希
- 后端检查哈希是否已存在（秒传）
- 文件切分为 5MB 分片
- Redis BitMap 记录已上传分片
- 支持断点续传

### 2. 实时弹幕系统

- WebSocket 实时双向通信
- Redis Pub/Sub 跨进程消息广播
- 支持多服务器部署
- Canvas 渲染弹幕动画

### 3. AI 智能评分

- 异步调用 LLM API 分析内容
- 评分 0-100 分（80+ 高亮显示）
- 支持 OpenAI/Kimi/DeepSeek 等多种 LLM
- 失败不影响内容正常显示

### 4. Redis 缓存策略

- **Write-Back 缓存**：播放量先写 Redis，定时同步 MySQL
- **Set 去重**：点赞使用 Redis Set 防止重复
- **BitMap**：上传进度使用 BitMap 节省内存
- **黑名单**：JWT 登出令牌加入黑名单

### 5. 用户兴趣画像

- 观看视频：分类权重 +1
- 点赞视频：分类权重 +3
- 收藏视频：分类权重 +5
- 用于个性化推荐

---

## 📚 开发文档

### 详细文档

- **环境搭建指南**：[SETUP.md](SETUP.md) - 详细的安装和配置步骤
- **后端开发指南**：[backend/README.md](backend/README.md) - API 开发指南
- **前端开发指南**：[frontend/README.md](frontend/README.md) - 页面开发指南

### 规范文档（.kiro/specs/ikvcs-video-community/）

- **需求文档**：[requirements.md](.kiro/specs/ikvcs-video-community/requirements.md) - 20 个功能需求和验收标准
- **设计文档**：[design.md](.kiro/specs/ikvcs-video-community/design.md) - 架构设计 + 34 个正确性属性
- **任务列表**：[tasks.md](.kiro/specs/ikvcs-video-community/tasks.md) - 40 个实施任务

### 开发分工建议

**后端开发（任务 1-21）**：
- 用户认证系统（JWT + bcrypt）
- 分片上传和视频转码（FFmpeg）
- 实时弹幕系统（WebSocket + Redis Pub/Sub）
- LLM 智能评分（异步调用）
- 评论和互动功能
- 管理后台 API
- Redis 缓存策略

**前端开发（任务 22-37）**：
- 用户认证界面
- 视频上传界面（分片上传 + 进度条）
- 视频列表和播放页面（HLS 播放器）
- 实时弹幕功能（Canvas 渲染）
- 评论系统界面
- 管理后台界面
- 数据统计图表（ECharts）

---

## 🔧 开发进度

### ✅ 已完成

- [x] **任务 1**：后端基础架构（数据库、Redis、日志、数据模型）
- [x] **任务 2**：前端基础架构（Axios、Router、Pinia、页面组件）

### ⏳ 进行中

- [ ] **任务 2**：用户认证系统（注册、登录、JWT）
- [ ] **任务 23**：用户认证界面

### 📋 待开发

- 视频上传和转码
- 实时弹幕系统
- 评论和互动功能
- 管理后台
- 数据统计

---

## ⚠️ 注意事项

### 安全配置

1. **不要上传 `.env` 文件**：包含数据库密码和 API 密钥
2. **生成强密钥**：
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
3. **生产环境**：修改 `frontend/.env.production` 中的 API 地址

### LLM API 配置（可选）

系统支持多种 LLM 提供商，在 `backend/.env` 中配置：

```env
# OpenAI
LLM_API_KEY=sk-your-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo

# Kimi（月之暗面）
LLM_API_KEY=your-key
LLM_BASE_URL=https://api.moonshot.cn/v1
LLM_MODEL=moonshot-v1-8k

# DeepSeek
LLM_API_KEY=your-key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

**注意**：LLM API 是可选功能，不配置不影响其他功能开发。

---

## 🏗️ 架构设计

### 分层架构

```
┌─────────────────────────────────────┐
│  前端层 (Vue 3 + Element Plus)       │
└─────────────────────────────────────┘
              ↓ HTTP/WebSocket
┌─────────────────────────────────────┐
│  API 层 (FastAPI Router)            │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  服务层 (Business Logic)            │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  数据层 (SQLAlchemy ORM)            │
└─────────────────────────────────────┘
              ↓
┌──────────┬──────────┬──────────────┐
│  MySQL   │  Redis   │  文件存储     │
└──────────┴──────────┴──────────────┘
```

### 核心组件

- **用户认证**：JWT 令牌 + bcrypt 密码哈希 + Redis 黑名单
- **分片上传**：SHA-256 秒传 + Redis BitMap 进度记录
- **视频转码**：FFmpeg 后台任务 + HLS 流媒体
- **实时弹幕**：WebSocket 连接管理 + Redis Pub/Sub 广播
- **AI 分析**：异步 LLM 调用 + 智能评分
- **缓存策略**：Write-Back 缓存 + 定时同步

---

## 🧪 测试

### 测试框架

- **后端**：pytest + Hypothesis（属性测试）
- **前端**：Vitest（可选）

### 测试覆盖

- 34 个正确性属性
- 单元测试覆盖核心业务逻辑
- API 集成测试

---

## 📖 快速链接

- **环境搭建**：[SETUP.md](SETUP.md)
- **后端开发**：[backend/README.md](backend/README.md)
- **前端开发**：[frontend/README.md](frontend/README.md)
- **需求文档**：[.kiro/specs/ikvcs-video-community/requirements.md](.kiro/specs/ikvcs-video-community/requirements.md)
- **设计文档**：[.kiro/specs/ikvcs-video-community/design.md](.kiro/specs/ikvcs-video-community/design.md)
- **任务列表**：[.kiro/specs/ikvcs-video-community/tasks.md](.kiro/specs/ikvcs-video-community/tasks.md)

---

## 🤝 贡献指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目仅用于学习和开发目的。

---

## 📧 联系方式

如有问题或建议，欢迎提交 Issue。
