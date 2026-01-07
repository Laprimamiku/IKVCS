"""
时区/时间工具

说明：
- 数据库存储的 datetime 多为「无时区」(naive)，本项目历史上使用 datetime.utcnow() 写入；
  因此前端看到的时间会比北京时间少 8 小时。
- 这里统一约定：naive datetime 视为 UTC，并在 API 输出时转换为 settings.APP_TIMEZONE（默认 Asia/Shanghai）。
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from app.core.config import settings


def get_app_tz():
    tz_name = getattr(settings, "APP_TIMEZONE", None) or "Asia/Shanghai"
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return timezone(timedelta(hours=8))


def ensure_utc(dt: datetime) -> datetime:
    """将 datetime 转为 UTC aware；naive 一律按 UTC 处理。"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_app_tz(dt: datetime) -> datetime:
    """将 datetime 转为应用时区（settings.APP_TIMEZONE）。"""
    return ensure_utc(dt).astimezone(get_app_tz())


def isoformat_in_app_tz(dt: datetime) -> str:
    """输出为带时区偏移的 ISO8601 字符串（默认 +08:00）。"""
    return to_app_tz(dt).isoformat()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

