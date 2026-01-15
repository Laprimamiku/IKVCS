"""
视频相关常量定义

统一管理视频状态、审核状态等常量，避免魔法数字
"""
from enum import IntEnum


class VideoStatus(IntEnum):
    """视频状态枚举"""
    TRANSCODING = 0  # 转码中
    REVIEWING = 1    # 审核中
    PUBLISHED = 2    # 已发布
    REJECTED = 3     # 拒绝
    DELETED = 4      # 软删除


class ReviewStatus(IntEnum):
    """审核状态枚举"""
    PENDING = 0   # 待审核
    APPROVED = 1  # 通过
    REJECTED = 2  # 拒绝


class ReportStatus(IntEnum):
    """举报状态枚举"""
    PENDING = 0   # 待处理
    PROCESSED = 1 # 已处理
    IGNORED = 2   # 已忽略


# 视频状态映射（用于显示）
VIDEO_STATUS_MAP = {
    VideoStatus.TRANSCODING: "转码中",
    VideoStatus.REVIEWING: "审核中",
    VideoStatus.PUBLISHED: "已发布",
    VideoStatus.REJECTED: "拒绝",
    VideoStatus.DELETED: "已删除"
}

# 审核状态映射（用于显示）
REVIEW_STATUS_MAP = {
    ReviewStatus.PENDING: "待审核",
    ReviewStatus.APPROVED: "通过",
    ReviewStatus.REJECTED: "拒绝"
}

# 举报状态映射（用于显示）
REPORT_STATUS_MAP = {
    ReportStatus.PENDING: "待处理",
    ReportStatus.PROCESSED: "已处理",
    ReportStatus.IGNORED: "已忽略"
}

