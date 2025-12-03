# IKVCS 后端 API

智能知识型视频社区系统 - FastAPI 后端服务

---

## 📋 技术栈（版本以 SETUP.md 为准）

```
Python: 3.10+
FastAPI: 0.104.1
uvicorn: 0.24.0
SQLAlchemy: 2.0.23
MySQL: 8.0
pymysql: 1.1.0
Redis: 5.0+
redis (Python): 5.0.1
python-jose: 3.3.0
passlib: 1.7.4
pydantic: 2.5.0
httpx: 0.25.2
python-dotenv: 1.0.0
apscheduler: 3.10.4
FFmpeg: 最新稳定版
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd backend
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 编辑 .env 文件
notepad .env
```

**必须配置**:
- `DATABASE_URL` - MySQL 连接字符串
- `SECRET_KEY` - 应用密钥（生成：`python -c "import secrets; print(secrets.token_urlsafe(32))"`）
- `JWT_SECRET_KEY` - JWT 密钥
- `LLM_API_KEY` - LLM API 密钥（可选）

### 3. 初始化数据库

```bash
mysql -u root -p < init_database.sql
```

### 4. 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档

---

## 📁 项目结构

```
backend/
├── app/
│   ├── api/              # API 路由层（8个文件）
│   │   ├── auth.py       # 用户认证
│   │   ├── users.py      # 用户管理
│   │   ├── videos.py     # 视频管理
│   │   ├── upload.py     # 分片上传
│   │   ├── danmaku.py    # 弹幕
│   │   ├── interactions.py  # 点赞/收藏/评论
│   │   ├── websocket.py  # WebSocket
│   │   └── admin.py      # 管理后台
│   ├── core/             # 核心配置（7个文件）
│   │   ├── config.py     # 配置管理
│   │   ├── database.py   # 数据库连接
│   │   ├── redis.py      # Redis 连接
│   │   ├── security.py   # JWT/密码哈希
│   │   ├── dependencies.py  # 依赖注入
│   │   └── exceptions.py # 自定义异常
│   ├── models/           # SQLAlchemy ORM 模型（8个文件）
│   │   ├── user.py
│   │   ├── video.py
│   │   ├── danmaku.py
│   │   ├── comment.py
│   │   ├── upload.py
│   │   ├── interaction.py
│   │   ├── interest.py
│   │   └── report.py
│   ├── services/         # 业务逻辑层（3个文件）
│   │   ├── llm_service.py  # LLM 智能分析
│   │   ├── redis_service.py  # Redis 操作
│   │   └── transcode_service.py  # 视频转码
│   ├── schemas/          # Pydantic 数据验证
│   │   └── user.py
│   └── main.py           # FastAPI 应用入口
├── logs/                 # 日志目录
├── uploads/              # 上传文件临时目录
├── videos/               # 视频存储目录
├── .env                  # 环境变量
├── .env.example          # 环境变量示例
├── requirements.txt      # Python 依赖
├── init_database.sql     # 数据库初始化脚本
└── README.md             # 本文档
```

---

## 🔧 开发指南

### API 开发流程

1. 定义数据模型 (`app/models/`)
2. 定义 Pydantic Schema (`app/schemas/`)
3. 实现业务逻辑 (`app/services/`)
4. 创建 API 路由 (`app/api/`)
5. 注册路由 (`app/main.py`)

### 代码示例

**API 路由**:
```python
from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user, get_db

router = APIRouter()

@router.post("/endpoint")
async def create_something(
    data: RequestSchema,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 实现逻辑
    return {"success": True, "data": result}
```

**后台任务**:
```python
from fastapi import BackgroundTasks

@router.post("/upload/finish")
async def finish_upload(background_tasks: BackgroundTasks):
    background_tasks.add_task(transcode_video, video_id)
```

---

## 📚 API 文档

启动服务后访问：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## ⚠️ 注意事项

### LLM API 配置

根据提供商配置 `.env`：

```env
# OpenAI
LLM_API_KEY=sk-your-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo

# Kimi
LLM_API_KEY=your-key
LLM_BASE_URL=https://api.moonshot.cn/v1
LLM_MODEL=moonshot-v1-8k

# DeepSeek
LLM_API_KEY=your-key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

### 开发规范

- 所有 API 使用 `/api/v1` 前缀
- 使用 Pydantic 进行请求/响应验证
- 所有删除操作使用软删除
- 统一的错误处理和响应格式

---

## 📖 相关文档

- [项目 README](../README.md)
- [前端 README](../frontend/README.md)
- [AI 开发提示词](../PROMPT.md)
- [需求文档](../.kiro/specs/ikvcs-video-community/requirements.md)
- [设计文档](../.kiro/specs/ikvcs-video-community/design.md)
- [任务列表](../.kiro/specs/ikvcs-video-community/tasks.md)
