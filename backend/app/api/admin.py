"""
管理后台 API
需求：6.1-6.3, 14.1-14.5, 15.1-15.5, 16.1-16.5, 17.1-17.4, 20.1-20.4
"""
from fastapi import APIRouter

router = APIRouter()

# TODO: 分类管理
# TODO: 实现创建分类 API (POST /categories)
# TODO: 实现分类列表 API (GET /categories)

# TODO: 视频审核
# TODO: 实现待审核列表 API (GET /videos/pending)
# TODO: 实现通过审核 API (POST /videos/{video_id}/approve)
# TODO: 实现拒绝审核 API (POST /videos/{video_id}/reject)
# TODO: 实现软删除视频 API (DELETE /videos/{video_id})

# TODO: 用户管理
# TODO: 实现用户列表 API (GET /users)
# TODO: 实现封禁用户 API (POST /users/{user_id}/ban)
# TODO: 实现解封用户 API (POST /users/{user_id}/unban)
# TODO: 实现用户详情 API (GET /users/{user_id})

# TODO: 举报处理
# TODO: 实现举报列表 API (GET /reports)
# TODO: 实现处理举报 API (POST /reports/{report_id}/handle)

# TODO: 数据统计
# TODO: 实现统计概览 API (GET /statistics/overview)
# TODO: 实现视频趋势 API (GET /statistics/videos/{video_id}/trends)
# TODO: 实现分类分布 API (GET /statistics/categories)

# TODO: LLM 重新分析
# TODO: 实现重新分析 API (POST /videos/{video_id}/reanalyze)
