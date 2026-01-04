"""
反馈式自我纠错服务

功能：
1. 分析管理员修正记录，识别错误模式
2. 使用元 Prompt 生成优化建议
3. 管理 Prompt 版本历史
4. 支持 Prompt 更新和回滚

需求：深化方向三 - 进化层
"""

import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.types import ErrorPattern, CorrectionRecord
from app.core.database import SessionLocal
from app.models.ai_correction import AiCorrection
from app.models.ai_prompt_version import AiPromptVersion

logger = logging.getLogger(__name__)


class SelfCorrectionService:
    """反馈式自我纠错服务"""
    
    def __init__(self):
        self.min_samples = settings.SELF_CORRECTION_MIN_SAMPLES
        self.analysis_days = settings.SELF_CORRECTION_ANALYSIS_DAYS
    
    async def analyze_errors(self, days: Optional[int] = None) -> dict:
        """
        分析最近 N 天的错误案例
        
        参数：
        - days: 分析天数（默认使用配置值）
        
        返回：
        {
            "error_patterns": [...],
            "suggestions": "...",
            "sample_count": 10,
            "analysis_date": "2025-12-25"
        }
        """
        if days is None:
            days = self.analysis_days
        
        db = SessionLocal()
        try:
            # 1. 查询修正记录
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            corrections = db.query(AiCorrection).filter(
                AiCorrection.created_at >= cutoff_date
            ).all()
            
            if len(corrections) < self.min_samples:
                return {
                    "error": f"样本数量不足（需要至少 {self.min_samples} 个，当前 {len(corrections)} 个）",
                    "sample_count": len(corrections),
                    "analysis_date": datetime.utcnow().isoformat()
                }
            
            logger.info(f"[SelfCorrection] 开始分析 {len(corrections)} 个修正记录")
            
            # 2. 调用元 Prompt 分析错误模式
            error_patterns = await self._analyze_error_patterns(corrections)
            
            # 3. 生成优化建议
            suggestions = await self._generate_suggestions(error_patterns, corrections)
            
            return {
                "error_patterns": error_patterns,
                "suggestions": suggestions,
                "sample_count": len(corrections),
                "analysis_date": datetime.utcnow().isoformat()
            }
        finally:
            db.close()
    
    async def _analyze_error_patterns(
        self, corrections: List[AiCorrection]
    ) -> List[Dict[str, Any]]:
        """使用元 Prompt 分析错误模式（优化版：使用本地模型，更精确的错误模式识别）"""
        from app.services.ai.local_model_service import local_model_service
        
        # 格式化修正案例（最多15个，避免超出token限制）
        cases_text = self._format_corrections(corrections[:15])
        
        # 统计错误类型频率
        error_stats = self._calculate_error_statistics(corrections)
        
        meta_prompt = f"""你是 AI 系统优化专家。以下是最近 {len(corrections)} 个误判案例：

{cases_text}

错误统计：
{error_stats}

请深入分析：
1. **共同模式识别**：这些错误的共同特征是什么？（内容类型、评分偏差、分类错误等）
2. **Prompt弱点**：当前 System Prompt 的哪些部分容易导致误判？
3. **规则建议**：应该添加哪些新的判断规则或示例？
4. **高频错误**：哪些类型的错误出现频率最高？需要优先修复。

请以严格的 JSON 格式返回分析结果（不要包含任何Markdown标记）：
{{
    "common_patterns": ["模式1：...", "模式2：..."],
    "weak_points": ["弱点1：...", "弱点2：..."],
    "suggested_rules": ["规则1：...", "规则2：..."],
    "high_frequency_errors": ["错误类型1：...", "错误类型2：..."],
    "priority_fixes": ["优先修复项1", "优先修复项2"]
}}"""
        
        try:
            # 使用本地模型进行分析
            result = await local_model_service.predict(meta_prompt, "comment")
            if not result:
                logger.warning("[SelfCorrection] 本地模型分析失败，尝试降级处理")
                return self._fallback_pattern_analysis(corrections)
            
            # 从结果中提取分析内容
            if isinstance(result, dict) and "reason" in result:
                # 如果返回的是标准格式，尝试从reason中提取JSON
                reason_text = result.get("reason", "")
                try:
                    patterns = json.loads(reason_text)
                    logger.info(f"[SelfCorrection] 识别到 {len(patterns.get('common_patterns', []))} 个错误模式")
                    return patterns
                except json.JSONDecodeError:
                    pass
            
            # 如果无法从reason提取，尝试直接解析整个结果
            patterns = {
                "common_patterns": [result.get("category", "未知模式")],
                "weak_points": [result.get("label", "未知弱点")],
                "suggested_rules": [result.get("reason", "需要进一步分析")],
                "high_frequency_errors": [result.get("category", "未知错误")],
                "priority_fixes": []
            }
            logger.info(f"[SelfCorrection] 使用降级分析，识别到基础模式")
            return patterns
            
        except Exception as e:
            logger.error(f"[SelfCorrection] 错误模式分析异常: {e}")
            return self._fallback_pattern_analysis(corrections)
    
    def _calculate_error_statistics(self, corrections: List[AiCorrection]) -> str:
        """计算错误统计信息"""
        stats = {
            "content_types": {},
            "score_diffs": [],
            "categories": {}
        }
        
        for corr in corrections:
            # 统计内容类型
            stats["content_types"][corr.content_type] = stats["content_types"].get(corr.content_type, 0) + 1
            
            # 计算评分差异
            original_score = corr.original_result.get("score", 0) if isinstance(corr.original_result, dict) else 0
            corrected_score = corr.corrected_result.get("score", 0) if isinstance(corr.corrected_result, dict) else 0
            stats["score_diffs"].append(abs(original_score - corrected_score))
            
            # 统计错误分类
            original_cat = corr.original_result.get("category", "未知") if isinstance(corr.original_result, dict) else "未知"
            stats["categories"][original_cat] = stats["categories"].get(original_cat, 0) + 1
        
        avg_diff = sum(stats["score_diffs"]) / len(stats["score_diffs"]) if stats["score_diffs"] else 0
        
        return f"""
- 内容类型分布: {json.dumps(stats['content_types'], ensure_ascii=False)}
- 平均评分差异: {avg_diff:.1f}分
- 错误分类分布: {json.dumps(stats['categories'], ensure_ascii=False)}
"""
    
    def _fallback_pattern_analysis(self, corrections: List[AiCorrection]) -> Dict[str, Any]:
        """降级分析：当LLM分析失败时，使用规则基础分析"""
        # 简单的规则基础分析
        content_types = {}
        score_diffs = []
        
        for corr in corrections:
            content_types[corr.content_type] = content_types.get(corr.content_type, 0) + 1
            original_score = corr.original_result.get("score", 0) if isinstance(corr.original_result, dict) else 0
            corrected_score = corr.corrected_result.get("score", 0) if isinstance(corr.corrected_result, dict) else 0
            score_diffs.append(abs(original_score - corrected_score))
        
        avg_diff = sum(score_diffs) / len(score_diffs) if score_diffs else 0
        most_common_type = max(content_types.items(), key=lambda x: x[1])[0] if content_types else "未知"
        
        return {
            "common_patterns": [f"{most_common_type}类型内容误判率较高"],
            "weak_points": [f"平均评分偏差 {avg_diff:.1f}分，需要优化评分逻辑"],
            "suggested_rules": ["增加更多示例，提高判断准确性"],
            "high_frequency_errors": [most_common_type],
            "priority_fixes": [f"优先优化{most_common_type}类型的判断逻辑"]
        }
    
    async def _generate_suggestions(
        self, error_patterns: Dict[str, Any], corrections: List[AiCorrection]
    ) -> str:
        """生成优化建议（优化版：使用本地模型，更精炼的建议）"""
        from app.services.ai.local_model_service import local_model_service
        
        if not error_patterns:
            return "未发现明显的错误模式，建议继续收集更多样本。"
        
        suggestion_prompt = f"""基于以下错误模式分析，请生成具体的 System Prompt 优化建议：

{json.dumps(error_patterns, ensure_ascii=False, indent=2)}

请生成优化建议（要求精炼，不超过200字）：
1. 需要修改的具体部分
2. 建议添加的新规则或示例（最多3条）
3. 需要删除或弱化的规则（最多2条）

请以简洁的文本格式返回，不要使用Markdown。"""
        
        try:
            # 使用本地模型生成建议
            result = await local_model_service.predict(suggestion_prompt, "comment")
            if not result:
                logger.warning("[SelfCorrection] 本地模型生成建议失败，使用规则基础建议")
                return self._generate_fallback_suggestions(error_patterns)
            
            # 从结果中提取建议文本
            suggestion_text = result.get("reason", "") or result.get("label", "")
            if suggestion_text:
                logger.info("[SelfCorrection] 优化建议生成完成")
                return suggestion_text
            else:
                return self._generate_fallback_suggestions(error_patterns)
                
        except Exception as e:
            logger.error(f"[SelfCorrection] 生成优化建议异常: {e}")
            return self._generate_fallback_suggestions(error_patterns)
    
    def _generate_fallback_suggestions(self, error_patterns: Dict[str, Any]) -> str:
        """降级建议生成：当LLM失败时，使用规则基础建议"""
        suggestions = []
        
        if error_patterns.get("common_patterns"):
            suggestions.append(f"发现 {len(error_patterns['common_patterns'])} 个共同模式，建议在Prompt中添加相应示例。")
        
        if error_patterns.get("weak_points"):
            suggestions.append(f"识别到 {len(error_patterns['weak_points'])} 个Prompt弱点，需要针对性优化。")
        
        if error_patterns.get("suggested_rules"):
            suggestions.append(f"建议添加 {len(error_patterns['suggested_rules'])} 条新规则以提高准确性。")
        
        if error_patterns.get("priority_fixes"):
            suggestions.append(f"优先修复：{', '.join(error_patterns['priority_fixes'][:2])}")
        
        return "\n".join(suggestions) if suggestions else "建议继续收集更多样本进行深入分析。"
    
    def _format_corrections(self, corrections: List[AiCorrection]) -> str:
        """格式化修正案例"""
        cases = []
        for i, corr in enumerate(corrections, 1):
            cases.append(f"""
案例 {i}:
- 内容类型: {corr.content_type}
- 内容: {corr.content[:100]}...
- AI 原始结果: {json.dumps(corr.original_result, ensure_ascii=False)}
- 管理员修正: {json.dumps(corr.corrected_result, ensure_ascii=False)}
- 修正原因: {corr.correction_reason}
""")
        return "\n".join(cases)
    
    async def update_system_prompt(
        self,
        prompt_type: str,
        new_prompt: str,
        update_reason: str,
        updated_by: Optional[int] = None
    ) -> bool:
        """
        更新 System Prompt
        
        流程：
        1. 备份当前 Prompt
        2. 停用旧版本
        3. 创建新版本并激活
        4. 记录版本历史
        
        参数：
        - prompt_type: Prompt 类型（COMMENT / DANMAKU / MEME_EXPERT / EMOTION_EXPERT / LEGAL_EXPERT）
        - new_prompt: 新的 Prompt 内容
        - update_reason: 更新原因
        - updated_by: 更新人ID
        
        返回：
        - bool: 是否更新成功
        """
        try:
            db = SessionLocal()
            try:
                # 1. 停用旧版本
                db.query(AiPromptVersion).filter(
                    AiPromptVersion.prompt_type == prompt_type,
                    AiPromptVersion.is_active == True
                ).update({"is_active": False})
                
                # 2. 创建新版本
                new_version = AiPromptVersion(
                    prompt_type=prompt_type,
                    prompt_content=new_prompt,
                    update_reason=update_reason,
                    updated_by=updated_by,
                    is_active=True
                )
                db.add(new_version)
                db.commit()
                
                logger.info(f"[SelfCorrection] System Prompt 更新成功: {prompt_type}")
                return True
            finally:
                db.close()
        except Exception as e:
            logger.error(f"[SelfCorrection] System Prompt 更新失败: {e}")
            return False
    
    def get_active_prompt(self, prompt_type: str) -> Optional[str]:
        """
        获取当前激活的 Prompt
        
        参数：
        - prompt_type: Prompt 类型
        
        返回：
        - str: Prompt 内容，如果不存在则返回 None
        """
        db = SessionLocal()
        try:
            version = db.query(AiPromptVersion).filter(
                AiPromptVersion.prompt_type == prompt_type,
                AiPromptVersion.is_active == True
            ).first()
            
            if version:
                return version.prompt_content
            return None
        finally:
            db.close()
    
    def get_prompt_history(
        self, prompt_type: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取 Prompt 版本历史
        
        参数：
        - prompt_type: Prompt 类型（可选，不指定则返回所有类型）
        - limit: 返回数量限制
        
        返回：
        - List[Dict]: 版本历史列表
        """
        db = SessionLocal()
        try:
            query = db.query(AiPromptVersion)
            
            if prompt_type:
                query = query.filter(AiPromptVersion.prompt_type == prompt_type)
            
            versions = query.order_by(
                AiPromptVersion.created_at.desc()
            ).limit(limit).all()
            
            return [
                {
                    "id": v.id,
                    "prompt_type": v.prompt_type,
                    "prompt_content": v.prompt_content[:200] + "..." if len(v.prompt_content) > 200 else v.prompt_content,
                    "update_reason": v.update_reason,
                    "updated_by": v.updated_by,
                    "is_active": v.is_active,
                    "created_at": v.created_at.isoformat()
                }
                for v in versions
            ]
        finally:
            db.close()
    
    async def rollback_prompt(
        self, version_id: int, rollback_by: Optional[int] = None
    ) -> bool:
        """
        回滚到指定版本
        
        参数：
        - version_id: 要回滚到的版本ID
        - rollback_by: 回滚操作人ID
        
        返回：
        - bool: 是否回滚成功
        """
        db = SessionLocal()
        try:
            # 1. 查询目标版本
            target_version = db.query(AiPromptVersion).filter(
                AiPromptVersion.id == version_id
            ).first()
            
            if not target_version:
                logger.warning(f"[SelfCorrection] 版本 {version_id} 不存在")
                return False
            
            # 2. 停用当前激活版本
            db.query(AiPromptVersion).filter(
                AiPromptVersion.prompt_type == target_version.prompt_type,
                AiPromptVersion.is_active == True
            ).update({"is_active": False})
            
            # 3. 激活目标版本
            target_version.is_active = True
            
            # 4. 记录回滚操作（创建新版本）
            rollback_version = AiPromptVersion(
                prompt_type=target_version.prompt_type,
                prompt_content=target_version.prompt_content,
                update_reason=f"回滚到版本 {version_id}",
                updated_by=rollback_by,
                is_active=True
            )
            db.add(rollback_version)
            
            db.commit()
            
            logger.info(
                f"[SelfCorrection] Prompt 回滚成功: {target_version.prompt_type} -> 版本 {version_id}"
            )
            return True
        except Exception as e:
            logger.error(f"[SelfCorrection] Prompt 回滚失败: {e}")
            db.rollback()
            return False
        finally:
            db.close()


# 全局实例
self_correction_service = SelfCorrectionService()
