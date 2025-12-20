# backend/app/services/ai/self_correction_service.py
"""
反馈式自我纠错服务

功能：
1. 分析管理员修正记录，识别错误模式
2. 使用元Prompt生成优化建议
3. 更新System Prompt（记录版本历史）
4. 验证优化效果

需求：深化方向三 - 进化层
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.ai_correction import AICorrection, AIPromptVersion
from app.services.ai.llm_service import llm_service

logger = logging.getLogger(__name__)


class SelfCorrectionService:
    """反馈式自我纠错服务"""
    
    def __init__(self):
        # 从配置读取最小样本数量
        self.min_samples = getattr(settings, "SELF_CORRECTION_MIN_SAMPLES", 10)
    
    async def analyze_errors(self, days: int = 7, content_type: Optional[str] = None) -> Dict[str, Any]:
        """
        分析最近N天的错误案例
        
        参数：
        - days: 分析最近多少天的数据
        - content_type: 内容类型过滤（"comment"/"danmaku"，None表示全部）
        
        返回：
        {
            "error_patterns": [...],
            "suggestions": "...",
            "sample_count": 10,
            "content_type": "comment"
        }
        """
        db = SessionLocal()
        try:
            # 1. 查询修正记录
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = db.query(AICorrection).filter(
                AICorrection.created_at >= cutoff_date
            )
            
            # 按内容类型过滤
            if content_type:
                query = query.filter(AICorrection.content_type == content_type)
            
            corrections = query.order_by(AICorrection.created_at.desc()).all()
            
            if len(corrections) < self.min_samples:
                return {
                    "error": f"样本数量不足（需要至少 {self.min_samples} 个，当前 {len(corrections)} 个）",
                    "sample_count": len(corrections),
                    "content_type": content_type
                }
            
            logger.info(f"开始分析 {len(corrections)} 个修正案例（最近{days}天，类型：{content_type or '全部'}）")
            
            # 2. 调用元Prompt分析错误模式
            error_patterns = await self._analyze_error_patterns(corrections)
            
            # 3. 生成优化建议
            suggestions = await self._generate_suggestions(error_patterns, corrections, content_type)
            
            return {
                "error_patterns": error_patterns,
                "suggestions": suggestions,
                "sample_count": len(corrections),
                "content_type": content_type,
                "analysis_date": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"错误分析失败: {e}")
            return {
                "error": f"分析过程出错: {str(e)}",
                "sample_count": 0
            }
        finally:
            db.close()
    
    async def _analyze_error_patterns(self, corrections: List[AICorrection]) -> Dict[str, Any]:
        """使用元Prompt分析错误模式"""
        # 格式化修正案例（最多取20个，避免Prompt过长）
        cases_text = self._format_corrections(corrections[:20])
        
        meta_prompt = f"""你是AI系统优化专家。以下是最近的 {len(corrections)} 个误判案例：

{cases_text}

请分析这些错误的共同模式：

1. **错误类型分析**：这些错误主要属于哪些类型？（如：情感识别错误、梗理解错误、合规判断错误等）
2. **共同特征**：这些被误判的内容有什么共同特征？
3. **当前Prompt的弱点**：基于这些错误，当前System Prompt可能存在哪些问题？
4. **高频错误**：哪些类型的错误出现频率最高？

请以JSON格式返回分析结果：
{{
    "error_types": ["错误类型1", "错误类型2"],
    "common_features": ["特征1", "特征2"],
    "prompt_weaknesses": ["弱点1", "弱点2"],
    "high_frequency_errors": ["高频错误1", "高频错误2"],
    "analysis_summary": "总体分析总结"
}}"""
        
        messages = [
            {"role": "system", "content": "你是AI系统优化专家，擅长分析错误模式并识别系统弱点。"},
            {"role": "user", "content": meta_prompt}
        ]
        
        response_text = await llm_service._call_llm_api(messages)
        if not response_text:
            logger.warning("错误模式分析返回为空")
            return {}
        
        try:
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            patterns = json.loads(clean_text)
            logger.info(f"错误模式分析完成: {patterns.get('analysis_summary', '无总结')}")
            return patterns
        except json.JSONDecodeError as e:
            logger.warning(f"错误模式分析返回格式错误: {e}")
            return {"error": "分析结果解析失败"}
    
    async def _generate_suggestions(
        self, 
        error_patterns: Dict[str, Any], 
        corrections: List[AICorrection],
        content_type: Optional[str]
    ) -> str:
        """生成优化建议"""
        if not error_patterns or "error" in error_patterns:
            return "错误模式分析失败，无法生成优化建议。建议收集更多样本或检查分析逻辑。"
        
        # 获取当前Prompt作为参考
        current_prompt = self._get_current_prompt(content_type or "comment")
        
        suggestion_prompt = f"""基于以下错误模式分析，请生成具体的System Prompt优化建议：

**错误模式分析结果：**
{json.dumps(error_patterns, ensure_ascii=False, indent=2)}

**当前System Prompt（前500字符）：**
{current_prompt[:500]}...

**任务要求：**
请生成具体的优化建议，包括：

1. **需要修改的具体部分**：指出当前Prompt中哪些部分需要修改
2. **建议添加的新规则**：基于错误案例，应该添加哪些新的判断规则
3. **建议添加的示例**：提供2-3个新的Few-Shot示例来解决常见错误
4. **需要删除或弱化的规则**：哪些现有规则可能导致误判
5. **优化后的Prompt片段**：提供关键部分的优化版本

请以Markdown格式返回，便于阅读和审核。"""
        
        messages = [
            {"role": "system", "content": "你是Prompt工程专家，擅长优化System Prompt以提高AI系统准确性。"},
            {"role": "user", "content": suggestion_prompt}
        ]
        
        response_text = await llm_service._call_llm_api(messages)
        if not response_text:
            return "优化建议生成失败，请稍后重试。"
        
        logger.info("优化建议生成完成")
        return response_text
    
    def _format_corrections(self, corrections: List[AICorrection]) -> str:
        """格式化修正案例"""
        cases = []
        for i, corr in enumerate(corrections, 1):
            # 安全地获取JSON字段
            original = corr.original_result or {}
            corrected = corr.corrected_result or {}
            
            cases.append(f"""
**案例 {i}** ({corr.content_type}):
- 内容: {corr.content[:100]}{'...' if len(corr.content) > 100 else ''}
- AI原始结果: 评分={original.get('score', '未知')}, 分类={original.get('category', '未知')}, 理由={original.get('reason', '未知')}
- 管理员修正: 评分={corrected.get('score', '未知')}, 分类={corrected.get('category', '未知')}, 理由={corrected.get('reason', '未知')}
- 修正原因: {corr.correction_reason or '无'}
""")
        return "\n".join(cases)
    
    def _get_current_prompt(self, content_type: str) -> str:
        """获取当前Prompt"""
        try:
            from app.services.ai.prompts import (
                COMMENT_SYSTEM_PROMPT,
                DANMAKU_SYSTEM_PROMPT
            )
            if content_type.lower() == "danmaku":
                return DANMAKU_SYSTEM_PROMPT
            else:
                return COMMENT_SYSTEM_PROMPT
        except ImportError:
            return "无法获取当前Prompt"
    
    async def update_system_prompt(
        self,
        prompt_type: str,
        new_prompt: str,
        update_reason: str,
        updated_by: Optional[int] = None
    ) -> bool:
        """
        更新System Prompt
        
        注意：这个方法只记录版本历史，实际的Prompt更新需要手动修改prompts.py文件
        
        参数：
        - prompt_type: "COMMENT" 或 "DANMAKU"
        - new_prompt: 新的Prompt内容
        - update_reason: 更新原因
        - updated_by: 更新人ID
        
        返回：
        - bool: 是否成功
        """
        try:
            db = SessionLocal()
            try:
                # 1. 备份当前Prompt
                current_prompt = self._get_current_prompt(prompt_type.lower())
                
                # 2. 保存当前版本到历史记录
                backup_version = AIPromptVersion(
                    prompt_type=prompt_type.upper(),
                    prompt_content=current_prompt,
                    update_reason=f"备份（更新前）: {update_reason}",
                    updated_by=updated_by
                )
                db.add(backup_version)
                
                # 3. 保存新版本到历史记录
                new_version = AIPromptVersion(
                    prompt_type=prompt_type.upper(),
                    prompt_content=new_prompt,
                    update_reason=update_reason,
                    updated_by=updated_by
                )
                db.add(new_version)
                
                db.commit()
                
                logger.info(f"Prompt版本历史已更新: {prompt_type}")
                
                # 4. 记录更新请求（实际更新需要手动操作）
                logger.warning(
                    f"Prompt更新请求已记录，但需要手动更新prompts.py文件！\n"
                    f"类型: {prompt_type}\n"
                    f"新内容前200字符: {new_prompt[:200]}..."
                )
                
                return True
                
            except Exception as e:
                logger.error(f"数据库操作失败: {e}")
                db.rollback()
                return False
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"System Prompt更新失败: {e}")
            return False
    
    def get_prompt_versions(
        self, 
        prompt_type: Optional[str] = None, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取Prompt版本历史
        
        参数：
        - prompt_type: 过滤类型（"COMMENT"/"DANMAKU"，None表示全部）
        - limit: 返回数量限制
        
        返回：
        - List[Dict]: 版本历史列表
        """
        db = SessionLocal()
        try:
            query = db.query(AIPromptVersion)
            
            if prompt_type:
                query = query.filter(AIPromptVersion.prompt_type == prompt_type.upper())
            
            versions = (
                query.order_by(AIPromptVersion.created_at.desc())
                .limit(limit)
                .all()
            )
            
            return [
                {
                    "id": v.id,
                    "prompt_type": v.prompt_type,
                    "prompt_content": v.prompt_content,
                    "update_reason": v.update_reason,
                    "updated_by": v.updated_by,
                    "created_at": v.created_at.isoformat()
                }
                for v in versions
            ]
            
        except Exception as e:
            logger.error(f"获取Prompt版本历史失败: {e}")
            return []
        finally:
            db.close()


# 全局实例
self_correction_service = SelfCorrectionService()
