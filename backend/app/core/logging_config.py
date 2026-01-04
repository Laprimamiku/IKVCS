"""
日志配置模块

提供统一的日志格式和颜色输出
"""
import logging
import sys
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """
    带颜色的日志格式化器（仅用于控制台输出）
    
    颜色映射：
    - DEBUG: 灰色
    - INFO: 绿色
    - WARNING: 黄色
    - ERROR: 红色
    - CRITICAL: 红色加粗
    """
    
    # ANSI 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    def format(self, record: logging.LogRecord) -> str:
        # 获取日志级别名称
        levelname = record.levelname
        
        # 添加颜色
        if levelname in self.COLORS:
            colored_levelname = f"{self.COLORS[levelname]}{self.BOLD}[{levelname:8s}]{self.RESET}"
        else:
            colored_levelname = f"[{levelname:8s}]"
        
        # 格式化时间
        asctime = self.formatTime(record, self.datefmt)
        
        # 构建格式化的日志消息
        # 格式: [时间] [级别] [模块] 消息
        message = f"{self.COLORS.get('INFO', '')}[{asctime}]{self.RESET} {colored_levelname} {self.COLORS.get('INFO', '')}[{record.module:15s}]{self.RESET} {record.getMessage()}"
        
        # 如果有异常信息，添加堆栈跟踪
        if record.exc_info:
            message += '\n' + self.formatException(record.exc_info)
        
        return message


class PlainFormatter(logging.Formatter):
    """
    纯文本日志格式化器（用于文件输出）
    
    格式: [时间] [级别] [模块] 消息
    """
    
    def format(self, record: logging.LogRecord) -> str:
        # 格式化时间
        asctime = self.formatTime(record, self.datefmt)
        
        # 构建格式化的日志消息
        message = f"[{asctime}] [{record.levelname:8s}] [{record.module:15s}] {record.getMessage()}"
        
        # 如果有异常信息，添加堆栈跟踪
        if record.exc_info:
            message += '\n' + self.formatException(record.exc_info)
        
        return message


def setup_logging(debug: bool = False, log_file: Optional[str] = None) -> None:
    """
    配置日志系统
    
    Args:
        debug: 是否启用调试模式
        log_file: 日志文件路径（可选）
    """
    # 设置日志级别
    level = logging.DEBUG if debug else logging.INFO
    
    # 创建根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 清除现有的处理器
    root_logger.handlers.clear()
    
    # 控制台处理器（带颜色）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = ColoredFormatter(
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器（纯文本）
    if log_file:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10485760,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_formatter = PlainFormatter(
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # 设置第三方库的日志级别（避免过多输出）
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

