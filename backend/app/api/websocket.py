"""
WebSocket 实时通信 API
需求：7.1, 7.2, 7.3
"""
import asyncio
import json
import logging
from typing import List, Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# ==================== 连接管理器 ====================

class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        # 存储结构：{video_id: [websocket1, websocket2, ...]}
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, video_id: int):
        await websocket.accept()
        if video_id not in self.active_connections:
            self.active_connections[video_id] = []
        self.active_connections[video_id].append(websocket)
        print(f"DEBUG: [ConnectionManager] 新连接加入 Video {video_id}，当前池中 keys: {list(self.active_connections.keys())}") # DEBUG

    def disconnect(self, websocket: WebSocket, video_id: int):
        if video_id in self.active_connections:
            if websocket in self.active_connections[video_id]:
                self.active_connections[video_id].remove(websocket)
            if not self.active_connections[video_id]:
                del self.active_connections[video_id]
        print(f"DEBUG: [ConnectionManager] 连接断开 Video {video_id}") # DEBUG

    async def broadcast_to_video(self, video_id: int, message: dict):
        """向指定视频的所有连接广播消息"""
        if video_id in self.active_connections:
            # 序列化消息
            text_data = json.dumps(message)
            connections = self.active_connections[video_id][:]
            
            print(f"DEBUG: [Broadcast] 正在向 Video {video_id} 的 {len(connections)} 个连接推送消息...") # DEBUG
            
            for connection in connections:
                try:
                    await connection.send_text(text_data)
                except Exception as e:
                    logger.error(f"发送 WebSocket 消息失败: {e}")
                    self.disconnect(connection, video_id)
        else:
            print(f"DEBUG: [Broadcast] Video {video_id} 在本地没有活跃连接，跳过推送") # DEBUG

# 全局连接管理器实例
manager = ConnectionManager()

# ==================== Redis 监听服务 (跨进程广播) ====================

async def start_redis_listener():
    """
    后台任务：监听 Redis 频道并广播到 WebSocket
    """
    redis_url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
    client = await aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)
    pubsub = client.pubsub()
    
    # 订阅所有弹幕频道
    await pubsub.psubscribe("danmaku:video:*")
    
    logger.info("Redis Pub/Sub 监听器已启动 (Pattern: danmaku:video:*)")
    
    try:
        async for message in pubsub.listen():
            # 过滤掉订阅成功的确认消息
            if message["type"] == 'psubscribe':
                continue
                
            print(f"DEBUG: [RedisListener] 收到原始消息: {message}") # DEBUG

            if message["type"] == "pmessage":
                channel = message["channel"]
                data = message["data"]
                
                try:
                    # 频道格式: danmaku:video:{video_id}
                    video_id_str = channel.split(":")[-1]
                    video_id = int(video_id_str)
                    
                    parsed_data = json.loads(data)
                    
                    print(f"DEBUG: [RedisListener] 解析成功 -> Video: {video_id}, 准备寻找本地连接...") # DEBUG
                    
                    # 仅当本进程有该视频的连接时才广播
                    if video_id in manager.active_connections:
                        await manager.broadcast_to_video(video_id, parsed_data)
                    else:
                        print(f"DEBUG: [RedisListener] 本地无 Video {video_id} 的连接，忽略") # DEBUG
                        
                except Exception as e:
                    logger.error(f"处理 Redis 消息失败: {e}")
    except Exception as e:
        logger.error(f"Redis 监听器异常: {e}")
    finally:
        await client.close()

# ==================== WebSocket 端点 ====================

@router.websocket("/videos/{video_id}")
async def websocket_endpoint(websocket: WebSocket, video_id: int):
    await manager.connect(websocket, video_id)
    try:
        while True:
            # 保持连接
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, video_id)
    except Exception as e:
        logger.error(f"WebSocket 异常: {e}")
        manager.disconnect(websocket, video_id)