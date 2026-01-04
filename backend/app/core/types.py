"""
通用类型定义
用于替代 Dict[str, Any] 等类型，提高类型安全性
"""
from typing import TypedDict, Dict, Any, Union, List
from typing_extensions import NotRequired


class SubtitleEntry(TypedDict):
    """字幕条目类型定义"""
    start_time: float
    end_time: float
    text: str


class OutlineEntry(TypedDict):
    """视频大纲条目类型定义"""
    title: str
    start_time: float
    description: NotRequired[str]
    key_points: NotRequired[List[str]]  # 关键知识点/内容点列表
    end_time: NotRequired[float]  # 章节结束时间


# 用于 Repository filters 的类型（动态筛选条件）
FilterDict = Dict[str, Union[str, int, float, bool, None]]


# ==================== AI 分析结果类型 ====================

class AIContentAnalysisResult(TypedDict):
    """AI 内容分析结果类型定义"""
    score: int  # 评分 (0-100)
    category: str  # 分类（如：普通、优质、低质等）
    label: str  # 标签
    reason: str  # 分析原因
    is_highlight: bool  # 是否高亮
    is_inappropriate: bool  # 是否不当内容


class ExpertResult(TypedDict):
    """多智能体专家结果类型定义"""
    score: int
    category: str
    label: str
    reason: str
    is_highlight: bool
    is_inappropriate: bool
    confidence: NotRequired[float]  # 置信度


class ErrorPattern(TypedDict):
    """错误模式类型定义"""
    pattern: str  # 错误模式描述
    frequency: int  # 出现频率
    examples: List[str]  # 示例


class CorrectionRecord(TypedDict):
    """修正记录类型定义"""
    id: int
    original_result: AIContentAnalysisResult
    corrected_result: AIContentAnalysisResult
    correction_reason: str
    created_at: str

