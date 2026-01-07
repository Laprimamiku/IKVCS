import asyncio
import sys
import os

sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.interaction import UserLike
from app.models.video import Video
from app.models.comment import Comment
from app.services.cache.redis_service import redis_service

async def sync_likes_from_redis_to_db():
    print("🔄 开始同步点赞数据 (Dirty Set 模式)...")
    db = SessionLocal()
    redis = redis_service.async_redis 
    
    try:
        # 1. 获取所有发生过变化的 ID (脏数据)
        dirty_targets = await redis.smembers("likes:dirty")
        print(f"🔍 发现 {len(dirty_targets)} 个待同步目标")
        
        for item in dirty_targets:
            # item 格式: "video:15"
            try:
                target_type, target_id_str = item.split(":")
                target_id = int(target_id_str)
            except ValueError:
                continue

            # 构造 Redis Key: "likes:video:15"
            redis_key = f"likes:{target_type}:{target_id}"
            
            # 获取 Redis 中的最新状态
            # 注意：如果 Key 不存在(被删完了)，smembers 返回空集合，这是正确的
            redis_user_ids = await redis.smembers(redis_key)
            
            valid_user_ids = set()
            for uid in redis_user_ids:
                try:
                    valid_user_ids.add(int(uid))
                except ValueError:
                    continue
            
            # Redis 为准的总数
            current_total_count = len(valid_user_ids)

            # --- 同步 user_likes 表 ---
            # 获取 DB 数据
            db_likes = db.query(UserLike.user_id).filter(
                UserLike.target_type == target_type,
                UserLike.target_id == target_id
            ).all()
            db_user_ids = {r[0] for r in db_likes}
            
            to_add = valid_user_ids - db_user_ids
            to_remove = db_user_ids - valid_user_ids
            
            if to_add:
                new_objects = [
                    UserLike(user_id=uid, target_type=target_type, target_id=target_id)
                    for uid in to_add
                ]
                db.bulk_save_objects(new_objects)
            
            if to_remove:
                db.query(UserLike).filter(
                    UserLike.target_type == target_type,
                    UserLike.target_id == target_id,
                    UserLike.user_id.in_(to_remove)
                ).delete(synchronize_session=False)

            # --- 同步主表统计数 ---
            if target_type == "video":
                # 这里会执行，即使 count 是 0
                db.query(Video).filter(Video.id == target_id).update(
                    {"like_count": current_total_count}
                )
                print(f"[Video {target_id}] 数据库更新为: {current_total_count}")
                
            elif target_type == "comment":
                db.query(Comment).filter(Comment.id == target_id).update(
                    {"like_count": current_total_count}
                )
        
        # 2. 清理脏数据标记 (只删除我们处理过的)
        # 生产环境建议用 srem 逐个删，这里为了简单直接删 key
        if dirty_targets:
            await redis.delete("likes:dirty")

        db.commit()
        print("同步完成")
        
    except Exception as e:
        print(f"同步失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(sync_likes_from_redis_to_db())
