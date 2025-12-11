"""
举报 Repository
提供举报相关的数据访问方法
"""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from datetime import datetime

from app.core.repository import BaseRepository
from app.models.report import Report


class ReportRepository(BaseRepository):
    """举报 Repository"""
    model = Report
    
    @classmethod
    def get_by_id_with_relations(
        cls,
        db: Session,
        report_id: int
    ) -> Optional[Report]:
        """
        根据ID查询举报（包含关联数据）
        
        Args:
            db: 数据库会话
            report_id: 举报ID
            
        Returns:
            Optional[Report]: 举报对象，不存在返回None
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
        
        Args:
            db: 数据库会话
            page: 页码（从1开始）
            page_size: 每页数量
            target_type: 举报目标类型（VIDEO/COMMENT/DANMAKU）
            
        Returns:
            Tuple[List[Report], int]: (举报列表, 总数)
        """
        # 基础查询：待处理的举报（status=0）
        query = db.query(Report).options(
            joinedload(Report.reporter)
        ).filter(Report.status == 0)
        
        # 按目标类型筛选
        if target_type:
            query = query.filter(Report.target_type == target_type)
        
        # 获取总数
        total = query.count()
        
        # 分页查询（按创建时间倒序）
        offset = (page - 1) * page_size
        reports = query.order_by(desc(Report.created_at)).offset(offset).limit(page_size).all()
        
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
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            page: 页码（从1开始）
            page_size: 每页数量
            
        Returns:
            Tuple[List[Report], int]: (举报列表, 总数)
        """
        # 基础查询：用户提交的举报
        query = db.query(Report).filter(Report.reporter_id == user_id)
        
        # 获取总数
        total = query.count()
        
        # 分页查询（按创建时间倒序）
        offset = (page - 1) * page_size
        reports = query.order_by(desc(Report.created_at)).offset(offset).limit(page_size).all()
        
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
        
        Args:
            db: 数据库会话
            target_type: 举报目标类型
            target_id: 举报目标ID
            
        Returns:
            List[Report]: 举报列表
        """
        return db.query(Report).options(
            joinedload(Report.reporter)
        ).filter(
            Report.target_type == target_type,
            Report.target_id == target_id
        ).order_by(desc(Report.created_at)).all()
    
    @classmethod
    def check_duplicate_report(
        cls,
        db: Session,
        reporter_id: int,
        target_type: str,
        target_id: int
    ) -> bool:
        """
        检查用户是否已举报过该目标
        
        Args:
            db: 数据库会话
            reporter_id: 举报人ID
            target_type: 举报目标类型
            target_id: 举报目标ID
            
        Returns:
            bool: 是否已举报
        """
        return db.query(Report).filter(
            Report.reporter_id == reporter_id,
            Report.target_type == target_type,
            Report.target_id == target_id
        ).first() is not None
    
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
        
        Args:
            db: 数据库会话
            report_id: 举报ID
            handler_id: 处理人ID
            status: 处理状态（1=已处理, 2=已忽略）
            admin_note: 管理员备注
            
        Returns:
            bool: 是否成功
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
    def get_report_statistics(
        cls,
        db: Session
    ) -> dict:
        """
        获取举报统计信息
        
        Args:
            db: 数据库会话
            
        Returns:
            dict: 统计信息
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
