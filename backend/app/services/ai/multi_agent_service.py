"""
多智能体陪审团服务

功能：
1. 并行调用多个专家 Agent（热梗专家、情感专家、法律专家）
2. 检测专家意见冲突
3. 冲突时调用裁决 Agent，无冲突时加权平均
4. 记录分析过程（可选，用于审计和优化）

需求：深化方向二 - 深度层
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional

from app.core.config import settings
from app.services.ai.llm_service import llm_service
from app.services.ai.prompts import (
    MEME_EXPERT_PROMPT,
    EMOTION_EXPERT_PROMPT,
    LEGAL_EXPERT_PROMPT,
    JUDGE_AGENT_PROMPT
)

logger = logging.getLogger(__name__)


class MultiAgentService:
    """多智能体陪审团服务"""
    
    # Agent 配置
    AGENTS = [
        {
            "name": "meme_expert",
            "prompt": MEME_EXPERT_PROMPT,
            "weight": 0.3,  # 权重
            "priority": 3   # 优先级（数字越小优先级越高）
        },
        {
            "name": "emotion_expert",
            "prompt": EMOTION_EXPERT_PROMPT,
            "weight": 0.3,
            "priority": 2
        },
        {
            "name": "legal_expert",
            "prompt": LEGAL_EXPERT_PROMPT,
            "weight": 0.4,  # 法律专家权重最高
            "priority": 1   # 优先级最高
        }
    ]
    
    def __init__(self):
        """初始化服务"""
        # 从配置读取冲突阈值（分数差异超过此值视为冲突）
        self.conflict_threshold = getattr(
            settings, 
            "MULTI_AGENT_CONFLICT_THRESHOLD", 
            0.2  # 默认 20%
        )
    
    async def analyze_with_jury(
        self, 
        content: str, 
        content_type: str
    ) -> Dict[str, Any]:
        """
        多 Agent 并行分析
        
        流程：
        1. 并行调用多个 Agent
        2. 检查冲突
        3. 如有冲突，调用裁决 Agent
        4. 如无冲突，加权平均
        
        参数：
        - content: 待分析内容
        - content_type: 内容类型（"comment" 或 "danmaku"）
        
        返回：
        - Dict[str, Any]: 分析结果（格式与 llm_service 返回一致）
        """
        logger.info(f"开始多智能体分析: {content[:20]}...")
        
        # 1. 并行调用多个 Agent
        expert_results = await self._call_agents_parallel(content, content_type)
        
        # 2. 检查冲突
        has_conflict = self._has_conflict(expert_results)
        
        if has_conflict:
            # 3. 调用裁决 Agent
            logger.info(f"检测到专家意见冲突，调用裁决 Agent: {content[:10]}...")
            final_result = await self._call_judge_agent(content, expert_results)
        else:
            # 4. 加权平均
            logger.info(f"专家意见一致，使用加权平均: {content[:10]}...")
            final_result = self._weighted_merge(expert_results)
        
        # 5. 记录分析过程（可选，用于审计和优化）
        await self._save_analysis_record(content, expert_results, final_result)
        
        return final_result
    
    async def _call_agents_parallel(
        self, 
        content: str, 
        content_type: str
    ) -> List[Dict[str, Any]]:
        """
        并行调用多个 Agent
        
        使用 asyncio.gather 实现并行调用，提高效率
        """
        # 创建并行任务
        tasks = [
            self._call_agent(agent, content, content_type)
            for agent in self.AGENTS
        ]
        
        # 并行执行，允许异常
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        expert_results = []
        for i, result in enumerate(results):
            agent_name = self.AGENTS[i]["name"]
            
            if isinstance(result, Exception):
                logger.error(f"Agent {agent_name} 调用失败: {result}")
                # 使用默认值，避免整个流程失败
                expert_results.append({
                    "agent": agent_name,
                    "score": 60,  # 默认中等分数
                    "category": "未知",
                    "label": "分析失败",
                    "reason": f"Agent 调用异常: {str(result)}",
                    "confidence": 0.5,
                    "error": str(result)
                })
            else:
                expert_results.append(result)
        
        return expert_results
    
    async def _call_agent(
        self, 
        agent: dict, 
        content: str, 
        content_type: str
    ) -> Dict[str, Any]:
        """
        调用单个 Agent
        
        复用现有的 llm_service._call_llm_api 方法
        """
        messages = [
            {"role": "system", "content": agent["prompt"]},
            {"role": "user", "content": f"输入内容: {content}"}
        ]
        
        # 复用现有 LLM 调用逻辑
        response_text = await llm_service._call_llm_api(messages)
        
        if not response_text:
            raise Exception(f"Agent {agent['name']} 返回为空")
        
        # 解析结果
        parsed = self._parse_agent_response(response_text)
        parsed["agent"] = agent["name"]
        parsed["weight"] = agent["weight"]
        parsed["priority"] = agent.get("priority", 999)
        
        return parsed
    
    def _parse_agent_response(self, response_text: str) -> Dict[str, Any]:
        """
        解析 Agent 返回结果
        
        处理 JSON 格式的返回，兼容可能的 markdown 代码块
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # 记录原始响应（用于调试）
            original_text = response_text.strip()
            logger.debug(f"Agent 原始响应: {original_text[:200]}...")
            
            # 第一步：清理 markdown 代码块标记
            clean_text = original_text
            
            # 移除开头的代码块标记（```json 或 ```）
            if clean_text.startswith("```"):
                # 找到第一个换行符
                first_newline = clean_text.find("\n")
                if first_newline != -1:
                    clean_text = clean_text[first_newline + 1:]
                else:
                    # 如果没有换行符，直接移除开头的 ```
                    clean_text = clean_text.lstrip("`")
            
            # 移除结尾的代码块标记
            if clean_text.rstrip().endswith("```"):
                # 找到最后一个换行符
                last_newline = clean_text.rfind("\n")
                if last_newline != -1:
                    clean_text = clean_text[:last_newline]
                else:
                    # 如果没有换行符，直接移除结尾的 ```
                    clean_text = clean_text.rstrip("`")
            
            # 移除所有残留的代码块标记
            clean_text = clean_text.replace("```json", "").replace("```JSON", "").replace("```", "").strip()
            
            # 第二步：提取 JSON 部分（如果文本中包含其他内容）
            if not clean_text.startswith("{"):
                # 尝试找到第一个 { 和最后一个 }
                start_idx = clean_text.find("{")
                end_idx = clean_text.rfind("}")
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    clean_text = clean_text[start_idx:end_idx + 1]
                else:
                    # 如果找不到 JSON，记录错误
                    logger.warning(f"无法找到 JSON 对象，清理后文本: {clean_text[:100]}")
                    raise ValueError(f"无法找到有效的 JSON 对象")
            
            # 第三步：解析 JSON
            if not clean_text:
                raise ValueError("清理后的文本为空")
            
            logger.debug(f"准备解析的 JSON 文本: {clean_text[:200]}...")
            data = json.loads(clean_text)
            
            # 验证必要字段
            if "score" not in data:
                data["score"] = 60
            if "category" not in data:
                data["category"] = "未知"
            if "label" not in data:
                data["label"] = "未知"
            if "reason" not in data:
                data["reason"] = "无理由"
            if "confidence" not in data:
                data["confidence"] = 0.5
            
            return data
            
        except json.JSONDecodeError as e:
            logger.warning(f"Agent 返回解析失败: {response_text[:100]}... 错误: {e}")
            # 返回默认值
            return {
                "score": 60,
                "category": "未知",
                "label": "解析失败",
                "reason": f"Agent 返回格式错误: {str(e)}",
                "confidence": 0.5
            }
    
    def _has_conflict(self, expert_results: List[Dict[str, Any]]) -> bool:
        """
        检查是否存在冲突
        
        策略：如果专家分数差异超过阈值，视为冲突
        
        参数：
        - expert_results: 专家分析结果列表
        
        返回：
        - bool: 是否存在冲突
        """
        # 过滤掉有错误的结果
        valid_results = [r for r in expert_results if "error" not in r]
        
        if len(valid_results) < 2:
            # 少于2个有效结果，无法判断冲突
            return False
        
        # 提取所有分数
        scores = [r.get("score", 60) for r in valid_results]
        
        max_score = max(scores)
        min_score = min(scores)
        score_diff = max_score - min_score
        
        # 分数差异超过阈值（默认20%），视为冲突
        threshold = self.conflict_threshold * 100  # 转换为分数差异
        
        has_conflict = score_diff > threshold
        
        if has_conflict:
            logger.info(
                f"检测到冲突: 分数差异 {score_diff} > 阈值 {threshold} "
                f"(最高: {max_score}, 最低: {min_score})"
            )
        
        return has_conflict
    
    async def _call_judge_agent(
        self, 
        content: str, 
        expert_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        调用裁决 Agent
        
        当专家意见冲突时，由裁决 Agent 综合判断
        """
        # 格式化专家意见
        expert_opinions = []
        for r in expert_results:
            if "error" not in r:
                expert_opinions.append(
                    f"**{r['agent']}**: {r.get('reason', '无理由')} "
                    f"(评分: {r.get('score', 60)}, "
                    f"置信度: {r.get('confidence', 0.5):.2f})"
                )
        
        expert_opinions_text = "\n\n".join(expert_opinions)
        
        # 构建消息
        messages = [
            {"role": "system", "content": JUDGE_AGENT_PROMPT},
            {
                "role": "user", 
                "content": f"专家意见：\n{expert_opinions_text}\n\n请给出最终裁决。"
            }
        ]
        
        # 调用 LLM
        response_text = await llm_service._call_llm_api(messages)
        
        if not response_text:
            # 降级到加权平均
            logger.warning("裁决 Agent 返回为空，降级到加权平均")
            return self._weighted_merge(expert_results)
        
        # 解析结果
        parsed = self._parse_agent_response(response_text)
        parsed["conflict_resolved"] = True
        parsed["expert_results"] = expert_results
        
        return parsed
    
    def _weighted_merge(self, expert_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        加权平均合并专家意见
        
        当专家意见一致时，使用加权平均得出最终结果
        """
        # 过滤掉有错误的结果
        valid_results = [r for r in expert_results if "error" not in r]
        
        if not valid_results:
            # 所有 Agent 都失败，返回默认值
            logger.error("所有 Agent 调用失败，返回默认结果")
            return {
                "score": 60,
                "category": "未知",
                "label": "分析失败",
                "reason": "所有 Agent 调用失败",
                "confidence": 0.0,
                "is_highlight": False,
                "is_inappropriate": False
            }
        
        # 计算加权平均 score
        total_weight = sum(r.get("weight", 0.33) for r in valid_results)
        if total_weight == 0:
            total_weight = 1.0  # 防止除零
        
        weighted_score = sum(
            r.get("score", 60) * r.get("weight", 0.33) 
            for r in valid_results
        ) / total_weight
        
        # 计算平均置信度
        avg_confidence = sum(
            r.get("confidence", 0.5) for r in valid_results
        ) / len(valid_results)
        
        # 选择最高优先级的 category 和 label
        # （优先级数字越小，优先级越高）
        sorted_results = sorted(
            valid_results, 
            key=lambda x: x.get("priority", 999)
        )
        primary_result = sorted_results[0]
        
        # 构建最终结果
        final_result = {
            "score": int(weighted_score),
            "category": primary_result.get("category", "综合"),
            "label": primary_result.get("label", "综合"),
            "reason": f"综合{len(valid_results)}位专家意见（加权平均）",
            "confidence": avg_confidence,
            "is_highlight": weighted_score >= 90,  # 高分高亮
            "is_inappropriate": weighted_score < 30,  # 低分标记不当
            "expert_results": expert_results  # 保留专家原始结果（用于审计）
        }
        
        return final_result
    
    async def _save_analysis_record(
        self, 
        content: str, 
        expert_results: List[Dict[str, Any]], 
        final_result: Dict[str, Any]
    ):
        """
        保存分析记录（可选，用于审计和优化）
        
        注意：如果数据库表不存在，此方法会静默失败
        """
        try:
            from app.core.database import SessionLocal
            from app.models.ai_agent_analysis import AgentAnalysis
            
            db = SessionLocal()
            try:
                # 计算内容哈希
                content_hash = llm_service._get_content_hash(content)
                
                # 创建记录
                record = AgentAnalysis(
                    content_hash=content_hash,
                    agent_name="multi_agent",
                    agent_result=json.dumps(expert_results, ensure_ascii=False),
                    final_result=json.dumps(final_result, ensure_ascii=False)
                )
                
                db.add(record)
                db.commit()
                
                logger.debug(f"已保存 Agent 分析记录: {content_hash}")
                
            except Exception as e:
                # 如果表不存在或其他错误，静默失败
                logger.debug(f"保存 Agent 分析记录失败（可能表不存在）: {e}")
                db.rollback()
            finally:
                db.close()
                
        except ImportError:
            # 如果模型不存在，静默失败
            logger.debug("AgentAnalysis 模型不存在，跳过记录保存")
        except Exception as e:
            logger.warning(f"保存 Agent 分析记录异常: {e}")


# 全局实例
multi_agent_service = MultiAgentService()