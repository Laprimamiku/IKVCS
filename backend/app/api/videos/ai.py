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
from datetime import datetime

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
from app.services.cache.redis_service import redis_service
from app.services.ai.llm_service import llm_service

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
                "conflict_resolved": False,
                "model_info": {"mode": "off", "models": []},
                "prompt_version": None,
                "cost": {"calls": 0, "estimated_tokens": 0},
                "decision_trace_summary": {"rule_hits": 0, "cache_hits": 0, "llm_calls": 0}
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
            "reason": d.ai_reason or "弹幕低分预警",
            "score": d.ai_score,
            "time": d.created_at,
            "source": getattr(d, "ai_source", "unknown"),
            "confidence": getattr(d, "ai_confidence", 0.5)
        })
    for c in comment_risks:
        combined_risks.append({
            "content": c.content,
            "reason": c.ai_reason or "评论低分预警",
            "score": c.ai_score,
            "time": c.created_at,
            "source": getattr(c, "ai_source", "unknown"),
            "confidence": getattr(c, "ai_confidence", 50) / 100.0 if getattr(c, "ai_confidence") else 0.5
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

    # 6. 新增：模型信息和成本统计
    from app.core.model_registry import model_registry
    available_models = model_registry.get_available_models()
    model_info = {
        "mode": llm_service.mode,
        "models": [{"type": k, "name": v.name, "base_url": v.base_url} for k, v in available_models.items()]
    }
    
    # 7. 新增：获取当前激活的Prompt版本
    from app.models.ai_prompt_version import AiPromptVersion
    active_danmaku_prompt = db.query(AiPromptVersion).filter(
        AiPromptVersion.prompt_type == "DANMAKU",
        AiPromptVersion.is_active == True
    ).first()
    active_comment_prompt = db.query(AiPromptVersion).filter(
        AiPromptVersion.prompt_type == "COMMENT", 
        AiPromptVersion.is_active == True
    ).first()
    
    prompt_version = {
        "danmaku": {"id": active_danmaku_prompt.id, "created_at": active_danmaku_prompt.created_at} if active_danmaku_prompt else None,
        "comment": {"id": active_comment_prompt.id, "created_at": active_comment_prompt.created_at} if active_comment_prompt else None
    }
    
    # 8. 新增：成本统计（从cost_tracker获取）
    cost_info = llm_service.cost_tracker.get(video_id, {"calls": 0, "chars": 0})
    
    # 9. 新增：决策轨迹摘要（从Redis获取埋点数据）
    try:
        today = datetime.utcnow().strftime("%Y%m%d")
        metrics_keys = [f"ai:metrics:{today}:rule_hit", f"ai:metrics:{today}:exact_hit", 
                       f"ai:metrics:{today}:cloud_call", f"ai:metrics:{today}:local_call"]
        metrics_values = await redis_service.async_redis.mget(*metrics_keys)
        decision_trace_summary = {
            "rule_hits": int(metrics_values[0] or 0),
            "cache_hits": int(metrics_values[1] or 0), 
            "cloud_calls": int(metrics_values[2] or 0),
            "local_calls": int(metrics_values[3] or 0)
        }
    except Exception:
        decision_trace_summary = {"rule_hits": 0, "cache_hits": 0, "cloud_calls": 0, "local_calls": 0}

    return {
        "sentiment": {
            "positive": positive,
            "neutral": neutral,
            "negative": negative
        },
        "risks": final_risks,
        "summary": summary,
        "expert_results": expert_results,
        "conflict_resolved": False,
        "model_info": model_info,
        "prompt_version": prompt_version,
        "cost": {
            "calls": cost_info["calls"],
            "estimated_tokens": cost_info["chars"] // 4  # 粗略估算token数
        },
        "decision_trace_summary": decision_trace_summary
    }


@router.get("/{video_id}/ai-analysis/items", summary="获取AI分析明细（弹幕/评论）")
async def get_ai_analysis_items(
    video_id: int,
    item_type: Optional[str] = None,  # danmaku/comment
    filter: Optional[str] = None,     # risk/highlight
    score_lt: Optional[int] = None,
    score_gt: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 鉴权：作者或管理员
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    if video.uploader_id != current_user.id and current_user.role != "admin":
        raise ForbiddenException("无权查看此报告")

    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    items = []
    total = 0

    def apply_filters(query, model):
        nonlocal total
        if filter == "risk":
            query = query.filter(model.ai_score < 40)
        if filter == "highlight":
            # 弹幕用 is_highlight / 评论用高分近似
            if hasattr(model, "is_highlight"):
                query = query.filter(model.is_highlight == True)
            else:
                query = query.filter(model.ai_score >= 80)
        if score_lt is not None:
            query = query.filter(model.ai_score < score_lt)
        if score_gt is not None:
            query = query.filter(model.ai_score > score_gt)
        total = query.count()
        return (
            query.order_by(model.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

    # danmaku
    if item_type in (None, "danmaku"):
        q = db.query(Danmaku).filter(Danmaku.video_id == video_id)
        danmaku_list = apply_filters(q, Danmaku)
        for d in danmaku_list:
            items.append({
                "id": d.id,
                "type": "danmaku",
                "content": d.content,
                "score": d.ai_score,
                "ai_category": getattr(d, "ai_category", None),
                "ai_reason": getattr(d, "ai_reason", None),
                "ai_confidence": getattr(d, "ai_confidence", 0.5),
                "ai_source": getattr(d, "ai_source", None),
                "ai_model": getattr(d, "ai_model", None),
                "ai_prompt_version_id": getattr(d, "ai_prompt_version_id", None),
                "is_highlight": getattr(d, "is_highlight", False),
                "created_at": d.created_at,
            })

    # comment
    if item_type in (None, "comment"):
        q = db.query(Comment).filter(Comment.video_id == video_id)
        comment_list = apply_filters(q, Comment)
        for c in comment_list:
            items.append({
                "id": c.id,
                "type": "comment",
                "content": c.content,
                "score": c.ai_score,
                "ai_label": getattr(c, "ai_label", None),
                "ai_reason": getattr(c, "ai_reason", None),
                "ai_confidence": getattr(c, "ai_confidence", 50) / 100.0 if getattr(c, "ai_confidence") else 0.5,
                "ai_source": getattr(c, "ai_source", None),
                "ai_model": getattr(c, "ai_model", None),
                "ai_prompt_version_id": getattr(c, "ai_prompt_version_id", None),
                "is_highlight": getattr(c, "ai_score", 0) >= 80,
                "created_at": c.created_at,
            })

    # 合并后按时间排序
    items.sort(key=lambda x: x["created_at"], reverse=True)
    # 截断到当前分页大小（因为两类合并后可能超过）
    items = items[:page_size]

    return success_response(
        data={
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.post("/{video_id}/ai-analysis/recompute", summary="触发AI分析重算（异步占位）")
async def trigger_ai_analysis_recompute(
    video_id: int,
    scope: str = "recent",  # recent/all
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    if video.uploader_id != current_user.id and current_user.role != "admin":
        raise ForbiddenException("无权触发重算")

    redis_client = redis_service.redis
    progress_key = f"analysis:progress:{video_id}"
    payload = {
        "status": "queued",
        "progress": 0,
        "scope": scope,
        "limit": limit,
        "message": "重算任务已排队（占位，需后台任务实现）"
    }
    try:
        redis_client.setex(progress_key, 600, json.dumps(payload, default=str))
    except Exception as e:
        logger.error(f"设置重算进度失败: {e}")
    return success_response(data=payload, message="已排队重算（占位实现）")


@router.post("/{video_id}/ai-analysis/jury", summary="手动触发多智能体复核（仅上传者/管理员）")
async def trigger_ai_analysis_jury(
    video_id: int,
    scope: str = "recent",  # recent/all
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    手动触发多智能体复核，默认仅处理最近数据，上传者/管理员可用。
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    if video.uploader_id != current_user.id and current_user.role != "admin":
        raise ForbiddenException("无权触发多智能体复核")

    # 获取弹幕与评论
    danmaku_query = (
        db.query(Danmaku)
        .filter(Danmaku.video_id == video_id, Danmaku.is_deleted == False)  # noqa: E712
        .order_by(Danmaku.created_at.desc())
    )
    comment_query = (
        db.query(Comment)
        .filter(Comment.video_id == video_id)
        .order_by(Comment.created_at.desc())
    )
    if scope != "all":
        danmakus = danmaku_query.limit(limit).all()
        comments = comment_query.limit(limit).all()
    else:
        danmakus = danmaku_query.all()
        comments = comment_query.all()

    processed = 0
    errors = 0

    async def _apply_result_for_danmaku(d):
        nonlocal processed, errors
        try:
            result = await llm_service.analyze_content(d.content, "danmaku", force_jury=True)
            d.ai_score = result.get("score", 60)
            d.ai_category = result.get("category", "普通")
            d.ai_reason = result.get("reason")
            d.ai_confidence = result.get("confidence", 0.5)
            d.ai_source = result.get("source")
            d.ai_prompt_version_id = result.get("prompt_version_id")
            d.ai_model = result.get("model_name")
            trace = result.get("decision_trace")
            d.ai_trace = json.dumps(trace, ensure_ascii=False) if trace else None
            d.is_highlight = result.get("is_highlight", False) or d.ai_score >= 90
            processed += 1
        except Exception as e:
            logger.error(f"Jury 复核弹幕失败 id={d.id}: {e}")
            errors += 1

    async def _apply_result_for_comment(c):
        nonlocal processed, errors
        try:
            result = await llm_service.analyze_content(c.content, "comment", force_jury=True)
            c.ai_score = result.get("score", 60)
            c.ai_label = result.get("label", "普通")
            c.ai_reason = result.get("reason")
            conf = result.get("confidence", 0.5)
            c.ai_confidence = int(conf * 100) if conf is not None else None
            c.ai_source = result.get("source")
            c.ai_prompt_version_id = result.get("prompt_version_id")
            c.ai_model = result.get("model_name")
            trace = result.get("decision_trace")
            c.ai_trace = json.dumps(trace, ensure_ascii=False) if trace else None
            processed += 1
        except Exception as e:
            logger.error(f"Jury 复核评论失败 id={c.id}: {e}")
            errors += 1

    # 顺序执行，避免占用过多资源
    for d in danmakus:
        await _apply_result_for_danmaku(d)
        db.commit()
    for c in comments:
        await _apply_result_for_comment(c)
        db.commit()

    return success_response(
        data={
            "processed": processed,
            "errors": errors,
            "danmaku_total": len(danmakus),
            "comment_total": len(comments),
            "scope": scope,
            "limit": limit,
        },
        message="已完成多智能体复核"
    )


@router.get("/{video_id}/ai-analysis/progress", summary="查询AI分析重算进度")
async def get_ai_analysis_progress(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ResourceNotFoundException(resource="视频", resource_id=video_id)
    if video.uploader_id != current_user.id and current_user.role != "admin":
        raise ForbiddenException("无权查看进度")

    progress_key = f"analysis:progress:{video_id}"
    try:
        val = redis_service.redis.get(progress_key)
        if not val:
            return success_response(
                data={"status": "idle", "progress": 0, "message": "未找到进行中的任务"}
            )
        return success_response(data=json.loads(val))
    except Exception as e:
        logger.error(f"查询重算进度失败: {e}")
        return success_response(
            data={"status": "unknown", "progress": 0, "message": "查询失败"}
        )


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
