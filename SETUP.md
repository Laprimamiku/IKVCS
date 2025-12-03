# IKVCS 项目环境部署指南

## 系统要求

- **操作系统**: Windows 10/11
- **开发工具**: VSCode
- **Python**: 3.10 或更高版本
- **Node.js**: 16.x 或更高版本
- **MySQL**: 8.0
- **Redis**: 5.0 或更高版本
- **FFmpeg**: 最新稳定版

---

## 一、Python 环境安装

### 1.1 安装 Python 3.10+

1. 访问 [Python 官网](https://www.python.org/downloads/)
2. 下载 Python 3.10 或更高版本的 Windows 安装包
3. 运行安装程序，**勾选 "Add Python to PATH"**
4. 验证安装：
```powershell
python --version
# 应显示: Python 3.10.x 或更高
```

### 1.2 创建虚拟环境

```powershell
# 在项目根目录创建后端目录
mkdir backend
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\activate

# 验证虚拟环境
where python
# 应显示虚拟环境中的 python.exe 路径
```

---

## 二、MySQL 8.0 安装

### 2.1 下载和安装

1. 访问 [MySQL 官网](https://dev.mysql.com/downloads/mysql/)
2. 下载 MySQL 8.0 Windows 安装包（推荐 MSI Installer）
3. 运行安装程序：
   - 选择 "Developer Default" 或 "Server only"
   - 设置 root 密码（记住此密码）
   - 端口保持默认 3306
   - 配置为 Windows 服务（开机自启）

### 2.2 验证安装

```powershell
# 打开命令行，连接 MySQL
mysql -u root -p
# 输入密码后应成功连接

# 在 MySQL 中执行
SHOW DATABASES;
# 应显示默认数据库列表
```

### 2.3 创建项目数据库

```sql
-- 创建数据库
CREATE DATABASE ikvcs CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建专用用户（可选，推荐）
CREATE USER 'ikvcs_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON ikvcs.* TO 'ikvcs_user'@'localhost';
FLUSH PRIVILEGES;

-- 验证
USE ikvcs;
SHOW TABLES;
```

---

## 三、Redis 5.0+ 安装

### 3.1 Windows 安装 Redis

**方法 1：使用 Memurai（推荐，Redis 官方推荐的 Windows 版本）**

1. 访问 [Memurai 官网](https://www.memurai.com/get-memurai)
2. 下载 Memurai Developer Edition（免费）
3. 运行安装程序，保持默认配置
4. 安装后会自动作为 Windows 服务运行

**方法 2：使用 WSL2 + Redis**

```powershell
# 安装 WSL2
wsl --install

# 在 WSL2 中安装 Redis
wsl
sudo apt update
sudo apt install redis-server
sudo service redis-server start
```

### 3.2 验证 Redis

```powershell
# 使用 redis-cli 连接
redis-cli

# 在 Redis CLI 中测试
127.0.0.1:6379> PING
# 应返回: PONG

127.0.0.1:6379> SET test "Hello Redis"
127.0.0.1:6379> GET test
# 应返回: "Hello Redis"
```

---

## 四、FFmpeg 安装

### 4.1 下载 FFmpeg

1. 访问 [FFmpeg 官网](https://ffmpeg.org/download.html)
2. 点击 Windows 图标，选择 "Windows builds from gyan.dev"
3. 下载 "ffmpeg-release-essentials.zip"

### 4.2 配置环境变量

1. 解压 zip 文件到 `C:\ffmpeg`
2. 将 `C:\ffmpeg\bin` 添加到系统 PATH：
   - 右键"此电脑" → 属性 → 高级系统设置
   - 环境变量 → 系统变量 → Path → 编辑
   - 新建 → 输入 `C:\ffmpeg\bin`
   - 确定保存

### 4.3 验证安装

```powershell
ffmpeg -version
# 应显示 FFmpeg 版本信息
```

---

## 五、Node.js 和 npm 安装

### 5.1 安装 Node.js

1. 访问 [Node.js 官网](https://nodejs.org/)
2. 下载 LTS 版本（推荐 16.x 或 18.x）
3. 运行安装程序，保持默认配置
4. 验证安装：

```powershell
node --version
# 应显示: v16.x.x 或更高

npm --version
# 应显示: 8.x.x 或更高
```

### 5.2 配置 npm 镜像（可选，加速下载）

```powershell
# 使用淘宝镜像
npm config set registry https://registry.npmmirror.com
```

---

## 六、后端依赖安装

### 6.1 创建 requirements.txt

在 `backend` 目录创建 `requirements.txt` 文件。

**推荐：使用核心依赖版本（适合快速开发和 Postman 测试）**

创建 `requirements.txt`（核心依赖）：

```txt
# ============================================
# IKVCS 后端核心依赖
# 适用于：快速开发 + Postman API 测试
# ============================================

# Web 框架
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# 数据库
sqlalchemy==2.0.23
pymysql==1.1.0
cryptography==41.0.7

# Redis
redis==5.0.1
hiredis==2.2.3

# 认证和安全
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
bcrypt==4.1.1

# 数据验证
pydantic==2.5.0
pydantic-settings==2.1.0
email-validator==2.1.0

# HTTP 客户端（调用 LLM API）
httpx==0.25.2
aiohttp==3.9.1

# 工具库
python-dotenv==1.0.0
python-dateutil==2.8.2

# 定时任务（Redis 到 MySQL 数据同步）
apscheduler==3.10.4
```

**可选：完整依赖版本（包含测试框架）**

如果后期需要编写自动化测试，创建 `requirements-dev.txt`：

```txt
# ============================================
# IKVCS 后端完整依赖（包含测试框架）
# 适用于：完整开发 + 自动化测试
# ============================================

# 包含所有核心依赖
-r requirements.txt

# 测试框架（可选，用于自动化测试）
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
hypothesis==6.92.1

# 代码质量工具（可选）
black==23.12.0
flake8==6.1.0
mypy==1.7.1

# 日志增强（可选，Python 自带 logging 也够用）
loguru==0.7.2
```

**依赖说明：**

| 依赖包 | 用途 | 是否必需 |
|--------|------|----------|
| fastapi | Web 框架 | ✅ 必需 |
| uvicorn | ASGI 服务器 | ✅ 必需 |
| sqlalchemy | ORM 数据库操作 | ✅ 必需 |
| pymysql | MySQL 驱动 | ✅ 必需 |
| redis | Redis 客户端 | ✅ 必需 |
| python-jose | JWT 令牌处理 | ✅ 必需 |
| passlib | 密码哈希 | ✅ 必需 |
| httpx/aiohttp | HTTP 客户端（调用 LLM） | ✅ 必需 |
| python-dotenv | 环境变量管理 | ✅ 必需 |
| apscheduler | 定时任务 | ⚠️ 推荐（数据同步） |
| pytest 系列 | 自动化测试 | ❌ 可选（Postman 测试可不装） |
| loguru | 日志增强 | ❌ 可选（Python logging 够用） |

### 6.2 安装依赖

```powershell
# 确保虚拟环境已激活
cd backend
.\venv\Scripts\activate

# 方案 1：安装核心依赖（推荐，快速开发）
pip install -r requirements.txt

# 方案 2：安装完整依赖（可选，包含测试框架）
# pip install -r requirements-dev.txt

# 验证安装
pip list

# 检查关键依赖是否安装成功
python -c "import fastapi; import sqlalchemy; import redis; print('核心依赖安装成功！')"
```

**安装建议：**

1. **初期开发阶段**：只安装 `requirements.txt`（核心依赖）
   - 更快的安装速度
   - 更小的虚拟环境体积
   - 使用 Postman 测试 API 完全够用

2. **后期完善阶段**：如需自动化测试，再安装 `requirements-dev.txt`
   - 包含 pytest 等测试框架
   - 用于编写单元测试和属性测试

3. **依赖升级**：定期更新依赖版本
   ```powershell
   pip list --outdated  # 查看可更新的包
   pip install --upgrade package_name  # 更新指定包
   ```

---

## 七、前端依赖安装

### 7.1 创建 Vue 3 项目

```powershell
# 在项目根目录
npm create vite@latest frontend -- --template vue

# 进入前端目录
cd frontend

# 安装基础依赖
npm install
```

### 7.2 安装项目依赖

**⚠️ 重要：请确保在 `frontend` 目录下执行以下命令**

```powershell
# 进入前端目录（如果还没有进入）
cd frontend

# 状态管理
npm install pinia

# UI 框架
npm install element-plus
npm install @element-plus/icons-vue

# HTTP 客户端
npm install axios

# WebSocket 客户端（实时弹幕）
npm install socket.io-client

# 路由
npm install vue-router@4

# 图表库
npm install echarts
npm install vue-echarts

# HLS 视频播放器
npm install hls.js
npm install video.js

# 工具库
npm install dayjs
npm install crypto-js

# 开发依赖
npm install -D sass
npm install -D @vitejs/plugin-vue
```

**依赖说明：**

| 依赖包 | 用途 | 是否必需 |
|--------|------|----------|
| pinia | 状态管理 | ✅ 必需 |
| element-plus | UI 组件库 | ✅ 必需 |
| axios | HTTP 请求 | ✅ 必需 |
| socket.io-client | WebSocket 客户端 | ✅ 必需（实时弹幕） |
| vue-router | 路由管理 | ✅ 必需 |
| echarts | 数据可视化 | ⚠️ 推荐（管理后台统计） |
| hls.js | HLS 视频播放 | ✅ 必需 |
| video.js | 视频播放器 | ✅ 必需 |
| dayjs | 时间处理 | ✅ 必需 |
| crypto-js | 加密工具 | ✅ 必需（文件哈希） |

**注意：**
- 浏览器原生支持 `WebSocket` API，但 `socket.io-client` 提供了更好的封装和自动重连功能
- 如果只使用原生 WebSocket API，可以不安装 `socket.io-client`，但需要自己处理重连逻辑

### 7.3 验证安装

```powershell
# 方法 1：查看所有已安装的包（简洁版）
npm list --depth=0

# 方法 2：验证核心依赖是否安装成功（推荐）
npm list pinia element-plus axios socket.io-client vue-router echarts hls.js video.js dayjs crypto-js

# 方法 3：一键验证所有核心依赖（最快）
node -e "const deps = ['pinia', 'element-plus', '@element-plus/icons-vue', 'axios', 'socket.io-client', 'vue-router', 'echarts', 'vue-echarts', 'hls.js', 'video.js', 'dayjs', 'crypto-js']; deps.forEach(dep => { try { require.resolve(dep); console.log('✅', dep); } catch(e) { console.log('❌', dep, '未安装'); } });"
```

**预期输出（方法 3）：**
```
✅ pinia
✅ element-plus
✅ @element-plus/icons-vue
✅ axios
✅ socket.io-client
✅ vue-router
✅ echarts
✅ vue-echarts
✅ hls.js
✅ video.js
✅ dayjs
✅ crypto-js
```

如果所有依赖都显示 ✅，说明安装成功！

---

## 八、VSCode 配置

### 8.1 安装推荐扩展

**必需扩展（强烈推荐）：**

| 扩展名 | 用途 | 是否必需 |
|--------|------|----------|
| **Python** (Microsoft) | Python 语言支持 | ✅ 必需 |
| **Pylance** (Microsoft) | Python 智能提示 | ✅ 必需 |
| **Vue Language Features (Volar)** | Vue 3 语言支持 | ✅ 必需 |
| **Prettier** | 代码格式化 | ✅ 必需 |

**可选扩展（提升体验）：**

| 扩展名 | 用途 | 是否必需 |
|--------|------|----------|
| ESLint | JavaScript 代码检查 | ⚠️ 推荐 |
| GitLens | Git 增强（类似 IDEA Git） | ⚠️ 推荐 |
| Thunder Client | API 测试（类似 Postman） | ❌ 可选（你有 Postman） |
| REST Client | HTTP 文件测试 | ❌ 可选 |
| Python Test Explorer | 测试管理 | ❌ 可选（你不用测试框架） |

**关于 Git 工具：**
- VSCode 自带 Git 功能已经很强大（类似 IDEA）
- 推荐安装 **GitLens** 扩展，提供更丰富的 Git 可视化功能
- 无需额外工具，VSCode + GitLens ≈ IDEA Git

### 8.2 工作区配置文件

**✅ 已自动创建以下配置文件：**

```
项目根目录/
└── .vscode/
    ├── settings.json      # 工作区设置（已创建）
    └── extensions.json    # 推荐扩展列表（已创建）
```

**配置文件说明：**

1. **`.vscode/settings.json`** - 工作区设置
   - ✅ Python 虚拟环境路径自动配置
   - ✅ 代码格式化设置（保存时自动格式化 Vue/JS）
   - ✅ 文件排除配置（提升性能）
   - ✅ Git 和终端配置

2. **`.vscode/extensions.json`** - 推荐扩展
   - 打开项目时 VSCode 会自动提示安装推荐扩展
   - 只包含必需和推荐的扩展
   - 自动排除冲突扩展

**验证配置：**

```powershell
# 查看配置文件是否存在
dir .vscode

# 应该看到：
# settings.json
# extensions.json
```

**使用方法：**

1. 用 VSCode 打开项目根目录
2. VSCode 会自动读取 `.vscode/settings.json` 配置
3. 右下角会弹出提示安装推荐扩展（点击"安装"即可）

---

## 九、项目目录结构

**✅ 已自动生成后端目录结构和必要文件**

### 9.1 后端目录结构

```
backend/
├── venv/                      # Python 虚拟环境
├── app/
│   ├── __init__.py           # ✅ 已创建
│   ├── main.py               # ✅ 已创建 - FastAPI 应用入口
│   ├── api/                  # API 路由层
│   │   ├── __init__.py       # ✅ 已创建
│   │   ├── auth.py           # ✅ 已创建 - 用户认证 API
│   │   ├── users.py          # ✅ 已创建 - 用户管理 API
│   │   ├── videos.py         # ✅ 已创建 - 视频列表与检索 API
│   │   ├── upload.py         # ✅ 已创建 - 分片上传 API
│   │   ├── interactions.py   # ✅ 已创建 - 点赞/收藏/评论 API
│   │   ├── danmaku.py        # ✅ 已创建 - 弹幕 API
│   │   ├── websocket.py      # ✅ 已创建 - WebSocket API
│   │   └── admin.py          # ✅ 已创建 - 管理后台 API
│   ├── core/                 # 核心配置层
│   │   ├── __init__.py       # ✅ 已创建
│   │   ├── config.py         # ✅ 已创建 - 配置管理
│   │   ├── security.py       # ✅ 已创建 - JWT/密码哈希
│   │   ├── database.py       # ✅ 已创建 - 数据库连接
│   │   ├── redis.py          # ✅ 已创建 - Redis 连接
│   │   ├── dependencies.py   # ✅ 已创建 - 依赖注入
│   │   └── exceptions.py     # ✅ 已创建 - 自定义异常
│   ├── models/               # 数据模型层（SQLAlchemy ORM）
│   │   ├── __init__.py       # ✅ 已创建
│   │   ├── user.py           # ✅ 已创建 - 用户模型
│   │   ├── video.py          # ✅ 已创建 - 视频/分类模型
│   │   ├── upload.py         # ✅ 已创建 - 上传会话模型
│   │   ├── danmaku.py        # ✅ 已创建 - 弹幕模型
│   │   ├── comment.py        # ✅ 已创建 - 评论模型
│   │   ├── interaction.py    # ✅ 已创建 - 点赞/收藏模型
│   │   ├── interest.py       # ✅ 已创建 - 用户兴趣模型
│   │   └── report.py         # ✅ 已创建 - 举报模型
│   ├── services/             # 业务逻辑层
│   │   ├── __init__.py       # ✅ 已创建
│   │   ├── llm_service.py    # ✅ 已创建 - LLM 智能分析 ⚠️ 需配置
│   │   ├── redis_service.py  # ✅ 已创建 - Redis 操作封装
│   │   └── transcode_service.py # ✅ 已创建 - 视频转码
│   └── schemas/              # Pydantic 数据验证模型
│       ├── __init__.py       # ✅ 已创建
│       └── user.py           # ✅ 已创建 - 用户相关模型
├── logs/                     # ✅ 已创建 - 日志目录
├── uploads/                  # ✅ 已创建 - 上传文件临时目录
├── videos/                   # ✅ 已创建 - 视频存储目录
├── .env.example              # ✅ 已创建 - 环境变量示例
├── .gitignore                # ✅ 已创建 - Git 忽略文件
└── requirements.txt          # ✅ 已创建 - 依赖列表
```

**文件说明：**
- ✅ 标记的文件已自动创建，包含基础结构和 TODO 注释
- ⚠️ 标记的文件需要根据实际情况配置（如 LLM API）
- 所有文件都包含详细的需求引用和实现提示

### 9.2 前端目录结构

```
frontend/
├── node_modules/             # npm 依赖（已安装）
├── public/                   # 静态资源
├── src/
│   ├── assets/              # 静态资源（图片、样式等）
│   ├── components/          # 公共组件
│   ├── views/               # 页面组件
│   ├── stores/              # Pinia 状态管理
│   ├── router/              # 路由配置
│   ├── api/                 # API 请求封装
│   ├── utils/               # 工具函数
│   ├── App.vue              # 根组件
│   └── main.js              # 应用入口
├── .env.development         # ✅ 已创建 - 开发环境变量
├── .env.production          # ✅ 已创建 - 生产环境变量
├── package.json             # npm 配置
├── vite.config.js           # Vite 配置
└── README.md
```

**注意：** 前端的 `src` 子目录需要在实施任务时创建

---

## 十、环境变量配置

**✅ 已自动生成环境变量配置文件**

### 10.1 后端环境变量

**文件位置：** `backend/.env`

**操作步骤：**

```powershell
# 1. 进入后端目录
cd backend

# 2. 复制示例文件为 .env
copy .env.example .env

# 3. 编辑 .env 文件，填写实际配置
notepad .env
```

**必须修改的配置项：**

| 配置项 | 说明 | 示例值 |
|--------|------|--------|
| `SECRET_KEY` | 应用密钥（至少 32 字符） | 随机生成的字符串 |
| `DATABASE_URL` | MySQL 连接字符串 | `mysql+pymysql://ikvcs_user:密码@localhost:3306/ikvcs` |
| `JWT_SECRET_KEY` | JWT 密钥（至少 32 字符） | 随机生成的字符串 |
| `LLM_API_KEY` | LLM API 密钥 | 你的 API Key |
| `LLM_BASE_URL` | LLM API 地址 | 根据提供商填写 |
| `LLM_MODEL` | LLM 模型名称 | 根据提供商填写 |

**⚠️ LLM API 配置说明：**

根据你使用的 LLM 提供商，修改以下三项：

```env
# OpenAI 示例：
LLM_API_KEY=sk-your-openai-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo

# Kimi (月之暗面) 示例：
LLM_API_KEY=your-kimi-api-key
LLM_BASE_URL=https://api.moonshot.cn/v1
LLM_MODEL=moonshot-v1-8k

# DeepSeek 示例：
LLM_API_KEY=your-deepseek-api-key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

**生成随机密钥：**

```powershell
# 使用 Python 生成随机密钥
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 10.2 前端环境变量

**文件位置：** 
- 开发环境：`frontend/.env.development` ✅ 已创建
- 生产环境：`frontend/.env.production` ✅ 已创建

**开发环境配置（已配置好，无需修改）：**

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_BASE_URL=ws://localhost:8000/api/v1
```

**生产环境配置（部署时修改）：**

```env
VITE_API_BASE_URL=https://your-domain.com/api/v1
VITE_WS_BASE_URL=wss://your-domain.com/api/v1
```

### 10.3 验证环境变量

```powershell
# 后端：验证 .env 文件是否存在
cd backend
dir .env

# 前端：验证环境变量文件
cd frontend
dir .env.development
dir .env.production
```

---

## 十一、验证环境

### 11.1 启动后端

```powershell
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 应该看到 FastAPI 自动生成的 API 文档

### 11.2 启动前端

```powershell
cd frontend
npm run dev
```

访问 http://localhost:5173 应该看到 Vue 应用

### 11.3 测试数据库连接

```python
# 在 backend 目录创建 test_db.py
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

engine = create_engine(os.getenv("DATABASE_URL"))
with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print("数据库连接成功！", result.fetchone())
```

运行测试：
```powershell
python test_db.py
```

### 11.4 测试 Redis 连接

```python
# 在 backend 目录创建 test_redis.py
import redis
from dotenv import load_dotenv
import os

load_dotenv()

r = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT")),
    db=int(os.getenv("REDIS_DB"))
)

r.set("test", "Hello Redis")
print("Redis 连接成功！", r.get("test").decode())
```

运行测试：
```powershell
python test_redis.py
```

---

## 十二、常见问题

### Q1: Python 虚拟环境激活失败
**A:** 如果提示"无法加载文件，因为在此系统上禁止运行脚本"，执行：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Q2: MySQL 连接失败
**A:** 检查：
1. MySQL 服务是否启动（services.msc）
2. 用户名密码是否正确
3. 数据库是否已创建
4. 防火墙是否阻止 3306 端口

### Q3: Redis 连接失败
**A:** 检查：
1. Redis 服务是否启动
2. 端口 6379 是否被占用
3. 如果使用 WSL2，确保 WSL2 正在运行

### Q4: FFmpeg 命令找不到
**A:** 
1. 确认 FFmpeg 已添加到 PATH
2. 重启命令行窗口
3. 使用完整路径：`C:\ffmpeg\bin\ffmpeg.exe`

### Q5: npm install 速度慢
**A:** 使用国内镜像：
```powershell
npm config set registry https://registry.npmmirror.com
```

---

## 下一步

环境配置完成后，您可以开始执行 `tasks.md` 中的实施任务。建议按顺序执行：

1. 先完成后端任务 1（搭建项目基础架构）
2. 再完成前端任务 22（搭建前端项目基础架构）
3. 然后按照任务列表逐步实现功能

如有任何问题，请随时询问！
