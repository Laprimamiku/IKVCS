"""
Prompt workflow service.
Implements define -> write -> test -> evaluate -> refine -> ship data flow.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.ai_correction import AiCorrection
from app.models.ai_prompt_experiment import AiPromptExperiment
from app.models.ai_prompt_task import AiPromptTask
from app.models.ai_prompt_version import AiPromptVersion
from app.services.ai.llm_service import llm_service
from app.services.ai.local_model_service import local_model_service
from app.core.model_registry import model_registry
from app.services.ai.prompts import COMMENT_SYSTEM_PROMPT, DANMAKU_SYSTEM_PROMPT
from app.utils.timezone_utils import isoformat_in_app_tz, utc_now

logger = logging.getLogger(__name__)


class PromptWorkflowService:
    """Prompt workflow orchestration."""

    def __init__(self) -> None:
        self.default_tasks = [
            {
                "name": "评论内容治理",
                "prompt_type": "COMMENT",
                "goal": "降低违规与低质评论，提升高质量互动曝光。",
                "metrics": {
                    "category_match_rate": "分类一致率",
                    "score_mae": "评分平均误差",
                    "highlight_match_rate": "高亮命中率",
                },
                "dataset_source": "corrections",
                "sample_min": 20,
            },
            {
                "name": "弹幕内容治理",
                "prompt_type": "DANMAKU",
                "goal": "降低违规与低质弹幕，提升高质量弹幕曝光。",
                "metrics": {
                    "category_match_rate": "分类一致率",
                    "score_mae": "评分平均误差",
                    "highlight_match_rate": "高亮命中率",
                },
                "dataset_source": "corrections",
                "sample_min": 20,
            },
        ]

    def ensure_default_tasks(self, db: Session, admin_id: Optional[int] = None) -> List[AiPromptTask]:
        tasks = db.query(AiPromptTask).order_by(AiPromptTask.id.asc()).all()
        if tasks:
            return tasks

        for task in self.default_tasks:
            db.add(
                AiPromptTask(
                    name=task["name"],
                    prompt_type=task["prompt_type"],
                    goal=task.get("goal", ""),
                    metrics=task.get("metrics", {}),
                    dataset_source=task.get("dataset_source", "corrections"),
                    sample_min=task.get("sample_min", 20),
                    is_active=True,
                    created_by=admin_id,
                    updated_by=admin_id,
                )
            )
        db.commit()
        return db.query(AiPromptTask).order_by(AiPromptTask.id.asc()).all()

    def _prompt_type_to_content_type(self, prompt_type: str) -> str:
        mapping = {"COMMENT": "comment", "DANMAKU": "danmaku"}
        key = (prompt_type or "").upper()
        if key not in mapping:
            raise ValueError(f"Unsupported prompt_type: {prompt_type}")
        return mapping[key]

    def _get_fallback_prompt(self, prompt_type: str) -> str:
        if prompt_type == "DANMAKU":
            return DANMAKU_SYSTEM_PROMPT
        return COMMENT_SYSTEM_PROMPT

    def _safe_score(self, value: Any, default: int = 0) -> int:
        try:
            return int(round(float(value)))
        except Exception:
            return default

    def _normalize_text(self, value: Any) -> str:
        return str(value).strip().lower() if value is not None else ""

    async def _run_single_inference(
        self,
        content: str,
        content_type: str,
        system_prompt: str,
        model_source: str,
    ) -> Optional[Dict[str, Any]]:
        source = model_source.lower()
        if source == "local":
            return await local_model_service.predict(content, content_type, system_prompt=system_prompt)
        if source == "cloud":
            model_config = model_registry.get_model("cloud_text")
            if not model_config:
                return None
            return await llm_service._call_cloud_model(content, system_prompt, model_config)

        for model_type in model_registry.get_text_model_priority():
            if model_type == "local_text":
                result = await local_model_service.predict(content, content_type, system_prompt=system_prompt)
            else:
                model_config = model_registry.get_model("cloud_text")
                if not model_config:
                    result = None
                else:
                    result = await llm_service._call_cloud_model(content, system_prompt, model_config)
            if result:
                return result
        return None

    def _compute_metrics(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        candidate_matches = []
        active_matches = []
        candidate_score_diffs = []
        active_score_diffs = []
        candidate_highlight = []
        active_highlight = []
        candidate_inappropriate = []
        active_inappropriate = []
        consistency_matches = []
        score_diff_between = []

        for sample in samples:
            gt = sample.get("ground_truth") or {}
            candidate = sample.get("candidate")
            active = sample.get("active")

            gt_category = self._normalize_text(gt.get("category") or gt.get("label"))
            gt_score = self._safe_score(gt.get("score"), default=0)
            gt_highlight = bool(gt.get("is_highlight"))
            gt_inappropriate = bool(gt.get("is_inappropriate"))

            if candidate:
                cand_category = self._normalize_text(candidate.get("category") or candidate.get("label"))
                cand_score = self._safe_score(candidate.get("score"), default=0)
                candidate_matches.append(cand_category == gt_category and gt_category != "")
                candidate_score_diffs.append(abs(cand_score - gt_score))
                candidate_highlight.append(bool(candidate.get("is_highlight")) == gt_highlight)
                candidate_inappropriate.append(bool(candidate.get("is_inappropriate")) == gt_inappropriate)

            if active:
                act_category = self._normalize_text(active.get("category") or active.get("label"))
                act_score = self._safe_score(active.get("score"), default=0)
                active_matches.append(act_category == gt_category and gt_category != "")
                active_score_diffs.append(abs(act_score - gt_score))
                active_highlight.append(bool(active.get("is_highlight")) == gt_highlight)
                active_inappropriate.append(bool(active.get("is_inappropriate")) == gt_inappropriate)

            if candidate and active:
                cand_category = self._normalize_text(candidate.get("category") or candidate.get("label"))
                act_category = self._normalize_text(active.get("category") or active.get("label"))
                cand_score = self._safe_score(candidate.get("score"), default=0)
                act_score = self._safe_score(active.get("score"), default=0)
                consistency_matches.append(cand_category == act_category and cand_category != "")
                score_diff_between.append(abs(cand_score - act_score))

        def _rate(values: List[bool]) -> float:
            if not values:
                return 0.0
            return round(sum(1 for v in values if v) / len(values), 4)

        def _avg(values: List[int]) -> float:
            if not values:
                return 0.0
            return round(sum(values) / len(values), 3)

        candidate_rate = _rate(candidate_matches)
        active_rate = _rate(active_matches)
        candidate_mae = _avg(candidate_score_diffs)
        active_mae = _avg(active_score_diffs)

        delta_category = round(candidate_rate - active_rate, 4)
        delta_mae = round(active_mae - candidate_mae, 3)

        recommendation = {
            "action": "refine",
            "reason": "候选版本仍需优化后再发布。",
            "delta_category_match": delta_category,
            "delta_score_mae": delta_mae,
        }
        if candidate_rate >= active_rate + 0.05 and delta_mae >= 1:
            recommendation = {
                "action": "publish",
                "reason": "候选版本在分类一致性与评分误差上优于当前版本。",
                "delta_category_match": delta_category,
                "delta_score_mae": delta_mae,
            }
        elif abs(delta_category) <= 0.03 and abs(delta_mae) <= 1:
            recommendation = {
                "action": "monitor",
                "reason": "候选版本与当前版本表现接近，可继续观察或补充样本。",
                "delta_category_match": delta_category,
                "delta_score_mae": delta_mae,
            }

        return {
            "candidate": {
                "category_match_rate": candidate_rate,
                "score_mae": candidate_mae,
                "highlight_match_rate": _rate(candidate_highlight),
                "inappropriate_match_rate": _rate(candidate_inappropriate),
            },
            "active": {
                "category_match_rate": active_rate,
                "score_mae": active_mae,
                "highlight_match_rate": _rate(active_highlight),
                "inappropriate_match_rate": _rate(active_inappropriate),
            },
            "comparison": {
                "consistency_rate": _rate(consistency_matches),
                "avg_score_diff": _avg(score_diff_between),
                "delta_category_match": delta_category,
                "delta_score_mae": delta_mae,
            },
            "recommendation": recommendation,
        }

    async def run_prompt_test(
        self,
        db: Session,
        candidate_version_id: int,
        sample_limit: int = 50,
        model_source: str = "auto",
        dataset_source: str = "corrections",
        task_id: Optional[int] = None,
        admin_id: Optional[int] = None,
        save_experiment: bool = True,
    ) -> Dict[str, Any]:
        candidate = db.query(AiPromptVersion).filter(
            AiPromptVersion.id == candidate_version_id
        ).first()
        if not candidate:
            raise ValueError("Candidate prompt version not found")

        prompt_type = candidate.prompt_type
        content_type = self._prompt_type_to_content_type(prompt_type)

        active_version = db.query(AiPromptVersion).filter(
            AiPromptVersion.prompt_type == prompt_type,
            AiPromptVersion.is_active == True,
        ).first()

        active_prompt = active_version.prompt_content if active_version else self._get_fallback_prompt(prompt_type)

        if dataset_source != "corrections":
            dataset_source = "corrections"

        corrections = (
            db.query(AiCorrection)
            .filter(AiCorrection.content_type == content_type)
            .order_by(AiCorrection.created_at.desc())
            .limit(sample_limit)
            .all()
        )
        if not corrections:
            raise ValueError("No correction samples available for testing")

        samples: List[Dict[str, Any]] = []
        for corr in corrections:
            ground_truth = corr.corrected_result or corr.original_result or {}
            candidate_result = await self._run_single_inference(
                corr.content, content_type, candidate.prompt_content, model_source
            )
            active_result = await self._run_single_inference(
                corr.content, content_type, active_prompt, model_source
            )

            samples.append(
                {
                    "id": corr.id,
                    "content_preview": (corr.content or "")[:160],
                    "ground_truth": ground_truth,
                    "candidate": candidate_result,
                    "active": active_result,
                }
            )

        metrics = self._compute_metrics(samples)
        comparison = metrics.get("comparison", {})

        consistency_rate = comparison.get("consistency_rate", 0.0)
        avg_score_diff = comparison.get("avg_score_diff", 0.0)
        estimated_cost = 0.0
        if model_source.lower() == "cloud":
            estimated_cost = round(len(samples) * 2 * 0.001, 4)

        experiment = None
        if save_experiment:
            experiment = AiPromptExperiment(
                task_id=task_id,
                prompt_type=prompt_type,
                candidate_version_id=candidate.id,
                active_version_id=active_version.id if active_version else None,
                model_source=model_source,
                dataset_source=dataset_source,
                sample_limit=sample_limit,
                sample_count=len(samples),
                metrics=metrics,
                sample_details=samples[:20],
                status="completed",
                created_by=admin_id,
            )
            db.add(experiment)
            db.commit()
            db.refresh(experiment)

        return {
            "experiment_id": experiment.id if experiment else None,
            "candidate_version_id": candidate.id,
            "active_version_id": active_version.id if active_version else None,
            "sample_count": len(samples),
            "consistency_rate": consistency_rate,
            "avg_score_diff": avg_score_diff,
            "estimated_cost": estimated_cost,
            "metrics": metrics,
            "recommendation": metrics.get("recommendation", {}),
            "test_timestamp": isoformat_in_app_tz(utc_now()),
        }


prompt_workflow_service = PromptWorkflowService()
