"""
视频摘要生成服务

功能：
1. 基于字幕、弹幕、评论生成视频摘要（字幕权重最高）
2. 提取核心知识点
3. 生成简短摘要（50-100字）和详细摘要（200-300字）

要求：
- 足够精炼，不超过本地模型算力
- 字幕权重最高，弹幕和评论作为补充
"""
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.video import Video
from app.models.danmaku import Danmaku
from app.models.comment import Comment
from app.services.video.subtitle_parser import SubtitleParser
from app.services.ai.local_model_service import local_model_service

logger = logging.getLogger(__name__)


class SummaryService:
    """视频摘要生成服务"""
    
    # 权重配置：字幕权重最高
    WEIGHT_SUBTITLE = 0.7  # 字幕权重 70%
    WEIGHT_DANMAKU = 0.2   # 弹幕权重 20%
    WEIGHT_COMMENT = 0.1   # 评论权重 10%
    
    # 内容长度限制（避免超出模型算力）
    MAX_SUBTITLE_LENGTH = 2000  # 字幕最多2000字符
    MAX_DANMAKU_COUNT = 50      # 弹幕最多50条
    MAX_COMMENT_COUNT = 20      # 评论最多20条
    
    async def generate_summary(self, video_id: int) -> Dict[str, Any]:
        """
        生成视频摘要和核心知识点
        
        Args:
            video_id: 视频ID
            
        Returns:
            Dict: {
                "summary_short": str,      # 简短摘要（50-100字）
                "summary_detailed": str,   # 详细摘要（200-300字）
                "knowledge_points": {      # 核心知识点
                    "concepts": List[str],  # 关键概念
                    "steps": List[str],     # 关键步骤
                    "data": List[str],      # 关键数据/统计
                    "opinions": List[str]   # 重要观点/结论
                }
            }
        """
        db = SessionLocal()
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                logger.error(f"视频不存在: video_id={video_id}")
                return {}
            
            # 1. 收集内容（字幕、弹幕、评论）
            content_data = self._collect_content(video, db)
            
            if not content_data.get("subtitle_text") and not content_data.get("danmaku_text") and not content_data.get("comment_text"):
                logger.warning(f"视频 {video_id} 无可用内容，无法生成摘要")
                return {}
            
            # 2. 生成摘要
            summary_result = await self._generate_summary_text(content_data)
            
            # 3. 提取核心知识点
            knowledge_points = await self._extract_knowledge_points(content_data)
            
            # 4. 保存到数据库
            self._save_summary_to_db(db, video, summary_result, knowledge_points)
            
            return {
                "summary_short": summary_result.get("short", ""),
                "summary_detailed": summary_result.get("detailed", ""),
                "knowledge_points": knowledge_points
            }
            
        except Exception as e:
            logger.error(f"生成视频摘要失败 (video_id={video_id}): {e}", exc_info=True)
            return {}
        finally:
            db.close()
    
    def _collect_content(self, video: Video, db: Session) -> Dict[str, Any]:
        """收集字幕、弹幕、评论内容"""
        content_data = {
            "subtitle_text": "",
            "danmaku_text": "",
            "comment_text": "",
            "subtitle_length": 0,
            "danmaku_count": 0,
            "comment_count": 0
        }
        
        # 1. 解析字幕（权重最高）
        if video.subtitle_url:
            try:
                subtitle_path = Path(settings.STORAGE_ROOT) / video.subtitle_url.lstrip('/')
                if not subtitle_path.exists():
                    subtitle_path = Path(settings.UPLOAD_SUBTITLE_DIR) / Path(video.subtitle_url).name
                
                if subtitle_path.exists():
                    subtitles = SubtitleParser.parse_subtitle_file(str(subtitle_path))
                    if subtitles:
                        subtitle_text = SubtitleParser.extract_text_only(subtitles)
                        # 限制长度
                        if len(subtitle_text) > self.MAX_SUBTITLE_LENGTH:
                            subtitle_text = subtitle_text[:self.MAX_SUBTITLE_LENGTH] + "..."
                        content_data["subtitle_text"] = subtitle_text
                        content_data["subtitle_length"] = len(subtitle_text)
            except Exception as e:
                logger.warning(f"解析字幕失败: {e}")
        
        # 2. 收集弹幕（按时间排序，取前N条）
        try:
            danmakus = db.query(Danmaku).filter(
                Danmaku.video_id == video.id,
                Danmaku.is_deleted == False
            ).order_by(Danmaku.video_time).limit(self.MAX_DANMAKU_COUNT).all()
            
            if danmakus:
                danmaku_texts = [d.content for d in danmakus if d.content and len(d.content.strip()) > 0]
                content_data["danmaku_text"] = " ".join(danmaku_texts[:self.MAX_DANMAKU_COUNT])
                content_data["danmaku_count"] = len(danmaku_texts)
        except Exception as e:
            logger.warning(f"收集弹幕失败: {e}")
        
        # 3. 收集评论（按点赞数排序，取前N条）
        try:
            comments = db.query(Comment).filter(
                Comment.video_id == video.id,
                Comment.is_deleted == False
            ).order_by(Comment.like_count.desc()).limit(self.MAX_COMMENT_COUNT).all()
            
            if comments:
                comment_texts = [c.content for c in comments if c.content and len(c.content.strip()) > 0]
                content_data["comment_text"] = " ".join(comment_texts[:self.MAX_COMMENT_COUNT])
                content_data["comment_count"] = len(comment_texts)
        except Exception as e:
            logger.warning(f"收集评论失败: {e}")
        
        return content_data
    
    async def _generate_summary_text(self, content_data: Dict[str, Any]) -> Dict[str, str]:
        """生成摘要文本（简短和详细）"""
        # 构建加权内容（字幕权重最高）
        weighted_content = self._build_weighted_content(content_data)
        
        if not weighted_content:
            return {"short": "", "detailed": ""}
        
        # 限制总长度（避免超出模型算力）
        max_total_length = 2500
        if len(weighted_content) > max_total_length:
            weighted_content = weighted_content[:max_total_length] + "..."
        
        # 生成简短摘要（50-100字）
        short_prompt = f"""请基于以下视频内容，生成一段50-100字的简短摘要，要求：
1. 精炼概括视频核心内容
2. 突出视频主题和要点
3. 语言简洁流畅

视频内容：
{weighted_content}

请只返回摘要文本，不要包含其他说明："""
        
        # 生成详细摘要（200-300字）
        detailed_prompt = f"""请基于以下视频内容，生成一段200-300字的详细摘要，要求：
1. 详细概括视频主要内容
2. 包含关键信息和要点
3. 语言流畅，结构清晰

视频内容：
{weighted_content}

请只返回摘要文本，不要包含其他说明："""
        
        try:
            # 并行生成简短和详细摘要
            short_result = await local_model_service.predict(short_prompt, "comment")
            detailed_result = await local_model_service.predict(detailed_prompt, "comment")
            
            short_summary = ""
            if short_result:
                short_summary = short_result.get("reason", "") or short_result.get("label", "") or ""
                # 清理可能的格式标记
                short_summary = short_summary.replace("```", "").strip()
                # 限制长度
                if len(short_summary) > 150:
                    short_summary = short_summary[:150] + "..."
            
            detailed_summary = ""
            if detailed_result:
                detailed_summary = detailed_result.get("reason", "") or detailed_result.get("label", "") or ""
                # 清理可能的格式标记
                detailed_summary = detailed_summary.replace("```", "").strip()
                # 限制长度
                if len(detailed_summary) > 400:
                    detailed_summary = detailed_summary[:400] + "..."
            
            return {
                "short": short_summary,
                "detailed": detailed_summary
            }
            
        except Exception as e:
            logger.error(f"生成摘要文本失败: {e}")
            return {"short": "", "detailed": ""}
    
    def _build_weighted_content(self, content_data: Dict[str, Any]) -> str:
        """构建加权内容（字幕权重最高）"""
        parts = []
        
        # 字幕内容（权重最高，完整展示）
        if content_data.get("subtitle_text"):
            parts.append(f"【字幕内容】（权重最高）\n{content_data['subtitle_text']}")
        
        # 弹幕内容（补充信息）
        if content_data.get("danmaku_text"):
            parts.append(f"【弹幕内容】（补充信息，共{content_data['danmaku_count']}条）\n{content_data['danmaku_text']}")
        
        # 评论内容（补充信息）
        if content_data.get("comment_text"):
            parts.append(f"【评论内容】（补充信息，共{content_data['comment_count']}条）\n{content_data['comment_text']}")
        
        return "\n\n".join(parts)
    
    async def _extract_knowledge_points(self, content_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """提取核心知识点"""
        weighted_content = self._build_weighted_content(content_data)
        
        if not weighted_content:
            return {
                "concepts": [],
                "steps": [],
                "data": [],
                "opinions": []
            }
        
        # 限制长度
        max_length = 2000
        if len(weighted_content) > max_length:
            weighted_content = weighted_content[:max_length] + "..."
        
        knowledge_prompt = f"""请基于以下视频内容，提取核心知识点，要求：
1. **概念**：提取3-5个关键概念或术语
2. **步骤**：提取3-5个关键步骤或流程（如果有）
3. **数据**：提取3-5个关键数据、统计或事实（如果有）
4. **观点**：提取3-5个重要观点或结论（如果有）

视频内容：
{weighted_content}

请以严格的JSON格式返回（不要包含Markdown标记）：
{{
    "concepts": ["概念1", "概念2"],
    "steps": ["步骤1", "步骤2"],
    "data": ["数据1", "数据2"],
    "opinions": ["观点1", "观点2"]
}}

如果某个类别没有相关内容，请返回空数组 []。"""
        
        try:
            result = await local_model_service.predict(knowledge_prompt, "comment")
            if not result:
                return {
                    "concepts": [],
                    "steps": [],
                    "data": [],
                    "opinions": []
                }
            
            # 尝试从reason中提取JSON
            reason_text = result.get("reason", "")
            if reason_text:
                try:
                    # 清理可能的格式标记
                    clean_text = reason_text.replace("```json", "").replace("```", "").strip()
                    knowledge_points = json.loads(clean_text)
                    # 验证结构
                    if isinstance(knowledge_points, dict):
                        return {
                            "concepts": knowledge_points.get("concepts", [])[:5],
                            "steps": knowledge_points.get("steps", [])[:5],
                            "data": knowledge_points.get("data", [])[:5],
                            "opinions": knowledge_points.get("opinions", [])[:5]
                        }
                except json.JSONDecodeError:
                    pass
            
            # 如果无法解析JSON，返回空结构
            return {
                "concepts": [],
                "steps": [],
                "data": [],
                "opinions": []
            }
            
        except Exception as e:
            logger.error(f"提取核心知识点失败: {e}")
            return {
                "concepts": [],
                "steps": [],
                "data": [],
                "opinions": []
            }
    
    def _save_summary_to_db(
        self,
        db: Session,
        video: Video,
        summary_result: Dict[str, str],
        knowledge_points: Dict[str, List[str]]
    ):
        """保存摘要到数据库（使用独立字段）"""
        try:
            # 使用独立字段保存摘要和知识点
            video.summary_short = summary_result.get("short", "")
            video.summary_detailed = summary_result.get("detailed", "")
            video.knowledge_points = knowledge_points  # JSON字段，直接保存字典
            
            db.commit()
            logger.info(f"视频摘要已保存: video_id={video.id}")
            
        except Exception as e:
            logger.error(f"保存视频摘要失败: {e}")
            db.rollback()


# 全局实例
summary_service = SummaryService()

