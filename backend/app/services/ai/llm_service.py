"""
LLM 智能分析服务
需求：8.1-8.5, 10.1-10.4, 20.1-20.4

功能：
提供弹幕和评论的智能评分与分类
提供异步后台任务处理方法，直接更新数据库
规则预过滤 + 提示工程模板 + 结果结构化解析
"""
import httpx
import json
import logging
import asyncio
from typing import Dict, Any, Optional

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.danmaku import Danmaku
from app.models.comment import Comment
# 引入新创建的 Prompt 模板
from app.services.ai.prompts import DANMAKU_SYSTEM_PROMPT, COMMENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_BASE_URL
        self.model = settings.LLM_MODEL
        self.timeout = 30.0
        
        # 默认兜底响应
        self.default_response = {
            "score": 60,
            "category": "普通",
            "label": "普通",
            "reason": "默认处理",
            "is_highlight": False,
            "is_inappropriate": False
        }

    async def analyze_content(self, content: str, content_type: str) -> Dict[str, Any]:
        """
        核心分析流程：规则过滤 -> 构建Prompt -> 调用API -> 解析结果
        """
        # 1. 规则预过滤 (Rule-based Filtering)
        # 针对极短或明显无意义的内容，不消耗 LLM Token
        pre_check = self._rule_based_filter(content, content_type)
        if pre_check:
            logger.info(f"Rule hit for content '{content}': {pre_check['reason']}")
            return pre_check

        # 2. 构建 Prompt (使用模板)
        messages = self._build_prompt(content, content_type)
        
        # 3. 调用 API
        response_text = await self._call_llm_api(messages)
        if not response_text:
            return self.default_response
            
        # 4. 解析结果
        return self._parse_response(response_text, content_type)

    def _rule_based_filter(self, content: str, content_type: str) -> Optional[Dict]:
        """
        基于规则的低成本过滤器
        """
        if not content:
            return self.default_response

        # 常见无意义短语库
        low_value_keywords = ["666", "111", "233", "哈哈", "打卡", "第一", "前排", "来了"]
        
        # 规则1: 纯数字或极短且在词库中 -> 判为普通
        clean_content = content.strip()
        if len(clean_content) < 4:
            if clean_content.isdigit() or any(k in clean_content for k in low_value_keywords):
                return {
                    **self.default_response,
                    "score": 65,
                    "category": "情绪表达",
                    "reason": "规则命中: 常见短弹幕",
                    "is_highlight": False
                }
        
        return None

    def _build_prompt(self, content: str, content_type: str) -> list:
        """
        加载 prompts.py 中的模板
        """
        if content_type == "danmaku":
            system_content = DANMAKU_SYSTEM_PROMPT
        else:
            system_content = COMMENT_SYSTEM_PROMPT

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"输入内容: {content}"}
        ]
    
    async def _call_llm_api(self, messages: list) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,  # 降低温度，让 JSON 输出更稳定
            "max_tokens": 300,   # 限制输出长度
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code != 200:
                    logger.error(f"LLM API Error: {response.status_code} - {response.text}")
                    return None
                    
                data = response.json()
                return data['choices'][0]['message']['content']
                
        except Exception as e:
            logger.error(f"LLM API Call Failed: {str(e)}")
            return None
    
    def _parse_response(self, response_text: str, content_type: str) -> Dict[str, Any]:
        try:
            # 清理 Markdown 标记
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_text)
            
            result = self.default_response.copy()
            result.update(data)
            
            # 类型安全转换
            result['category'] = str(result.get('category', '普通'))
            result['label'] = str(result.get('label', '普通'))
            
            return result
            
        except json.JSONDecodeError:
            logger.warning(f"JSON Parse Error. Raw: {response_text}")
            return self.default_response

    # ==================== 异步任务处理 ====================

    async def process_danmaku_task(self, danmaku_id: int):
        db = SessionLocal()
        try:
            danmaku = db.query(Danmaku).filter(Danmaku.id == danmaku_id).first()
            if not danmaku: return

            result = await self.analyze_content(danmaku.content, "danmaku")
            
            # 更新字段
            danmaku.ai_score = result.get('score', 60)
            danmaku.ai_category = result.get('category', '普通')
            
            # 处理高亮逻辑：AI 认为高亮 OR 分数极高
            # 注意：数据库目前只有 is_highlight 字段，没有 reason 字段，reason 仅记日志
            danmaku.is_highlight = result.get('is_highlight', False) or danmaku.ai_score >= 90
            
            # 记录详细日志用于调试 Prompt (CoT 的体现)
            if 'reason' in result:
                logger.info(f"[AI Analysis] Danmaku {danmaku_id}: Reason='{result['reason']}'")
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error processing danmaku {danmaku_id}: {e}")
            db.rollback()
        finally:
            db.close()

    async def process_comment_task(self, comment_id: int):
        db = SessionLocal()
        try:
            comment = db.query(Comment).filter(Comment.id == comment_id).first()
            if not comment: return

            result = await self.analyze_content(comment.content, "comment")
            
            comment.ai_score = result.get('score', 60)
            comment.ai_label = result.get('label', '普通')
            
            if 'reason' in result:
                logger.info(f"[AI Analysis] Comment {comment_id}: Reason='{result['reason']}'")
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error processing comment {comment_id}: {e}")
            db.rollback()
        finally:
            db.close()

# 全局实例
llm_service = LLMService()