"""
哈希计算工具函数

提供文件哈希、字符串哈希等通用操作
"""
import hashlib
from typing import Optional


def calculate_file_hash(file_path: str, algorithm: str = "sha256", chunk_size: int = 8192) -> str:
    """
    计算文件哈希值
    
    Args:
        file_path: 文件路径
        algorithm: 哈希算法（sha256, md5, sha1等）
        chunk_size: 读取块大小
        
    Returns:
        str: 文件哈希值（十六进制字符串）
    """
    hash_obj = hashlib.new(algorithm)
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def calculate_string_hash(content: str, algorithm: str = "sha256") -> str:
    """
    计算字符串哈希值
    
    Args:
        content: 字符串内容
        algorithm: 哈希算法（sha256, md5, sha1等）
        
    Returns:
        str: 字符串哈希值（十六进制字符串）
    """
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(content.encode('utf-8'))
    return hash_obj.hexdigest()


def calculate_bytes_hash(data: bytes, algorithm: str = "sha256") -> str:
    """
    计算字节数据的哈希值
    
    Args:
        data: 字节数据
        algorithm: 哈希算法（sha256, md5, sha1等）
        
    Returns:
        str: 数据哈希值（十六进制字符串）
    """
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(data)
    return hash_obj.hexdigest()


def verify_file_hash(file_path: str, expected_hash: str, algorithm: str = "sha256") -> bool:
    """
    验证文件哈希值是否匹配
    
    Args:
        file_path: 文件路径
        expected_hash: 期望的哈希值
        algorithm: 哈希算法
        
    Returns:
        bool: 是否匹配
    """
    try:
        actual_hash = calculate_file_hash(file_path, algorithm)
        return actual_hash.lower() == expected_hash.lower()
    except Exception:
        return False

