"""
JSON 处理工具函数

提供 JSON 解析和序列化的通用操作
"""
import json
import logging
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)


def safe_json_loads(
    json_str: Optional[str],
    default: Any = None
) -> Optional[Dict[str, Any]]:
    """
    安全解析 JSON 字符串
    
    支持字符串和字典类型的输入，自动处理异常
    
    Args:
        json_str: JSON 字符串或字典对象
        default: 解析失败时的默认值
        
    Returns:
        Optional[Dict[str, Any]]: 解析后的字典，失败返回 default
        
    使用示例：
        # 从字符串解析
        data = safe_json_loads('{"key": "value"}')
        
        # 从字典（已经是字典，直接返回）
        data = safe_json_loads({"key": "value"})
        
        # 解析失败返回默认值
        data = safe_json_loads("invalid json", default={})
    """
    if json_str is None:
        return default
    
    # 如果已经是字典，直接返回
    if isinstance(json_str, dict):
        return json_str
    
    # 如果是字符串，尝试解析
    if isinstance(json_str, str):
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug(f"JSON 解析失败: {e}")
            return default
    
    # 其他类型，返回默认值
    return default


def safe_json_dumps(
    obj: Any,
    default: str = "{}",
    ensure_ascii: bool = False
) -> str:
    """
    安全序列化对象为 JSON 字符串
    
    自动处理异常，返回默认值
    
    Args:
        obj: 要序列化的对象
        default: 序列化失败时的默认值
        ensure_ascii: 是否确保 ASCII 编码（默认 False，支持中文）
        
    Returns:
        str: JSON 字符串，失败返回 default
        
    使用示例：
        json_str = safe_json_dumps({"key": "value"})
        json_str = safe_json_dumps({"中文": "测试"}, ensure_ascii=False)
    """
    try:
        return json.dumps(obj, ensure_ascii=ensure_ascii)
    except (TypeError, ValueError) as e:
        logger.debug(f"JSON 序列化失败: {e}")
        return default


def parse_review_report(
    review_report: Optional[str],
    default: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    解析审核报告 JSON 字符串（专用方法）
    
    这是 safe_json_loads 的别名，用于审核报告解析场景
    
    Args:
        review_report: 审核报告 JSON 字符串或字典
        default: 解析失败时的默认值（默认 None）
        
    Returns:
        Optional[Dict[str, Any]]: 解析后的审核报告字典
    """
    return safe_json_loads(review_report, default=default)


def parse_json_field(json_str_or_dict: Optional[Any]) -> Optional[Dict[str, Any]]:
    """
    安全地解析 JSON 字符串或直接返回字典。
    如果输入是 None 或解析失败，返回 None。
    
    Args:
        json_str_or_dict: JSON 字符串或字典对象
        
    Returns:
        Optional[Dict[str, Any]]: 解析后的字典，失败返回 None
    """
    return safe_json_loads(json_str_or_dict, default=None)


def dump_json_field(data: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    安全地将字典转换为 JSON 字符串。
    如果输入是 None，返回 None。
    
    Args:
        data: 要序列化的字典对象
        
    Returns:
        Optional[str]: JSON 字符串，失败返回 None
    """
    if data is None:
        return None
    try:
        return json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        logger.error(f"序列化 JSON 字段失败: {e}, 原始数据: {data}")
        return None

