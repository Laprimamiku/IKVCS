"""
文件处理工具函数

提供文件相关的通用操作
"""
import os
import hashlib
from typing import Optional
from pathlib import Path


def get_file_hash(file_path: str, chunk_size: int = 8192) -> str:
    """
    计算文件哈希值（SHA256）
    
    Args:
        file_path: 文件路径
        chunk_size: 读取块大小
        
    Returns:
        str: 文件哈希值
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()


def ensure_directory_exists(directory: str) -> None:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        directory: 目录路径
    """
    Path(directory).mkdir(parents=True, exist_ok=True)


def get_file_extension(filename: str) -> str:
    """
    获取文件扩展名
    
    Args:
        filename: 文件名
        
    Returns:
        str: 文件扩展名（不含点号）
    """
    return os.path.splitext(filename)[1][1:].lower()


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小
    
    Args:
        size_bytes: 文件大小（字节）
        
    Returns:
        str: 格式化后的文件大小（如 "1.5 MB"）
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

