"""
举报 Repository
提供举报相关的数据访问方法
"""
from typing import Optional, List, Tuple
from datetime import datetime

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.core.repository import BaseRepository
from app.models.report import Report
from app.schemas.interaction import ReportCreate


class ReportRepository(BaseRepository):
    """举报 Repository"""
    model = Report

    # =========================
    # 创建 / 存在性检查
    # =========================

    @classmethod
    def create(
        cls,
        db: Session,
        report_in: ReportCreate,
        reporter_id: int
    ) -> Report:
        """
        创建举报记录
        """
        db_report = Report(
            reporter_id=reporter_id,
            target_type=report_in.target_type,
            target_id=report_in.target_id,
            reason=report_in.reason,
            description=report_in.description,
            status=0  # 0=待处理
        )
        db.add(db_report)
        db.commit()
        db.refresh(db_report)
        return db_report

    @classmethod
    def exists(
        cls,
        db: Session,
        reporter_id: int,
        target_type: str,
        target_id: int
    ) -> bool:
        """
        检查用户是否已经举报过该内容（仅检查待处理的举报）
        """
        return db.query(Report).filter(
            Report.reporter_id == reporter_id,
            Report.target_type == target_type,
            Report.target_id == target_id,
            Report.status == 0
        ).first() is not None

    # =========================
    # 查询相关
    # =========================

    @classmethod
    def get_by_id_with_relations(
        cls,
        db: Session,
        report_id: int
    ) -> Optional[Report]:
        """
        根据ID查询举报（包含举报人、处理人）
        """
        return db.query(Report).options(
            joinedload(Report.reporter),
            joinedload(Report.handler)
        ).filter(Report.id == report_id).first()

    @classmethod
    def get_pending_reports(
        cls,
        db: Session,
        page: int = 1,
        page_size: int = 20,
        target_type: Optional[str] = None
    ) -> Tuple[List[Report], int]:
        """
        获取待处理的举报列表
        """
        query = db.query(Report).options(
            joinedload(Report.reporter)
        ).filter(Report.status == 0)

        if target_type:
            query = query.filter(Report.target_type == target_type)

        total = query.count()
        offset = (page - 1) * page_size
        reports = (
            query.order_by(desc(Report.created_at))
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return reports, total

    @classmethod
    def get_user_reports(
        cls,
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Report], int]:
        """
        获取用户提交的举报列表
        """
        query = db.query(Report).filter(Report.reporter_id == user_id)

        total = query.count()
        offset = (page - 1) * page_size
        reports = (
            query.order_by(desc(Report.created_at))
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return reports, total

    @classmethod
    def get_target_reports(
        cls,
        db: Session,
        target_type: str,
        target_id: int
    ) -> List[Report]:
        """
        获取特定目标的所有举报
        """
        return (
            db.query(Report)
            .options(joinedload(Report.reporter))
            .filter(
                Report.target_type == target_type,
                Report.target_id == target_id
            )
            .order_by(desc(Report.created_at))
            .all()
        )

    @classmethod
    def check_duplicate_report(
        cls,
        db: Session,
        reporter_id: int,
        target_type: str,
        target_id: int
    ) -> bool:
        """
        检查用户是否已举报过该目标（不区分状态）
        """
        return db.query(Report).filter(
            Report.reporter_id == reporter_id,
            Report.target_type == target_type,
            Report.target_id == target_id
        ).first() is not None

    # =========================
    # 处理 / 统计
    # =========================

    @classmethod
    def handle_report(
        cls,
        db: Session,
        report_id: int,
        handler_id: int,
        status: int,
        admin_note: Optional[str] = None
    ) -> bool:
        """
        处理举报
        status: 1=已处理, 2=已忽略
        """
        report = cls.get_by_id(db, report_id)
        if not report:
            return False

        report.status = status
        report.handler_id = handler_id
        report.admin_note = admin_note
        report.handled_at = datetime.utcnow()
        db.commit()
        return True

    @classmethod
    def get_report_statistics(cls, db: Session) -> dict:
        """
        获取举报统计信息
        """
        total = db.query(Report).count()
        pending = db.query(Report).filter(Report.status == 0).count()
        handled = db.query(Report).filter(Report.status == 1).count()
        ignored = db.query(Report).filter(Report.status == 2).count()

        return {
            "total": total,
            "pending": pending,
            "handled": handled,
            "ignored": ignored
        }
