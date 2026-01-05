"""
大纲 LLM 调用模块

职责：调用 LLM 提取大纲，支持单次和分段处理
"""
import logging
import asyncio
from typing import List, Optional, Dict, Any, Callable

from app.core.config import settings
from app.services.video.subtitle_parser import SubtitleParser
from app.services.video.outline.outline_parser import parse_llm_response
import httpx

logger = logging.getLogger(__name__)

# 并发控制：限制同时进行的 LLM 请求数量，避免 GPU 负载波动
_llm_semaphore = asyncio.Semaphore(1)  # 同时只允许 1 个 LLM 请求

# 请求冷却时间：避免频繁调用 GPU，减少电流滋滋声
_last_request_time = None
_request_cooldown = 2.0  # 请求之间的最小间隔（秒），给 GPU 足够的冷却时间


def split_subtitles_by_time(
    subtitles: List[Dict[str, Any]],
    segment_duration: int = 600
) -> List[List[Dict[str, Any]]]:
    """
    将字幕按时间分段，每段约 segment_duration 秒（默认10分钟）
    
    Args:
        subtitles: 字幕条目列表
        segment_duration: 每段时长（秒）
        
    Returns:
        List[List[Dict]]: 分段后的字幕列表
    """
    if not subtitles:
        return []
    
    segments = []
    current_segment = []
    segment_start_time = subtitles[0].get('start_time', 0)
    
    for subtitle in subtitles:
        start_time = subtitle.get('start_time', 0)
        
        # 如果当前字幕的开始时间超过当前段的结束时间，开始新段
        if start_time >= segment_start_time + segment_duration:
            if current_segment:
                segments.append(current_segment)
            current_segment = [subtitle]
            segment_start_time = start_time
        else:
            current_segment.append(subtitle)
    
    # 添加最后一段
    if current_segment:
        segments.append(current_segment)
    
    return segments


async def llm_extract_outline(
    full_text: str,
    subtitles: List[Dict[str, Any]],
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> List[Dict[str, Any]]:
    """
    使用 LLM 提取大纲（支持长视频分段处理）
    
    Args:
        full_text: 字幕完整文本
        subtitles: 字幕条目列表（包含时间信息）
        
    Returns:
        List[Dict]: 大纲列表，每个条目包含标题、时间、描述和关键点
    """
    # 计算视频总时长
    video_duration = 0
    if subtitles:
        last_subtitle = subtitles[-1]
        video_duration = last_subtitle.get('end_time', 0)
    
    logger.info(f"[OutlineLLM] 视频总时长: {video_duration:.1f}秒，字幕文本长度: {len(full_text)} 字符")
    
    # 如果视频较短（<15分钟）或文本较短（<8000字符），直接处理
    max_text_length = 8000  # 单次处理的最大文本长度
    max_duration = 900  # 15分钟
    
    if len(full_text) <= max_text_length and video_duration <= max_duration:
        # 短视频，直接处理
        logger.info("[OutlineLLM] 视频较短，使用单次处理模式")
        if progress_callback:
            await progress_callback(30, "正在调用 AI 模型生成大纲...")
        return await llm_extract_outline_single(full_text, subtitles, progress_callback)
    else:
        # 长视频，分段处理
        logger.info(f"[OutlineLLM] 视频较长，使用分段处理模式（每段约10分钟）")
        if progress_callback:
            await progress_callback(20, f"视频较长，将分为多个段落处理...")
        return await llm_extract_outline_segmented(full_text, subtitles, progress_callback)


async def llm_extract_outline_single(
    full_text: str,
    subtitles: List[Dict[str, Any]],
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> List[Dict[str, Any]]:
    """单次处理模式（适用于短视频）"""
    # 限制输入文本长度，但尽量保留更多内容
    max_input_length = 8000
    if len(full_text) > max_input_length:
        logger.warning(f"[OutlineLLM] 文本过长 ({len(full_text)} 字符)，截取前 {max_input_length} 字符")
        full_text = full_text[:max_input_length]
    
    # 计算视频时长（秒）
    video_duration = 0
    if subtitles:
        last_subtitle = subtitles[-1]
        video_duration = last_subtitle.get('end_time', 0)
    
    # 根据视频时长估算章节数量（每3-5分钟一个章节）
    estimated_chapters = max(3, int(video_duration / 180))  # 每3分钟一个章节，最少3个
    estimated_chapters = min(estimated_chapters, 20)  # 最多20个章节
    
    # 根据视频时长确定关键点数量
    video_minutes = video_duration / 60
    if video_minutes <= 3:
        key_points_per_chapter = "1-2个"
        total_key_points = "1-2个"
    elif video_minutes <= 15:
        key_points_per_chapter = "2-3个"
        total_key_points = "5个左右"
    elif video_minutes <= 30:
        key_points_per_chapter = "3-4个"
        total_key_points = "10个左右"
    else:  # > 30分钟
        key_points_per_chapter = "4-5个"
        total_key_points = "15-20个"
    
    prompt = f"""请分析以下视频字幕内容，提取视频的主要章节/主题大纲，并为每个章节生成关键知识点/内容点。

**关键要求（必须严格遵守）：**
1. **视频总时长：{int(video_duration / 60)} 分钟（{int(video_duration)} 秒）**，你必须确保大纲覆盖从开始（0秒）到结束（{int(video_duration)}秒）的整个视频
2. **章节数量：建议生成 {estimated_chapters} 个章节**（每3-5分钟一个章节），确保覆盖整个视频
3. **时间分布：章节时间点必须均匀分布在整个视频中**
   - 第一个章节：0-{int(video_duration * 0.2)}秒
   - 中间章节：均匀分布在 {int(video_duration * 0.2)}-{int(video_duration * 0.8)}秒
   - 最后一个章节：必须在 {int(video_duration * 0.85)}-{int(video_duration * 0.95)}秒之间（不能是最后一秒，应该提前5-15%结束）
4. **禁止只生成前几分钟的大纲**，必须覆盖到视频结束时间（{int(video_duration)}秒）

**每个章节格式要求：**
- **title**: 章节标题（必须基于字幕内容生成，不能使用"开始"、"中间章节"、"最后章节"等通用名称。标题应该概括该章节的核心主题，10字以内，简洁明了）
- **start_time**: 开始时间（秒，必须从字幕内容中准确匹配对应的时间点，不能随意猜测，必须覆盖 0 到 {int(video_duration)} 秒）
- **description**: 章节简要描述（20-50字，必须基于字幕内容，准确概括该章节的主要内容，不能随意编造）
- **key_points**: 关键知识点/内容点列表（每个章节 {key_points_per_chapter} 关键点，整个视频总共约 {total_key_points} 关键点。每个关键点10-20字，必须基于字幕内容，不能随意编造）

**关键点数量规则（重要）：**
- 视频时长 ≤ 3分钟：每个章节1-2个关键点
- 视频时长 ≤ 15分钟：每个章节2-3个关键点（11分钟视频应该有4-5个章节，每个章节2-3个关键点，总共8-15个关键点）
- 视频时长 ≤ 30分钟：每个章节3-4个关键点
- 视频时长 > 30分钟：每个章节4-5个关键点

**注意：关键点数量 = 章节数量 × 每个章节的关键点数。例如11分钟视频有4-5个章节，每个2-3个关键点，总共应该有8-15个关键点。**

**输出要求：**
- **必须返回严格的 JSON 数组格式**，格式如下：
```json
[
    {{
        "title": "章节标题",
        "start_time": 0,
        "description": "章节描述",
        "key_points": ["关键点1", "关键点2"]
    }},
    {{
        "title": "下一个章节标题",
        "start_time": 180,
        "description": "章节描述",
        "key_points": ["关键点1", "关键点2"]
    }}
]
```
- **不要包含 Markdown 代码块标记（不要使用 ```json 或 ```）**
- **不要使用中文字段名（如"开始时间"），必须使用英文字段名（"start_time"）**
- start_time 必须是数字类型，不是字符串
- start_time 必须从字幕内容中准确匹配，不能随意猜测
- **最后一个章节的 start_time 必须在 {int(video_duration * 0.85)}-{int(video_duration * 0.95)}秒之间（不能是最后一秒，应该提前5-15%结束，确保有实际内容）**
- 标题、描述和关键点都必须基于字幕内容，不能随意编造

字幕内容（完整视频字幕）：
{full_text}

请返回 JSON 数组格式的大纲列表，**必须确保覆盖整个视频（0-{int(video_duration)}秒）**，**不要包含任何 Markdown 标记**："""
    
    if progress_callback:
        await progress_callback(50, "正在生成大纲...")
    
    result = await call_llm_for_outline(prompt, subtitles)
    
    if progress_callback:
        await progress_callback(90, "正在处理生成结果...")
    
    return result


async def llm_extract_outline_segmented(
    full_text: str,
    subtitles: List[Dict[str, Any]],
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> List[Dict[str, Any]]:
    """分段处理模式（适用于长视频）"""
    # 将字幕按时间分段（每段约10分钟）
    segments = split_subtitles_by_time(subtitles, segment_duration=600)
    logger.info(f"[OutlineLLM] 视频分为 {len(segments)} 段进行处理")
    
    if progress_callback:
        await progress_callback(25, f"视频分为 {len(segments)} 段，开始逐段处理...")
    
    all_outlines = []
    
    # 逐段处理
    for segment_idx, segment in enumerate(segments):
        if not segment:
            continue
        
        # 提取该段的文本
        segment_text = SubtitleParser.extract_text_only(segment)
        if len(segment_text) < 50:
            continue
        
        segment_start_time = segment[0].get('start_time', 0)
        segment_end_time = segment[-1].get('end_time', 0)
        
        logger.info(
            f"[OutlineLLM] 处理第 {segment_idx + 1}/{len(segments)} 段 "
            f"({segment_start_time:.1f}s - {segment_end_time:.1f}s, {len(segment_text)} 字符)"
        )
        
        if progress_callback:
            progress = 25 + int((segment_idx + 1) / len(segments) * 65)  # 25% - 90%
            await progress_callback(
                progress, 
                f"正在处理第 {segment_idx + 1}/{len(segments)} 段..."
            )
        
        # 限制单段文本长度
        max_segment_length = 6000
        if len(segment_text) > max_segment_length:
            logger.warning(f"[OutlineLLM] 段文本过长，截取前 {max_segment_length} 字符")
            segment_text = segment_text[:max_segment_length]
        
        # 计算片段时长（分钟）
        segment_duration_minutes = (segment_end_time - segment_start_time) / 60
        
        # 根据片段时长确定关键点数量
        if segment_duration_minutes <= 3:
            key_points_per_chapter = "1-2个"
        elif segment_duration_minutes <= 10:
            key_points_per_chapter = "2-3个"
        else:
            key_points_per_chapter = "3-4个"
        
        prompt = f"""请分析以下视频字幕片段，提取该片段的章节/主题大纲。

这是视频的第 {segment_idx + 1} 段（共 {len(segments)} 段），时间范围：{segment_start_time:.1f}秒 - {segment_end_time:.1f}秒（约 {segment_duration_minutes:.1f} 分钟）。

**关键要求：**
1. 识别该片段的主要主题和章节（2-5 个章节，根据片段长度调整）
2. **标题要求**：章节标题必须基于字幕内容生成，不能使用"开始"、"中间章节"、"最后章节"等通用名称。标题应该概括该章节的核心主题，10字以内，简洁明了
3. **描述要求**：章节简要描述必须基于字幕内容，准确概括该章节的主要内容，不能随意编造
4. **关键点要求**：关键知识点/内容点必须基于字幕内容，每个章节 {key_points_per_chapter} 关键点，每个10-20字，不能随意编造

**每个章节格式：**
- title: 章节标题（基于字幕内容，10字以内，不能使用通用名称）
- start_time: 开始时间（秒，必须在该片段的时间范围内：{segment_start_time:.1f}-{segment_end_time:.1f}秒，从字幕中准确匹配）
- description: 章节简要描述（20-50字，基于字幕内容）
- key_points: 关键知识点/内容点列表（{key_points_per_chapter} 要点，每个10-20字，基于字幕内容）

**输出要求：**
- **必须返回严格的 JSON 数组格式**，格式如下：
```json
[
    {{
        "title": "章节标题",
        "start_time": {segment_start_time:.0f},
        "description": "章节描述",
        "key_points": ["关键点1", "关键点2"]
    }}
]
```
- **不要包含 Markdown 代码块标记（不要使用 ```json 或 ```）**
- **不要使用中文字段名（如"开始时间"），必须使用英文字段名（"start_time"）**
- start_time 必须是数字类型，不是字符串
- start_time 必须准确，不能超出片段时间范围（{segment_start_time:.1f}-{segment_end_time:.1f}秒）
- 标题、描述和关键点都必须基于字幕内容，不能随意编造

字幕片段内容：
{segment_text}

请返回 JSON 数组格式的大纲列表，**不要包含任何 Markdown 标记**："""
        
        segment_outline = await call_llm_for_outline(prompt, segment)
        
        # 验证时间范围
        for item in segment_outline:
            start_time = item.get('start_time', 0)
            if start_time < segment_start_time or start_time > segment_end_time:
                # 时间超出范围，调整到片段开始时间
                logger.warning(
                    f"[OutlineLLM] 章节时间 {start_time:.1f}s 超出片段范围 "
                    f"({segment_start_time:.1f}s - {segment_end_time:.1f}s)，调整为片段开始时间"
                )
                item['start_time'] = segment_start_time
        
        all_outlines.extend(segment_outline)
        
        # 段之间稍作延迟，避免 GPU 负载过高
        if segment_idx < len(segments) - 1:
            await asyncio.sleep(1.0)
    
    logger.info(f"[OutlineLLM] 分段处理完成，共生成 {len(all_outlines)} 个章节")
    
    return all_outlines


async def _call_cloud_llm_for_outline(
    prompt: str,
    subtitles: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """调用云端 LLM 提取大纲"""
    try:
        # 云端模型配置
        api_key = settings.LLM_API_KEY
        base_url = settings.LLM_BASE_URL.rstrip("/")
        model = settings.LLM_MODEL
        timeout = 60.0  # 云端模型超时时间
        
        messages = [
            {
                "role": "system", 
                "content": "你是一个专业的视频内容分析助手，擅长从字幕中提取视频章节大纲。\n\n**重要：你必须只返回纯 JSON 数组格式，不要包含任何 Markdown 代码块标记（不要使用 ```json 或 ```）。\n\nJSON 格式示例：\n[\n  {\n    \"title\": \"章节标题\",\n    \"start_time\": 0,\n    \"description\": \"章节描述\",\n    \"key_points\": [\"关键点1\", \"关键点2\"]\n  }\n]\n\n注意：\n- 必须使用英文字段名（title, start_time, description, key_points）\n- start_time 必须是数字，不是字符串\n- 不要使用中文字段名（如\"开始时间\"）\n- 不要包含 Markdown 标记"
            },
            {"role": "user", "content": prompt}
        ]
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 3000,
        }
        
        logger.info(f"[OutlineLLM] 正在调用云端模型: {model} (超时: {timeout}s)")
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            
            if response.status_code != 200:
                logger.error(f"云端模型调用失败: {response.status_code} - {response.text}")
                return []
            
            response_data = response.json()
            response_text = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if not response_text:
                logger.warning("云端模型返回空响应")
                return []
            
            logger.info(f"[OutlineLLM] 云端模型调用成功，响应长度: {len(response_text)} 字符")
            
            # 解析响应
            outline = parse_llm_response(response_text)
            
            return outline
            
    except httpx.TimeoutException:
        logger.error(f"云端模型调用超时 ({timeout}s)")
        return []
    except Exception as e:
        logger.error(f"云端 LLM 提取大纲失败: {e}", exc_info=True)
        return []


async def call_llm_for_outline(
    prompt: str,
    subtitles: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """调用 LLM 提取大纲（通用方法）"""
    # 如果使用云端模型，调用云端API
    if settings.USE_CLOUD_LLM:
        return await _call_cloud_llm_for_outline(prompt, subtitles)
    
    try:
        # 使用信号量控制并发，避免 GPU 负载波动（仅在本地模型模式下）
        async with _llm_semaphore:
            # 请求冷却：避免频繁调用 GPU，减少电流滋滋声（仅在本地模型模式下）
            global _last_request_time
            if _last_request_time is not None:
                time_since_last = asyncio.get_event_loop().time() - _last_request_time
                if time_since_last < _request_cooldown:
                    wait_time = _request_cooldown - time_since_last
                    logger.info(f"[OutlineLLM] 请求冷却中，等待 {wait_time:.2f} 秒...")
                    await asyncio.sleep(wait_time)
            
            _last_request_time = asyncio.get_event_loop().time()
            
            # 调用本地模型服务（Ollama API）
            base_url = settings.LOCAL_LLM_BASE_URL.rstrip("/")
            model = settings.LOCAL_LLM_MODEL
            # 增加超时时间，长视频需要更长时间
            timeout = max(settings.LOCAL_LLM_TIMEOUT, 120.0)  # 至少120秒
            
            messages = [
                {
                    "role": "system", 
                    "content": "你是一个专业的视频内容分析助手，擅长从字幕中提取视频章节大纲。\n\n**重要：你必须只返回纯 JSON 数组格式，不要包含任何 Markdown 代码块标记（不要使用 ```json 或 ```）。\n\nJSON 格式示例：\n[\n  {\n    \"title\": \"章节标题\",\n    \"start_time\": 0,\n    \"description\": \"章节描述\",\n    \"key_points\": [\"关键点1\", \"关键点2\"]\n  }\n]\n\n注意：\n- 必须使用英文字段名（title, start_time, description, key_points）\n- start_time 必须是数字，不是字符串\n- 不要使用中文字段名（如\"开始时间\"）\n- 不要包含 Markdown 标记"
                },
                {"role": "user", "content": prompt}
            ]
            
            logger.info(f"[OutlineLLM] 正在调用本地模型: {model} (超时: {timeout}s)")
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": 0.3,
                        "max_tokens": 3000,  # 增加输出长度限制
                        "stream": False
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"本地模型调用失败: {response.status_code} - {response.text}")
                    return []
                
                response_data = response.json()
                response_text = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                if not response_text:
                    logger.warning("本地模型返回空响应")
                    return []
                
                logger.info(f"[OutlineLLM] 本地模型调用成功，响应长度: {len(response_text)} 字符")
                
                # 解析响应
                outline = parse_llm_response(response_text)
                
                return outline
            
    except httpx.TimeoutException:
        logger.error(f"本地模型调用超时 ({timeout}s)")
        return []
    except Exception as e:
        logger.error(f"LLM 提取大纲失败: {e}", exc_info=True)
        return []

