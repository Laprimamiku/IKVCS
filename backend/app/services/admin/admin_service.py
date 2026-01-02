"""
管理员服务层
封装管理员相关的业务逻辑
"""
from sqlalchemy.orm import Session
from typing import List, Tuple
from fastapi import HTTPException, status
from datetime import datetime

from app.repositories.report_repository import ReportRepository
from app.repositories.video_repository import VideoRepository
from app.repositories.comment_repository import CommentRepository
from app.repositories.danmaku_repository import DanmakuRepository
from app.models.report import Report
from app.models.video import Video
from app.models.comment import Comment
from app.models.danmaku import Danmaku
from app.core.exceptions import ResourceNotFoundException


class AdminService:
    """管理员服务"""
    
    @staticmethod
    def get_reports(
        db: Session,
        report_status: int = 0,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Report], int]:
        """
        获取举报列表
        
        Args:
            db: 数据库会话
            report_status: 举报状态（0=待处理,1=已处理,2=已忽略）
            page: 页码
            page_size: 每页数量
            
        Returns:
            Tuple[List[Report], int]: (举报列表, 总数)
        """
        from sqlalchemy.orm import joinedload
        from sqlalchemy import desc
        
        query = db.query(Report).filter(Report.status == report_status)
        total = query.count()
        offset = (page - 1) * page_size
        
        reports = (
            query.options(joinedload(Report.reporter))
            .order_by(desc(Report.created_at))
            .offset(offset)
            .limit(page_size)
            .all()
        )
        
        return reports, total
    
    @staticmethod
    def handle_report(
        db: Session,
        report_id: int,
        action: str,
        admin_id: int,
        admin_note: str = None
    ) -> None:
        """
        处理举报
        
        Args:
            db: 数据库会话
            report_id: 举报ID
            action: 操作类型（delete_target/ignore）
            admin_id: 管理员ID
            admin_note: 管理员备注
            
        Raises:
            ResourceNotFoundException: 举报不存在
            HTTPException: 无效操作
        """
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise ResourceNotFoundException(resource="举报", resource_id=report_id)
        
        if action == "delete_target":
            # 删除目标内容
            if report.target_type == "VIDEO":
                video = VideoRepository.get_by_id(db, report.target_id)
                if video:
                    video.status = 4  # 4 表示已删除
            elif report.target_type == "COMMENT":
                comment = CommentRepository.get(db, report.target_id)
                if comment:
                    comment.is_deleted = True
            elif report.target_type == "DANMAKU":
                danmaku = DanmakuRepository.get_by_id(db, report.target_id)
                if danmaku:
                    danmaku.is_deleted = True
            
            report.status = 1  # 已处理
            report.admin_note = admin_note or "管理员删除了违规内容"
        
        elif action == "ignore":
            report.status = 2  # 已忽略
            report.admin_note = admin_note or "管理员判定无违规"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效操作"
            )
        
        report.handler_id = admin_id
        report.handled_at = datetime.utcnow()
        db.commit()





