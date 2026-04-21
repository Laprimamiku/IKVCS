"""用户兴趣画像服务（轻量）"""
import logging
from typing import Dict
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.interest import UserInterest

logger = logging.getLogger(__name__)


class InterestProfileService:
    """管理 user_interests 的读写"""

    @staticmethod
    def adjust_interest(
        db: Session,
        user_id: int,
        category_id: int | None,
        delta: int,
    ) -> None:
        """按分类调整兴趣权重（upsert），权重不低于 0。"""
        if not category_id or delta == 0:
            return

        record = db.query(UserInterest).filter(
            UserInterest.user_id == user_id,
            UserInterest.category_id == category_id,
        ).first()

        if record:
            record.weight = max(0, int(record.weight or 0) + int(delta))
            record.updated_at = datetime.utcnow()
            return

        if delta > 0:
            db.add(UserInterest(
                user_id=user_id,
                category_id=category_id,
                weight=int(delta),
            ))

    @staticmethod
    def get_top_interest_weights(
        db: Session,
        user_id: int,
        top_n: int = 3,
    ) -> Dict[int, int]:
        """获取用户 TopN 分类兴趣权重映射：{category_id: weight}"""
        rows = db.query(UserInterest).filter(
            UserInterest.user_id == user_id,
            UserInterest.weight > 0,
        ).order_by(
            desc(UserInterest.weight),
            desc(UserInterest.updated_at),
        ).limit(top_n).all()

        return {int(row.category_id): int(row.weight or 0) for row in rows}
