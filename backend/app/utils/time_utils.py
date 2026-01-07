"""
时间处理工具函数

提供时间相关的通用操作
"""
from datetime import datetime, timedelta
from typing import Optional

from app.utils.timezone_utils import ensure_utc, utc_now

def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化 datetime 对象为字符串
    
    Args:
        dt: datetime 对象
        format_str: 格式字符串
        
    Returns:
        str: 格式化后的时间字符串
    """
    return dt.strftime(format_str)


def parse_datetime(dt_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """
    解析时间字符串为 datetime 对象
    
    Args:
        dt_str: 时间字符串
        format_str: 格式字符串
        
    Returns:
        Optional[datetime]: datetime 对象，解析失败返回 None
    """
    try:
        return datetime.strptime(dt_str, format_str)
    except ValueError:
        return None


def get_time_ago(dt: datetime) -> str:
    """
    获取相对时间描述（如 "2小时前"）
    
    Args:
        dt: datetime 对象
        
    Returns:
        str: 相对时间描述
    """
    now = utc_now()
    delta = now - ensure_utc(dt)
    
    if delta.days > 365:
        years = delta.days // 365
        return f"{years}年前"
    elif delta.days > 30:
        months = delta.days // 30
        return f"{months}个月前"
    elif delta.days > 0:
        return f"{delta.days}天前"
    elif delta.seconds > 3600:
        hours = delta.seconds // 3600
        return f"{hours}小时前"
    elif delta.seconds > 60:
        minutes = delta.seconds // 60
        return f"{minutes}分钟前"
    else:
        return "刚刚"

