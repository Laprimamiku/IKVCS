"""
视频 AI 功能 API

功能：
1. 生成视频大纲
2. 获取视频AI分析报告
3. 生成视频摘要
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, case, desc

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ResourceNotFoundException, ForbiddenException, ValidationException
from app.core.response import success_response
from app.models.user import User
from app.models.video import Video
from app.models.danmaku import Danmaku
from app.models.comment import Comment

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{video_id}/outline/generate", response_model=dict)
async def generate_video_outline(
    video_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    手动触发生成视频大纲（需要登录，仅上传者可操作）
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    if video.uploader_id != current_user.id:
        raise ForbiddenException("只有视频上传者可以生成大纲")
    
    if not video.subtitle_url:
        raise ValidationException(message="视频没有字幕文件，无法生成大纲")
    
    # 异步生成大纲
    from app.services.video.outline_service import OutlineService
    
    async def generate_and_save():
        # 使用新的数据库会话保存
        from app.core.database import SessionLocal
        db_session = SessionLocal()
        try:
            logger.info(f"[视频 {video_id}] 开始生成大纲...")
            
            # 直接删除原有大纲（不保留）
            video_obj = db_session.query(Video).filter(Video.id == video_id).first()
            if video_obj:
                video_obj.outline = None  # 直接删除
                db_session.commit()
            
            # 生成新大纲（不使用进度回调）
            outline = await OutlineService.extract_outline(
                video_id, 
                video.subtitle_url,
                progress_callback=None  # 不使用进度回调
            )
            
            # 保存新大纲（仅当生成成功时保存，失败则不保存）
            video_obj = db_session.query(Video).filter(Video.id == video_id).first()
            if video_obj:
                if outline and len(outline) > 0:
                    # 生成成功，保存新大纲
                    video_obj.outline = json.dumps(outline, ensure_ascii=False)
                    db_session.commit()
                    logger.info(f"[视频 {video_id}] 视频大纲已生成完毕，共 {len(outline)} 个章节")
                else:
                    # 生成失败，不保存（保持为 None）
                    db_session.commit()
                    logger.error(f"[视频 {video_id}] 视频大纲生成出错：生成结果为空")
        except Exception as e:
            logger.error(f"[视频 {video_id}] 视频大纲生成出错：{str(e)}", exc_info=True)
            # 确保大纲被删除
            try:
                video_obj = db_session.query(Video).filter(Video.id == video_id).first()
                if video_obj:
                    video_obj.outline = None
                    db_session.commit()
            except:
                pass
        finally:
            db_session.close()
    
    background_tasks.add_task(generate_and_save)
    
    return success_response(
        data={},
        message="大纲生成任务已启动，请稍后查询"
    )


@router.get("/{video_id}/ai-analysis", summary="获取视频AI分析报告")
async def get_video_ai_analysis(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. 鉴权：只有作者能看
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    if video.uploader_id != current_user.id and current_user.role != "admin":
        raise ForbiddenException("无权查看此报告")

    # 2. 检查数据量 (评论 + 弹幕)
    comment_count = db.query(Comment).filter(Comment.video_id == video_id).count()
    danmaku_count = db.query(Danmaku).filter(Danmaku.video_id == video_id).count()
    total_count = comment_count + danmaku_count

    if total_count == 0:
        return success_response(
            data={
                "sentiment": {"positive": 0, "neutral": 0, "negative": 0},
                "risks": [],
                "summary": "暂无数据：该视频尚未产生足够的互动（评论/弹幕），无法进行AI智能分析。",
                "expert_results": [],
                "conflict_resolved": False
            },
            message="暂无分析数据"
        )

    # 3. 统计情感分布 (基于 ai_score)
    # score < 40: 负面/争议
    # 40 <= score <= 75: 中性/普通
    # score > 75: 正面/优质
    
    # 3.1 弹幕统计
    danmaku_stats = db.query(
        func.sum(case((Danmaku.ai_score < 40, 1), else_=0)).label("negative"),
        func.sum(case((Danmaku.ai_score.between(40, 75), 1), else_=0)).label("neutral"),
        func.sum(case((Danmaku.ai_score > 75, 1), else_=0)).label("positive")
    ).filter(Danmaku.video_id == video_id).first()

    # 3.2 评论统计
    comment_stats = db.query(
        func.sum(case((Comment.ai_score < 40, 1), else_=0)).label("negative"),
        func.sum(case((Comment.ai_score.between(40, 75), 1), else_=0)).label("neutral"),
        func.sum(case((Comment.ai_score > 75, 1), else_=0)).label("positive")
    ).filter(Comment.video_id == video_id).first()

    # 合并统计
    positive = (danmaku_stats.positive or 0) + (comment_stats.positive or 0)
    neutral = (danmaku_stats.neutral or 0) + (comment_stats.neutral or 0)
    negative = (danmaku_stats.negative or 0) + (comment_stats.negative or 0)

    # 4. 获取风险/高亮内容 (从两张表获取，合并排序)
    danmaku_risks = db.query(Danmaku).filter(
        Danmaku.video_id == video_id,
        Danmaku.ai_score < 30
    ).order_by(desc(Danmaku.created_at)).limit(5).all()

    comment_risks = db.query(Comment).filter(
        Comment.video_id == video_id,
        Comment.ai_score < 30
    ).order_by(desc(Comment.created_at)).limit(5).all()

    # 合并并按时间倒序
    combined_risks = []
    for d in danmaku_risks:
        combined_risks.append({
            "content": d.content,
            "reason": "弹幕低分预警",
            "score": d.ai_score,
            "time": d.created_at
        })
    for c in comment_risks:
        combined_risks.append({
            "content": c.content,
            "reason": "评论低分预警",
            "score": c.ai_score,
            "time": c.created_at
        })
    
    # 再次排序取前5
    combined_risks.sort(key=lambda x: x['time'], reverse=True)
    final_risks = combined_risks[:5]

    # 5. 动态生成陪审团数据 (模拟逻辑)
    # 基于情感分布动态调整专家评分
    
    # Meme Expert: 正面内容越多，评分越高
    meme_score = 60 + min(35, int((positive / total_count) * 40)) if total_count > 0 else 80
    
    # Emotion Expert: 负面内容越少，评分越高
    emotion_score = 100 - min(40, int((negative / total_count) * 100)) if total_count > 0 else 90
    
    # Legal Expert: 风险内容越多，评分越低
    risk_count = len(combined_risks)
    legal_score = max(50, 100 - risk_count * 10)

    expert_results = [
        {"agent": "Meme Expert", "score": meme_score, "opinion": "社区梗与互动氛围检测中...", "safe": True},
        {"agent": "Emotion Expert", "score": emotion_score, "opinion": "情感倾向与对立情绪分析中...", "safe": True},
        {"agent": "Legal Expert", "score": legal_score, "opinion": "合规性与潜在风险扫描中...", "safe": legal_score > 60}
    ]
    
    sentiment_desc = "积极" if positive > negative else "需关注"
    summary = f"基于 {total_count} 条互动（{comment_count}条评论，{danmaku_count}条弹幕）分析，整体氛围{sentiment_desc}。发现 {len(combined_risks)} 条潜在风险内容。"

    return {
        "sentiment": {
            "positive": positive,
            "neutral": neutral,
            "negative": negative
        },
        "risks": final_risks,
        "summary": summary,
        "expert_results": expert_results,
        "conflict_resolved": False
    }


@router.post("/{video_id}/summary", summary="生成视频摘要")
async def generate_video_summary(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    生成视频摘要和核心知识点
    
    基于字幕（权重70%）、弹幕（权重20%）、评论（权重10%）生成摘要
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    
    # 权限检查：只有上传者或管理员可以触发生成
    if current_user and video.uploader_id != current_user.id and current_user.role != "admin":
        raise ForbiddenException("只有视频上传者或管理员可以生成摘要")
    
    # 异步生成摘要（避免阻塞）
    from app.services.video.summary_service import summary_service
    background_tasks.add_task(summary_service.generate_summary, video_id)
    
    return success_response(
        data={},
        message="摘要生成任务已启动，请稍后查询"
    )

