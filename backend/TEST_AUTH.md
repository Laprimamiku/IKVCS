# 用户认证 API 测试指南

## 启动后端服务

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API 端点测试

### 1. 用户注册

**请求:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123",
    "nickname": "测试用户"
  }'
```

**预期响应:**
```json
{
  "id": 1,
  "username": "testuser",
  "nickname": "测试用户",
  "avatar": null,
  "intro": null,
  "role": "user",
  "created_at": "2024-01-01T00:00:00"
}
```

### 2. 用户登录

**请求:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }'
```

**预期响应:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 3. 用户登出

**请求:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/logout" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**预期响应:**
```json
{
  "message": "登出成功"
}
```

## 测试场景

### 场景 1: 用户名重复注册
1. 注册用户 "testuser"
2. 再次注册相同用户名
3. 应返回 400 错误: "用户名已存在"

### 场景 2: 错误密码登录
1. 使用错误密码登录
2. 应返回 401 错误: "用户名或密码错误"

### 场景 3: 令牌黑名单
1. 登录获取令牌
2. 登出（令牌加入黑名单）
3. 使用相同令牌访问受保护资源
4. 应返回 401 错误: "令牌已失效"

## 验证需求

- ✅ 需求 1.1: 验证用户名唯一性并创建账户
- ✅ 需求 1.2: 用户名已存在时拒绝注册
- ✅ 需求 1.3: 验证密码并返回 JWT 令牌
- ✅ 需求 1.4: 更新最后登录时间
- ✅ 需求 1.5: 验证 JWT 令牌有效性

## Swagger UI

访问 http://localhost:8000/docs 可以使用交互式 API 文档进行测试。
