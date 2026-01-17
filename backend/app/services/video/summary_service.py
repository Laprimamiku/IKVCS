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
import re
from typing import Dict, Any, Optional, List
from pathlib import Path
from sqlalchemy.orm import Session
import httpx

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.video import Video
from app.models.danmaku import Danmaku
from app.models.comment import Comment
from app.services.video.subtitle_parser import SubtitleParser

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

    def _get_cloud_summary_config(self) -> Optional[Dict[str, str]]:
        api_key = getattr(settings, "SUMMARY_API_KEY", "") or settings.LLM_API_KEY
        base_url = (getattr(settings, "SUMMARY_BASE_URL", "") or settings.LLM_BASE_URL).rstrip("/")
        model = getattr(settings, "SUMMARY_MODEL", "") or settings.LLM_MODEL
        if not api_key or not base_url or not model:
            return None
        return {"api_key": api_key, "base_url": base_url, "model": model}

    def _get_local_summary_config(self) -> Optional[Dict[str, str]]:
        base_url = (settings.LOCAL_LLM_BASE_URL or "").rstrip("/")
        model = settings.LOCAL_LLM_MODEL
        if not base_url or not model:
            return None
        return {"base_url": base_url, "model": model}

    async def _call_cloud_llm(self, prompt: str, max_tokens: int) -> Optional[str]:
        cfg = self._get_cloud_summary_config()
        if not cfg:
            return None
        headers = {
            "Authorization": f"Bearer {cfg['api_key']}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": cfg["model"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{cfg['base_url']}/chat/completions",
                    json=payload,
                    headers=headers,
                )
            if resp.status_code != 200:
                logger.warning("Summary cloud call failed: %s - %s", resp.status_code, resp.text)
                return None
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Summary cloud call error: %s", exc)
            return None

    async def _call_local_llm(self, prompt: str, max_tokens: int) -> Optional[str]:
        cfg = self._get_local_summary_config()
        if not cfg:
            return None
        payload = {
            "model": cfg["model"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": max_tokens,
            "stream": False,
        }
        timeout = max(float(getattr(settings, "LOCAL_LLM_TIMEOUT", 60.0) or 60.0), 60.0)
        try:
            async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
                resp = await client.post(
                    f"{cfg['base_url']}/chat/completions",
                    json=payload,
                )
            if resp.status_code != 200:
                logger.warning("Summary local call failed: %s - %s", resp.status_code, resp.text)
                return None
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Summary local call error: %s", exc)
            return None

    async def _call_llm_text(self, prompt: str, max_tokens: int, prefer_cloud: bool = True) -> Optional[str]:
        llm_mode = getattr(settings, "LLM_MODE", "hybrid").lower()
        use_cloud = llm_mode in ("cloud_only", "hybrid")
        use_local = llm_mode in ("local_only", "hybrid")
        if llm_mode == "off":
            return None

        if prefer_cloud:
            if use_cloud:
                result = await self._call_cloud_llm(prompt, max_tokens)
                if result:
                    return result
            if use_local:
                return await self._call_local_llm(prompt, max_tokens)
        else:
            if use_local:
                result = await self._call_local_llm(prompt, max_tokens)
                if result:
                    return result
            if use_cloud:
                return await self._call_cloud_llm(prompt, max_tokens)
        return None

    def _clean_text(self, text: Optional[str]) -> str:
        if not text:
            return ""
        clean = text.strip()
        clean = re.sub(r"^```[a-zA-Z]*\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
        return clean.strip().strip('"')

    def _extract_json_from_text(self, text: Optional[str]) -> Optional[Dict[str, Any]]:
        if not text:
            return None
        clean = text.strip()
        # Try fenced blocks first
        for match in re.finditer(r"```(?:json)?\s*([\s\S]*?)\s*```", clean, flags=re.IGNORECASE):
            candidate = (match.group(1) or "").strip()
            if not candidate:
                continue
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

        clean = re.sub(r"```json\s*|\s*```", "", clean, flags=re.IGNORECASE).strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            pass

        start = clean.find("{")
        end = clean.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(clean[start : end + 1])
            except json.JSONDecodeError:
                return None
        return None
    
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
            # Local-first to save cost, cloud fallback for weak/empty outputs.
            short_text = await self._call_llm_text(short_prompt, max_tokens=256, prefer_cloud=False)
            if not short_text or len(self._clean_text(short_text)) < 20:
                short_text = await self._call_llm_text(short_prompt, max_tokens=256, prefer_cloud=True)

            detailed_text = await self._call_llm_text(detailed_prompt, max_tokens=512, prefer_cloud=False)
            if not detailed_text or len(self._clean_text(detailed_text)) < 40:
                detailed_text = await self._call_llm_text(detailed_prompt, max_tokens=512, prefer_cloud=True)

            short_summary = self._clean_text(short_text)
            if len(short_summary) > 150:
                short_summary = short_summary[:150] + "..."

            detailed_summary = self._clean_text(detailed_text)
            if len(detailed_summary) > 400:
                detailed_summary = detailed_summary[:400] + "..."

            return {"short": short_summary, "detailed": detailed_summary}
            
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
            response_text = await self._call_llm_text(knowledge_prompt, max_tokens=512, prefer_cloud=False)
            knowledge_points = self._extract_json_from_text(response_text)
            if not knowledge_points:
                response_text = await self._call_llm_text(knowledge_prompt, max_tokens=512, prefer_cloud=True)
                knowledge_points = self._extract_json_from_text(response_text)
            if isinstance(knowledge_points, dict):
                return {
                    "concepts": knowledge_points.get("concepts", [])[:5],
                    "steps": knowledge_points.get("steps", [])[:5],
                    "data": knowledge_points.get("data", [])[:5],
                    "opinions": knowledge_points.get("opinions", [])[:5]
                }
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
    
    async def _generate_structured_summary(self, content_data: Dict[str, Any]) -> Dict[str, str]:
        """
        生成结构化摘要（问题背景、研究方法、主要发现、最终结论）
        
        不保存到数据库，仅用于实时显示
        """
        weighted_content = self._build_weighted_content(content_data)
        
        if not weighted_content.strip():
            return {
                "problem_background": "",
                "research_methods": "",
                "main_findings": "",
                "conclusions": ""
            }
        
        prompt = f"""请基于以下视频内容，生成结构化摘要，包含以下四个部分：

1. **问题背景**：视频要解决的核心问题或讨论的背景
2. **研究方法**：视频中采用的研究方法、分析思路或技术手段
3. **主要发现**：视频中发现的重要信息、数据或观点
4. **最终结论**：视频得出的结论或总结

请以JSON格式返回，格式如下：
{{
    "problem_background": "问题背景内容",
    "research_methods": "研究方法内容",
    "main_findings": "主要发现内容",
    "conclusions": "最终结论内容"
}}

**重要：只返回JSON对象，不要包含任何Markdown标记或其他说明文字。**

视频内容：
{weighted_content}
"""
        
        try:
            response_text = await self._call_llm_text(prompt, max_tokens=1024, prefer_cloud=False)
            if not response_text or len(self._clean_text(response_text)) < 50:
                response_text = await self._call_llm_text(prompt, max_tokens=1024, prefer_cloud=True)
            
            # 尝试解析JSON
            cleaned_text = self._clean_text(response_text)
            try:
                # 移除可能的Markdown代码块标记
                if "```json" in cleaned_text:
                    cleaned_text = cleaned_text.split("```json")[1].split("```")[0].strip()
                elif "```" in cleaned_text:
                    cleaned_text = cleaned_text.split("```")[1].split("```")[0].strip()
                
                parsed = json.loads(cleaned_text)
                return {
                    "problem_background": parsed.get("problem_background", "").strip(),
                    "research_methods": parsed.get("research_methods", "").strip(),
                    "main_findings": parsed.get("main_findings", "").strip(),
                    "conclusions": parsed.get("conclusions", "").strip()
                }
            except json.JSONDecodeError:
                # 如果JSON解析失败，尝试从文本中提取
                return self._extract_structured_from_text(cleaned_text)
        except Exception as e:
            logger.error(f"生成结构化摘要失败: {e}")
            return {
                "problem_background": "",
                "research_methods": "",
                "main_findings": "",
                "conclusions": ""
            }
    
    def _extract_structured_from_text(self, text: str) -> Dict[str, str]:
        """从文本中提取结构化信息"""
        result = {
            "problem_background": "",
            "research_methods": "",
            "main_findings": "",
            "conclusions": ""
        }
        
        # 尝试匹配各个部分
        patterns = {
            "problem_background": [r"问题背景[：:]\s*(.+?)(?=\n|研究方法|主要发现|最终结论|$)", r"背景[：:]\s*(.+?)(?=\n|方法|发现|结论|$)"],
            "research_methods": [r"研究方法[：:]\s*(.+?)(?=\n|主要发现|最终结论|问题背景|$)", r"方法[：:]\s*(.+?)(?=\n|发现|结论|背景|$)"],
            "main_findings": [r"主要发现[：:]\s*(.+?)(?=\n|最终结论|问题背景|研究方法|$)", r"发现[：:]\s*(.+?)(?=\n|结论|背景|方法|$)"],
            "conclusions": [r"最终结论[：:]\s*(.+?)(?=\n|问题背景|研究方法|主要发现|$)", r"结论[：:]\s*(.+?)(?=\n|背景|方法|发现|$)"]
        }
        
        for key, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if match:
                    result[key] = match.group(1).strip()
                    break
        
        return result


# 全局实例
summary_service = SummaryService()
