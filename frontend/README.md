# IKVCS 前端

智能知识型视频社区系统 - Vue 3 前端应用

---

## 📋 技术栈（版本以 SETUP.md 为准）

```
Node.js: 16.x+
Vue: 3.x
Vite: 最新
Pinia: 最新
Element Plus: 最新
Axios: 最新
Vue Router: 4.x
video.js: 最新
hls.js: 最新
socket.io-client: 最新
ECharts: 最新
dayjs: 最新
crypto-js: 最新
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 配置环境变量

开发环境配置已预设在 `.env.development`：

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_BASE_URL=ws://localhost:8000/api/v1
```

生产环境需修改 `.env.production`。

### 3. 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:5173

### 4. 构建生产版本

```bash
npm run build
```

---

## 📁 项目结构

```
frontend/
├── src/
│   ├── views/           # 页面组件
│   │   ├── Home.vue           # 首页
│   │   ├── VideoDetail.vue    # 视频详情
│   │   ├── Upload.vue         # 视频上传
│   │   ├── Profile.vue        # 个人中心
│   │   └── Admin/             # 管理后台
│   ├── components/      # 公共组件
│   │   ├── VideoCard.vue      # 视频卡片
│   │   ├── DanmakuPlayer.vue  # 弹幕播放器
│   │   └── CommentList.vue    # 评论列表
│   ├── stores/          # Pinia 状态管理
│   │   ├── user.js            # 用户状态
│   │   └── video.js           # 视频状态
│   ├── router/          # 路由配置
│   │   └── index.js
│   ├── api/             # API 请求封装
│   │   ├── auth.js            # 认证 API
│   │   ├── video.js           # 视频 API
│   │   ├── upload.js          # 上传 API
│   │   └── danmaku.js         # 弹幕 API
│   ├── utils/           # 工具函数
│   │   ├── request.js         # Axios 封装
│   │   ├── auth.js            # 认证工具
│   │   └── upload.js          # 上传工具
│   ├── App.vue          # 根组件
│   └── main.js          # 应用入口
├── .env.development     # 开发环境变量
├── .env.production      # 生产环境变量
├── vite.config.js       # Vite 配置
├── package.json         # 依赖配置
└── README.md            # 本文档
```

---

## 🔧 开发指南

### 页面开发流程

1. 创建页面组件 (`src/views/`)
2. 配置路由 (`src/router/index.js`)
3. 封装 API 请求 (`src/api/`)
4. 创建 Pinia Store（如需要）
5. 开发页面逻辑和 UI

### 代码示例

**API 封装**:
```javascript
// src/api/video.js
import request from '@/utils/request'

export function getVideoList(params) {
  return request({
    url: '/videos',
    method: 'get',
    params
  })
}
```

**状态管理**:
```javascript
// src/stores/user.js
import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userInfo: null
  }),
  actions: {
    setToken(token) {
      this.token = token
      localStorage.setItem('token', token)
    }
  }
})
```

**WebSocket 连接**:
```javascript
// src/utils/websocket.js
export class DanmakuWebSocket {
  constructor(videoId) {
    this.ws = new WebSocket(`${import.meta.env.VITE_WS_BASE_URL}/ws/videos/${videoId}`)
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      // 处理弹幕消息
    }
  }
  
  send(message) {
    this.ws.send(JSON.stringify(message))
  }
}
```

---

## 🎨 UI 组件

### Element Plus

使用 Element Plus 作为 UI 组件库：

```javascript
import { ElButton, ElInput, ElMessage } from 'element-plus'
```

### 视频播放器

使用 video.js + hls.js 播放 HLS 流媒体：

```vue
<template>
  <video ref="videoPlayer" class="video-js"></video>
</template>

<script setup>
import videojs from 'video.js'

const player = videojs(videoPlayer.value, {
  sources: [{
    src: 'video.m3u8',
    type: 'application/x-mpegURL'
  }]
})
</script>
```

---

## 📦 构建与部署

### 开发环境

```bash
npm run dev
```

### 生产构建

```bash
npm run build
```

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    root /path/to/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
    }
    
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 📖 相关文档

- [项目 README](../README.md)
- [后端 README](../backend/README.md)
- [AI 开发提示词](../PROMPT.md)
- [需求文档](../.kiro/specs/ikvcs-video-community/requirements.md)
- [设计文档](../.kiro/specs/ikvcs-video-community/design.md)
- [任务列表](../.kiro/specs/ikvcs-video-community/tasks.md)
