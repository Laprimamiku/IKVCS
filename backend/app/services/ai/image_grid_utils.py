"""
图片网格拼接工具

功能：
1. 将多张图片拼接成网格图（3×3）
2. 统一图片尺寸，避免变形
3. 支持批量图片处理
"""

import os
import logging
from typing import List, Tuple, Optional
from PIL import Image

logger = logging.getLogger(__name__)


def create_image_grid(
    image_paths: List[str], 
    grid_size: Tuple[int, int] = (3, 3),
    output_path: Optional[str] = None
) -> Optional[Image.Image]:
    """
    将多张图片拼接成网格图
    
    Args:
        image_paths: 图片路径列表
        grid_size: 网格大小 (rows, cols)，默认3×3
        output_path: 可选，保存拼接后的图片路径
    
    Returns:
        拼接后的图片对象，失败返回None
    """
    if not image_paths:
        logger.warning("图片路径列表为空")
        return None
    
    rows, cols = grid_size
    max_images = rows * cols
    images_to_process = image_paths[:max_images]
    
    if len(images_to_process) == 0:
        logger.warning("没有可处理的图片")
        return None
    
    try:
        logger.info(f"[ImageGrid] 开始拼接图片网格: 输入{len(image_paths)}张，网格{rows}×{cols}，最大{max_images}张")
        
        # 加载所有图片
        images = []
        for idx, path in enumerate(images_to_process):
            if not os.path.exists(path):
                logger.warning(f"[ImageGrid] 图片不存在 [{idx+1}/{len(images_to_process)}]: {path}")
                continue
            
            try:
                img = Image.open(path)
                original_size = (img.width, img.height)
                # 转换为RGB模式（处理RGBA等格式）
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                images.append(img)
                logger.debug(f"[ImageGrid] 加载图片 [{idx+1}/{len(images_to_process)}]: {os.path.basename(path)} {original_size}")
            except Exception as e:
                logger.error(f"[ImageGrid] 加载图片失败 [{idx+1}/{len(images_to_process)}] {path}: {e}")
                continue
        
        if not images:
            logger.error("[ImageGrid] 没有成功加载的图片，拼接失败")
            return None
        
        logger.info(f"[ImageGrid] 成功加载 {len(images)}/{len(images_to_process)} 张图片")
        
        # 统一图片尺寸（取最大尺寸）
        max_width = max(img.width for img in images)
        max_height = max(img.height for img in images)
        logger.info(f"[ImageGrid] 统一尺寸: {max_width}×{max_height}")
        
        # 调整所有图片到统一尺寸（保持宽高比，填充白色背景）
        resized_images = []
        for idx, img in enumerate(images):
            original_size = (img.width, img.height)
            # 计算缩放比例，保持宽高比
            scale_w = max_width / img.width
            scale_h = max_height / img.height
            scale = min(scale_w, scale_h)  # 取较小的缩放比例，确保图片完整显示
            
            new_width = int(img.width * scale)
            new_height = int(img.height * scale)
            
            # 缩放图片
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 创建白色背景
            final_img = Image.new('RGB', (max_width, max_height), color='white')
            
            # 居中放置图片
            x_offset = (max_width - new_width) // 2
            y_offset = (max_height - new_height) // 2
            final_img.paste(resized_img, (x_offset, y_offset))
            
            resized_images.append(final_img)
            logger.debug(f"[ImageGrid] 调整图片 [{idx+1}/{len(images)}]: {original_size} → {max_width}×{max_height}")
        
        # 如果图片数量不足，用白色图片填充
        fill_count = max_images - len(resized_images)
        if fill_count > 0:
            logger.info(f"[ImageGrid] 图片数量不足，填充 {fill_count} 张白色图片")
            for _ in range(fill_count):
                white_img = Image.new('RGB', (max_width, max_height), color='white')
                resized_images.append(white_img)
        
        # 创建网格图
        grid_width = max_width * cols
        grid_height = max_height * rows
        grid_image = Image.new('RGB', (grid_width, grid_height), color='white')
        logger.info(f"[ImageGrid] 创建网格画布: {grid_width}×{grid_height}")
        
        # 填充图片到网格
        for idx, img in enumerate(resized_images):
            row = idx // cols
            col = idx % cols
            x = col * max_width
            y = row * max_height
            grid_image.paste(img, (x, y))
            logger.debug(f"[ImageGrid] 放置图片 [{idx+1}/{len(resized_images)}]: 位置({row},{col}) 坐标({x},{y})")
        
        # 如果指定了输出路径，保存图片
        if output_path:
            try:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                grid_image.save(output_path, 'JPEG', quality=85)
                file_size = os.path.getsize(output_path) / 1024  # KB
                logger.info(f"[ImageGrid] 网格图已保存: {output_path} ({file_size:.1f} KB)")
            except Exception as e:
                logger.error(f"[ImageGrid] 保存网格图失败: {e}")
        
        logger.info(f"[ImageGrid] ✅ 成功创建网格图: {len(images_to_process)}张图片 → {rows}×{cols}网格 ({grid_width}×{grid_height})")
        return grid_image
        
    except Exception as e:
        logger.error(f"创建网格图失败: {e}", exc_info=True)
        return None


def batch_images(image_paths: List[str], batch_size: int = 9) -> List[List[str]]:
    """
    将图片路径列表分批处理
    
    Args:
        image_paths: 图片路径列表
        batch_size: 每批大小，默认9（3×3网格）
    
    Returns:
        分批后的图片路径列表
    """
    batches = []
    for i in range(0, len(image_paths), batch_size):
        batch = image_paths[i:i + batch_size]
        batches.append(batch)
    return batches

