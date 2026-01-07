"""
视频多模态审核服务 - 两阶段审核优化版

功能：
1. 两阶段审核：初筛（低成本）+ 精审（高成本）
2. 帧审核：规则预筛选 + 云端精审
3. 字幕审核：本地粗判 + 云端复核
4. 成本控制：预算管理 + 智能采样
5. 硬件优化：针对RTX 3050 4GB显存优化

架构：
- Stage 1: 规则/本地模型初筛（低成本，高召回）
- Stage 2: 云端模型精审（高成本，高精度）
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.video import Video
from app.services.ai.token_optimizer import token_optimizer
from app.utils.timezone_utils import isoformat_in_app_tz, utc_now

logger = logging.getLogger(__name__)


class TwoStageVideoReviewService:
    """两阶段视频审核服务"""
    
    def __init__(self):
        # 使用新的模式配置
        llm_mode = getattr(settings, "LLM_MODE", "hybrid").lower()
        vision_mode = getattr(settings, "VISION_MODE", "hybrid").lower()
        
        self.use_cloud = llm_mode in ("cloud_only", "hybrid") and settings.LLM_API_KEY
        self.use_local = llm_mode in ("local_only", "hybrid")
        self.use_cloud_vision = vision_mode in ("cloud_only", "hybrid") and getattr(settings, 'LLM_VISION_API_KEY', settings.LLM_API_KEY)
        
        # 两阶段审核配置
        self.stage1_confidence_threshold = 0.7  # 初筛置信度阈值
        self.stage2_budget_limit = getattr(settings, 'CLOUD_MAX_CALLS_PER_VIDEO', 50)
        
        # 硬件优化配置
        self.max_concurrent_frames = 2  # RTX 3050优化：降低并发
        self.frame_sampling_rate = 0.5  # 采样率：只处理50%的帧
        
        logger.info(f"两阶段审核服务初始化: cloud={self.use_cloud}, local={self.use_local}")
    
    async def review_video_two_stage(
        self, 
        video_id: int, 
        video_path: str,
        subtitle_path: Optional[str] = None,
        force_stage2: bool = False
    ) -> Dict[str, Any]:
        """
        两阶段视频审核主入口
        
        Args:
            video_id: 视频ID
            video_path: 视频文件路径
            subtitle_path: 字幕文件路径（可选）
            force_stage2: 是否强制进行第二阶段审核
        
        Returns:
            Dict: 审核报告
        """
        logger.info(f"开始两阶段审核: video_id={video_id}")
        
        review_report = {
            "video_id": video_id,
            "review_type": "two_stage",
            "stage1_results": {},
            "stage2_results": {},
            "final_decision": {},
            "cost_info": {},
            "timestamp": isoformat_in_app_tz(utc_now()),
        }
        
        try:
            # Stage 1: 初筛（低成本）
            stage1_results = await self._stage1_initial_screening(
                video_id, video_path, subtitle_path
            )
            review_report["stage1_results"] = stage1_results
            
            # 判断是否需要进入Stage 2
            needs_stage2 = (
                force_stage2 or 
                stage1_results.get("risk_score", 0) > 30 or
                stage1_results.get("confidence", 1.0) < self.stage1_confidence_threshold
            )
            
            if needs_stage2:
                # Stage 2: 精审（高成本）
                stage2_results = await self._stage2_detailed_review(
                    video_id, video_path, subtitle_path, stage1_results
                )
                review_report["stage2_results"] = stage2_results
                
                # 合并结果
                final_decision = self._merge_stage_results(stage1_results, stage2_results)
            else:
                # 仅使用Stage 1结果
                final_decision = self._finalize_stage1_results(stage1_results)
                logger.info(f"视频 {video_id} 通过初筛，跳过精审")
            
            review_report["final_decision"] = final_decision
            review_report["cost_info"] = await self._calculate_cost_info(stage1_results, review_report.get("stage2_results"))
            
            # 更新数据库
            await self._update_video_review_status(video_id, final_decision)
            
            return review_report
            
        except Exception as e:
            logger.error(f"两阶段审核失败: video_id={video_id}, error={e}")
            review_report["error"] = str(e)
            return review_report
    
    async def _stage1_initial_screening(
        self, 
        video_id: int, 
        video_path: str, 
        subtitle_path: Optional[str]
    ) -> Dict[str, Any]:
        """
        Stage 1: 初筛阶段（低成本，高召回）
        
        策略：
        1. 规则基础筛选
        2. 本地模型粗判
        3. 关键帧采样
        4. 字幕关键词检测
        """
        logger.info(f"Stage 1 初筛开始: video_id={video_id}")
        
        stage1_results = {
            "stage": 1,
            "method": "initial_screening",
            "frame_results": [],
            "subtitle_results": {},
            "rule_results": {},
            "risk_score": 0,
            "confidence": 1.0,
            "processing_time": 0
        }
        
        start_time = datetime.utcnow()
        
        try:
            # 1. 规则基础筛选
            rule_results = await self._rule_based_screening(video_path, subtitle_path)
            stage1_results["rule_results"] = rule_results
            
            # 如果规则直接判定为高风险，提高风险分数
            if rule_results.get("high_risk", False):
                stage1_results["risk_score"] = 80
                stage1_results["confidence"] = 0.9
                return stage1_results
            
            # 2. 字幕初筛（如果有字幕）
            if subtitle_path:
                subtitle_results = await self._subtitle_initial_screening(subtitle_path)
                stage1_results["subtitle_results"] = subtitle_results
                stage1_results["risk_score"] = max(stage1_results["risk_score"], subtitle_results.get("risk_score", 0))
            
            # 3. 关键帧采样和初筛
            frame_results = await self._frame_initial_screening(video_path)
            stage1_results["frame_results"] = frame_results
            
            # 计算综合风险分数
            frame_risk = max([f.get("risk_score", 0) for f in frame_results], default=0)
            stage1_results["risk_score"] = max(stage1_results["risk_score"], frame_risk)
            
            # 计算置信度（基于处理的样本数量和一致性）
            stage1_results["confidence"] = self._calculate_stage1_confidence(stage1_results)
            
        except Exception as e:
            logger.error(f"Stage 1 初筛失败: {e}")
            stage1_results["error"] = str(e)
            stage1_results["confidence"] = 0.0
        
        finally:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            stage1_results["processing_time"] = processing_time
            logger.info(f"Stage 1 完成: risk_score={stage1_results['risk_score']}, confidence={stage1_results['confidence']:.2f}")
        
        return stage1_results
    
    async def _stage2_detailed_review(
        self, 
        video_id: int, 
        video_path: str, 
        subtitle_path: Optional[str],
        stage1_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Stage 2: 精审阶段（高成本，高精度）
        
        策略：
        1. 云端模型精确分析
        2. 重点审核Stage 1标记的疑似内容
        3. 多智能体复核（如果启用）
        4. 预算控制
        """
        logger.info(f"Stage 2 精审开始: video_id={video_id}")
        
        stage2_results = {
            "stage": 2,
            "method": "detailed_review",
            "frame_results": [],
            "subtitle_results": {},
            "cloud_calls": 0,
            "risk_score": 0,
            "confidence": 1.0,
            "processing_time": 0,
            "budget_exceeded": False
        }
        
        start_time = datetime.utcnow()
        
        try:
            # 检查预算
            if not await token_optimizer._check_budget():
                stage2_results["budget_exceeded"] = True
                stage2_results["confidence"] = 0.5
                logger.warning(f"预算不足，跳过Stage 2精审: video_id={video_id}")
                return stage2_results
            
            # 1. 精审疑似风险帧
            suspicious_frames = [
                f for f in stage1_results.get("frame_results", [])
                if f.get("risk_score", 0) > 20
            ]
            
            if suspicious_frames and self.use_cloud_vision:
                frame_results = await self._detailed_frame_review(suspicious_frames[:10])  # 限制数量
                stage2_results["frame_results"] = frame_results
                stage2_results["cloud_calls"] += len(frame_results)
            
            # 2. 精审字幕内容
            if subtitle_path and stage1_results.get("subtitle_results", {}).get("risk_score", 0) > 20:
                subtitle_results = await self._detailed_subtitle_review(subtitle_path)
                stage2_results["subtitle_results"] = subtitle_results
                stage2_results["cloud_calls"] += 1
            
            # 计算综合风险分数
            frame_risk = max([f.get("risk_score", 0) for f in stage2_results["frame_results"]], default=0)
            subtitle_risk = stage2_results.get("subtitle_results", {}).get("risk_score", 0)
            stage2_results["risk_score"] = max(frame_risk, subtitle_risk)
            
            # 高置信度（云端模型结果）
            stage2_results["confidence"] = 0.95
            
        except Exception as e:
            logger.error(f"Stage 2 精审失败: {e}")
            stage2_results["error"] = str(e)
            stage2_results["confidence"] = 0.0
        
        finally:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            stage2_results["processing_time"] = processing_time
            logger.info(f"Stage 2 完成: risk_score={stage2_results['risk_score']}, cloud_calls={stage2_results['cloud_calls']}")
        
        return stage2_results
    
    async def _rule_based_screening(self, video_path: str, subtitle_path: Optional[str]) -> Dict[str, Any]:
        """规则基础筛选"""
        rule_results = {
            "high_risk": False,
            "risk_keywords": [],
            "file_checks": {}
        }
        
        # 文件大小检查
        import os
        if os.path.exists(video_path):
            file_size = os.path.getsize(video_path)
            rule_results["file_checks"]["size_mb"] = file_size / (1024 * 1024)
            
            # 超大文件可能包含更多风险内容
            if file_size > 500 * 1024 * 1024:  # 500MB
                rule_results["high_risk"] = True
                rule_results["risk_keywords"].append("超大文件")
        
        # 字幕关键词检查
        if subtitle_path and os.path.exists(subtitle_path):
            try:
                with open(subtitle_path, 'r', encoding='utf-8') as f:
                    subtitle_content = f.read()
                
                # 高风险关键词
                high_risk_keywords = ["暴力", "血腥", "恐怖", "政治", "敏感"]
                found_keywords = [kw for kw in high_risk_keywords if kw in subtitle_content]
                
                if found_keywords:
                    rule_results["high_risk"] = True
                    rule_results["risk_keywords"].extend(found_keywords)
                    
            except Exception as e:
                logger.warning(f"字幕关键词检查失败: {e}")
        
        return rule_results
    
    async def _subtitle_initial_screening(self, subtitle_path: str) -> Dict[str, Any]:
        """字幕初筛"""
        subtitle_results = {
            "risk_score": 0,
            "method": "local_screening",
            "segments_checked": 0
        }
        
        try:
            # 这里可以调用本地模型进行字幕初筛
            # 暂时使用简单的关键词匹配
            with open(subtitle_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 简单风险评估
            risk_indicators = ["争议", "问题", "不当", "违规"]
            risk_count = sum(1 for indicator in risk_indicators if indicator in content)
            
            subtitle_results["risk_score"] = min(risk_count * 15, 60)  # 最高60分
            subtitle_results["segments_checked"] = len(content.split('\n'))
            
        except Exception as e:
            logger.error(f"字幕初筛失败: {e}")
            subtitle_results["error"] = str(e)
        
        return subtitle_results
    
    async def _frame_initial_screening(self, video_path: str) -> List[Dict[str, Any]]:
        """关键帧初筛"""
        frame_results = []
        
        try:
            # 这里应该调用帧提取和初筛逻辑
            # 暂时返回模拟结果
            for i in range(5):  # 模拟5帧
                frame_result = {
                    "frame_index": i,
                    "timestamp": i * 10,  # 每10秒一帧
                    "risk_score": 10 + (i * 5),  # 模拟风险分数
                    "method": "rule_based"
                }
                frame_results.append(frame_result)
                
        except Exception as e:
            logger.error(f"关键帧初筛失败: {e}")
        
        return frame_results
    
    async def _detailed_frame_review(self, suspicious_frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """详细帧审核（云端）"""
        detailed_results = []
        
        for frame in suspicious_frames:
            try:
                # 这里应该调用云端视觉模型
                # 暂时返回模拟结果
                detailed_result = frame.copy()
                detailed_result["method"] = "cloud_vision"
                detailed_result["risk_score"] = min(frame.get("risk_score", 0) + 10, 100)
                detailed_result["confidence"] = 0.9
                
                detailed_results.append(detailed_result)
                
                # 记录Token使用
                await token_optimizer.record_token_usage(1)
                
            except Exception as e:
                logger.error(f"详细帧审核失败: {e}")
        
        return detailed_results
    
    async def _detailed_subtitle_review(self, subtitle_path: str) -> Dict[str, Any]:
        """详细字幕审核（云端）"""
        subtitle_results = {
            "risk_score": 0,
            "method": "cloud_text",
            "confidence": 0.9
        }
        
        try:
            # 这里应该调用云端文本模型
            # 暂时返回模拟结果
            subtitle_results["risk_score"] = 25  # 模拟结果
            
            # 记录Token使用
            await token_optimizer.record_token_usage(1)
            
        except Exception as e:
            logger.error(f"详细字幕审核失败: {e}")
            subtitle_results["error"] = str(e)
        
        return subtitle_results
    
    def _calculate_stage1_confidence(self, stage1_results: Dict[str, Any]) -> float:
        """计算Stage 1置信度"""
        base_confidence = 0.7
        
        # 根据处理的内容数量调整置信度
        frame_count = len(stage1_results.get("frame_results", []))
        if frame_count > 3:
            base_confidence += 0.1
        
        # 根据规则匹配情况调整
        if stage1_results.get("rule_results", {}).get("high_risk", False):
            base_confidence += 0.2
        
        return min(base_confidence, 1.0)
    
    def _merge_stage_results(self, stage1_results: Dict[str, Any], stage2_results: Dict[str, Any]) -> Dict[str, Any]:
        """合并两阶段结果"""
        return {
            "final_risk_score": max(
                stage1_results.get("risk_score", 0),
                stage2_results.get("risk_score", 0)
            ),
            "confidence": stage2_results.get("confidence", 0.5),
            "review_method": "two_stage",
            "stage1_risk": stage1_results.get("risk_score", 0),
            "stage2_risk": stage2_results.get("risk_score", 0),
            "cloud_calls_used": stage2_results.get("cloud_calls", 0),
            "total_processing_time": (
                stage1_results.get("processing_time", 0) + 
                stage2_results.get("processing_time", 0)
            )
        }
    
    def _finalize_stage1_results(self, stage1_results: Dict[str, Any]) -> Dict[str, Any]:
        """最终化Stage 1结果"""
        return {
            "final_risk_score": stage1_results.get("risk_score", 0),
            "confidence": stage1_results.get("confidence", 0.7),
            "review_method": "stage1_only",
            "cloud_calls_used": 0,
            "total_processing_time": stage1_results.get("processing_time", 0)
        }
    
    async def _calculate_cost_info(self, stage1_results: Dict[str, Any], stage2_results: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """计算成本信息"""
        cost_info = {
            "stage1_cost": 0.0,  # Stage 1基本无成本
            "stage2_cost": 0.0,
            "total_cost": 0.0,
            "cloud_calls": 0,
            "cost_efficiency": "high"
        }
        
        if stage2_results:
            cloud_calls = stage2_results.get("cloud_calls", 0)
            cost_info["cloud_calls"] = cloud_calls
            cost_info["stage2_cost"] = cloud_calls * 0.01  # 假设每次调用0.01元
            cost_info["total_cost"] = cost_info["stage2_cost"]
            
            # 成本效率评估
            if cloud_calls > 10:
                cost_info["cost_efficiency"] = "low"
            elif cloud_calls > 5:
                cost_info["cost_efficiency"] = "medium"
        
        return cost_info
    
    async def _update_video_review_status(self, video_id: int, final_decision: Dict[str, Any]):
        """更新视频审核状态"""
        try:
            db = SessionLocal()
            try:
                video = db.query(Video).filter(Video.id == video_id).first()
                if video:
                    risk_score = final_decision.get("final_risk_score", 0)
                    
                    if risk_score > 70:
                        video.review_status = "rejected"
                    elif risk_score > 40:
                        video.review_status = "pending"
                    else:
                        video.review_status = "approved"
                    
                    db.commit()
                    logger.info(f"视频 {video_id} 审核状态更新为: {video.review_status}")
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"更新视频审核状态失败: {e}")


# 全局实例
two_stage_review_service = TwoStageVideoReviewService()
