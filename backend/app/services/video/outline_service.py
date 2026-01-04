"""
视频内容大纲提取服务
基于字幕内容，使用 LLM 提取视频章节/主题
"""
import json
import logging
import asyncio
from typing import List, Optional, Dict, Any, Callable
from pathlib import Path

from app.core.config import settings
from app.core.types import SubtitleEntry, OutlineEntry
from app.services.video.subtitle_parser import SubtitleParser
import httpx

logger = logging.getLogger(__name__)

# 并发控制：限制同时进行的 LLM 请求数量，避免 GPU 负载波动
# 对于 RTX 3050 4GB，建议设置为 1，确保 GPU 负载稳定
_llm_semaphore = asyncio.Semaphore(1)  # 同时只允许 1 个 LLM 请求

# 请求冷却时间：避免频繁调用 GPU，减少电流滋滋声
_last_request_time = None
_request_cooldown = 2.0  # 请求之间的最小间隔（秒），给 GPU 足够的冷却时间


class OutlineService:
    """视频大纲提取服务"""
    
    @staticmethod
    async def extract_outline(
        video_id: int, 
        subtitle_url: str,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> List[OutlineEntry]:
        """
        提取视频内容大纲
        
        Args:
            video_id: 视频ID
            subtitle_url: 字幕文件URL
            
        Returns:
            List[Dict]: 大纲列表，每个条目包含 {title, start_time, description}
        """
        try:
            # 1. 解析字幕文件
            subtitle_path = Path(settings.STORAGE_ROOT) / subtitle_url.lstrip('/')
            if not subtitle_path.exists():
                # 尝试从 uploads 目录查找
                subtitle_path = Path(settings.UPLOAD_SUBTITLE_DIR) / Path(subtitle_url).name
                if not subtitle_path.exists():
                    logger.warning(f"字幕文件不存在: {subtitle_url}")
                    return []
            
            subtitles = SubtitleParser.parse_subtitle_file(str(subtitle_path))
            if not subtitles:
                logger.warning(f"字幕文件为空: {subtitle_url}")
                return []
            
            # 2. 提取文本内容
            full_text = SubtitleParser.extract_text_only(subtitles)
            if len(full_text) < 50:  # 文本太短，无法提取大纲
                return []
            
            # 3. 使用 LLM 提取大纲
            if progress_callback:
                await progress_callback(10, "开始分析字幕内容...")
            
            outline = await OutlineService._llm_extract_outline(
                full_text, 
                subtitles,
                progress_callback=progress_callback
            )
            
            if progress_callback:
                await progress_callback(100, f"大纲生成完成，共 {len(outline) if outline else 0} 个章节")
            
            return outline
            
        except Exception as e:
            logger.error(f"提取视频大纲失败 (video_id={video_id}): {e}")
            return []
    
    @staticmethod
    def _split_subtitles_by_time(
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
    
    @staticmethod
    async def _llm_extract_outline(
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
        
        logger.info(f"[OutlineService] 视频总时长: {video_duration:.1f}秒，字幕文本长度: {len(full_text)} 字符")
        
        # 如果视频较短（<15分钟）或文本较短（<8000字符），直接处理
        max_text_length = 8000  # 单次处理的最大文本长度
        max_duration = 900  # 15分钟
        
        if len(full_text) <= max_text_length and video_duration <= max_duration:
            # 短视频，直接处理
            logger.info("[OutlineService] 视频较短，使用单次处理模式")
            if progress_callback:
                await progress_callback(30, "正在调用 AI 模型生成大纲...")
            return await OutlineService._llm_extract_outline_single(full_text, subtitles, progress_callback)
        else:
            # 长视频，分段处理
            logger.info(f"[OutlineService] 视频较长，使用分段处理模式（每段约10分钟）")
            if progress_callback:
                await progress_callback(20, f"视频较长，将分为多个段落处理...")
            return await OutlineService._llm_extract_outline_segmented(full_text, subtitles, progress_callback)
    
    @staticmethod
    async def _llm_extract_outline_single(
        full_text: str,
        subtitles: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> List[Dict[str, Any]]:
        """单次处理模式（适用于短视频）"""
        # 限制输入文本长度，但尽量保留更多内容
        max_input_length = 8000
        if len(full_text) > max_input_length:
            logger.warning(f"[OutlineService] 文本过长 ({len(full_text)} 字符)，截取前 {max_input_length} 字符")
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
        
        result = await OutlineService._call_llm_for_outline(prompt, subtitles)
        
        if progress_callback:
            await progress_callback(90, "正在处理生成结果...")
        
        return result
    
    @staticmethod
    async def _llm_extract_outline_segmented(
        full_text: str,
        subtitles: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> List[Dict[str, Any]]:
        """分段处理模式（适用于长视频）"""
        # 将字幕按时间分段（每段约10分钟）
        segments = OutlineService._split_subtitles_by_time(subtitles, segment_duration=600)
        logger.info(f"[OutlineService] 视频分为 {len(segments)} 段进行处理")
        
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
                f"[OutlineService] 处理第 {segment_idx + 1}/{len(segments)} 段 "
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
                logger.warning(f"[OutlineService] 段文本过长，截取前 {max_segment_length} 字符")
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
            
            segment_outline = await OutlineService._call_llm_for_outline(prompt, segment)
            
            # 验证时间范围
            for item in segment_outline:
                start_time = item.get('start_time', 0)
                if start_time < segment_start_time or start_time > segment_end_time:
                    # 时间超出范围，调整到片段开始时间
                    logger.warning(
                        f"[OutlineService] 章节时间 {start_time:.1f}s 超出片段范围 "
                        f"({segment_start_time:.1f}s - {segment_end_time:.1f}s)，调整为片段开始时间"
                    )
                    item['start_time'] = segment_start_time
            
            all_outlines.extend(segment_outline)
            
            # 段之间稍作延迟，避免 GPU 负载过高
            if segment_idx < len(segments) - 1:
                await asyncio.sleep(1.0)
        
        logger.info(f"[OutlineService] 分段处理完成，共生成 {len(all_outlines)} 个章节")
        
        if progress_callback:
            await progress_callback(90, "正在合并和优化大纲...")
        
        # 合并和去重
        result = OutlineService._merge_outlines(all_outlines, subtitles)
        
        if progress_callback:
            await progress_callback(95, f"大纲生成完成，共 {len(result)} 个章节")
        
        return result
    
    @staticmethod
    async def _call_llm_for_outline(
        prompt: str,
        subtitles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """调用 LLM 提取大纲（通用方法）"""
        try:
            # 使用信号量控制并发，避免 GPU 负载波动
            async with _llm_semaphore:
                # 请求冷却：避免频繁调用 GPU，减少电流滋滋声
                global _last_request_time
                if _last_request_time is not None:
                    time_since_last = asyncio.get_event_loop().time() - _last_request_time
                    if time_since_last < _request_cooldown:
                        wait_time = _request_cooldown - time_since_last
                        logger.info(f"[OutlineService] 请求冷却中，等待 {wait_time:.2f} 秒...")
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
                
                logger.info(f"[OutlineService] 正在调用本地模型: {model} (超时: {timeout}s)")
                
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
                    
                    logger.info(f"[OutlineService] 本地模型调用成功，响应长度: {len(response_text)} 字符")
                    
                    # 解析响应
                    outline = OutlineService._parse_llm_response(response_text)
                    
                    return outline
                
        except httpx.TimeoutException:
            logger.error(f"本地模型调用超时 ({timeout}s)")
            return []
        except Exception as e:
            logger.error(f"LLM 提取大纲失败: {e}", exc_info=True)
            return []
    
    @staticmethod
    def _merge_outlines(
        outlines: List[Dict[str, Any]],
        subtitles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """合并和去重大纲"""
        if not outlines:
            return []
        
        # 按时间排序
        outlines.sort(key=lambda x: x.get('start_time', 0))
        
        # 去重：如果两个章节时间太接近（<30秒），合并为一个
        merged = []
        for outline in outlines:
            if not merged:
                merged.append(outline)
            else:
                last_outline = merged[-1]
                last_time = last_outline.get('start_time', 0)
                current_time = outline.get('start_time', 0)
                
                if current_time - last_time < 30:
                    # 时间太接近，合并描述和关键点
                    logger.debug(f"[OutlineService] 合并章节: {last_time:.1f}s 和 {current_time:.1f}s")
                    last_outline['description'] = f"{last_outline.get('description', '')} | {outline.get('description', '')}"
                    
                    # 确保 key_points 是数组格式
                    last_key_points = last_outline.get('key_points', [])
                    current_key_points = outline.get('key_points', [])
                    
                    # 如果 key_points 是字符串，转换为数组
                    if isinstance(last_key_points, str):
                        last_key_points = [p.strip() for p in last_key_points.split(',') if p.strip()]
                    if isinstance(current_key_points, str):
                        current_key_points = [p.strip() for p in current_key_points.split(',') if p.strip()]
                    
                    # 合并并去重
                    if not isinstance(last_key_points, list):
                        last_key_points = []
                    if not isinstance(current_key_points, list):
                        current_key_points = []
                    
                    last_outline['key_points'] = list(set(
                        last_key_points + current_key_points
                    ))
                else:
                    merged.append(outline)
        
        # 验证和补充时间信息
        merged = OutlineService._validate_and_fill_times(merged, subtitles)
        
        return merged
    
    @staticmethod
    def _parse_llm_response(response_text: str) -> List[OutlineEntry]:
        """解析 LLM 响应（鲁棒解析，处理格式不完整的 JSON）"""
        import re
        
        try:
            # 清理响应文本
            text = response_text.strip()
            
            # 移除代码块标记（处理 ```json ... ``` 格式）
            if text.startswith('```'):
                # 移除开头的 ```json 或 ```
                text = re.sub(r'^```(?:json)?\s*\n?', '', text, flags=re.IGNORECASE)
                # 移除结尾的 ```
                text = re.sub(r'\n?```\s*$', '', text)
                text = text.strip()
            
            # 方法1：尝试直接解析
            try:
                data = json.loads(text)
                return OutlineService._extract_outline_list(data)
            except json.JSONDecodeError:
                pass
            
            # 方法2：提取 JSON 数组部分（改进版）
            json_start = text.find('[')
            if json_start >= 0:
                # 从 [ 开始，尝试找到匹配的 ]
                bracket_count = 0
                in_string = False
                escape_next = False
                json_end = len(text)
                
                for i in range(json_start, len(text)):
                    char = text[i]
                    
                    if escape_next:
                        escape_next = False
                        continue
                    
                    if char == '\\':
                        escape_next = True
                        continue
                    
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        continue
                    
                    if not in_string:
                        if char == '[':
                            bracket_count += 1
                        elif char == ']':
                            bracket_count -= 1
                            if bracket_count == 0:
                                json_end = i + 1
                                break
                
                json_text = text[json_start:json_end]
                
                # 尝试修复常见的 JSON 问题
                # 1. 移除尾部的逗号
                json_text = re.sub(r',\s*\]', ']', json_text)
                json_text = re.sub(r',\s*\}', '}', json_text)
                
                # 2. 修复未转义的引号（更简单的方法：移除或替换问题字符）
                # 如果JSON解析失败，尝试移除可能导致问题的字符
                # 注意：这是一个保守的修复策略
                
                # 3. 修复未闭合的字符串
                if json_text and json_text[-1] != ']':
                    last_brace = json_text.rfind('}')
                    if last_brace > 0:
                        json_text = json_text[:last_brace + 1] + ']'
                
                try:
                    data = json.loads(json_text)
                    return OutlineService._extract_outline_list(data)
                except json.JSONDecodeError as e:
                    logger.warning(f"方法2解析失败: {e}")
            
            # 方法3：使用正则表达式提取 JSON 数组（更宽松，支持多行）
            # 匹配从 [ 开始到 ] 结束的内容，但需要处理嵌套
            json_match = re.search(r'\[\s*(\{.*?\})\s*\]', text, re.DOTALL)
            if not json_match:
                # 尝试匹配多个对象
                json_match = re.search(r'\[\s*(\{.*\})\s*\]', text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                # 尝试修复
                json_str = re.sub(r',\s*\]', ']', json_str)
                json_str = re.sub(r',\s*\}', '}', json_str)
                
                try:
                    data = json.loads(json_str)
                    return OutlineService._extract_outline_list(data)
                except json.JSONDecodeError:
                    pass
            
            # 方法4：尝试提取所有 JSON 对象，然后组合成数组
            # 使用正则表达式查找所有可能的 JSON 对象
            # 匹配 { "title": ... } 模式的对象
            object_pattern = r'\{[^{}]*"title"[^{}]*\}'
            matches = re.findall(object_pattern, text, re.DOTALL)
            
            objects = []
            for match in matches:
                try:
                    # 尝试修复常见的JSON问题
                    match_clean = re.sub(r',\s*\}', '}', match)
                    match_clean = re.sub(r',\s*$', '', match_clean)
                    # 移除控制字符
                    match_clean = ''.join(char for char in match_clean if ord(char) >= 32 or char in '\n\r\t')
                    
                    obj = json.loads(match_clean)
                    if isinstance(obj, dict) and 'title' in obj:
                        objects.append(obj)
                except:
                    # 如果解析失败，尝试更宽松的匹配
                    try:
                        # 尝试提取 title 和 start_time 字段
                        title_match = re.search(r'"title"\s*:\s*"([^"]*)"', match)
                        time_match = re.search(r'"start_time"\s*:\s*(\d+(?:\.\d+)?)', match)
                        if title_match and time_match:
                            obj = {
                                'title': title_match.group(1),
                                'start_time': float(time_match.group(1)),
                                'description': '',
                                'key_points': []
                            }
                            objects.append(obj)
                    except:
                        pass
            
            if objects:
                logger.info(f"使用方法4提取了 {len(objects)} 个对象")
                return objects
            
            # 方法5：使用正则表达式直接提取关键字段，手动构建对象
            # 这是一个最后的备用方案，处理格式错误的JSON
            objects = []
            
            # 尝试多种模式匹配
            # 模式1：标准的对象格式 { "title": "...", "start_time": ... }
            chapter_pattern1 = r'\{\s*"title"\s*:\s*"([^"]*)"[^}]*"start_time"\s*:\s*(\d+(?:\.\d+)?)'
            matches1 = re.finditer(chapter_pattern1, text, re.DOTALL)
            
            for match in matches1:
                try:
                    title = match.group(1)
                    start_time = float(match.group(2))
                    
                    # 尝试提取 description
                    desc_match = re.search(r'"description"\s*:\s*"([^"]*)"', match.group(0))
                    description = desc_match.group(1) if desc_match else ''
                    
                    # 尝试提取 key_points
                    key_points = []
                    key_points_match = re.search(r'"key_points"\s*:\s*\[(.*?)\]', match.group(0), re.DOTALL)
                    if key_points_match:
                        points_text = key_points_match.group(1)
                        point_matches = re.findall(r'"([^"]*)"', points_text)
                        key_points = point_matches
                    
                    obj = {
                        'title': title,
                        'start_time': start_time,
                        'description': description,
                        'key_points': key_points
                    }
                    objects.append(obj)
                except Exception as e:
                    logger.debug(f"方法5模式1提取对象失败: {e}")
                    continue
            
            # 模式2：处理格式错误的响应（如 "开始时间": "0" 而不是 "start_time": 0）
            # 查找所有可能的字段组合
            if not objects:
                # 尝试提取 title 字段（可能使用不同的字段名）
                title_patterns = [
                    r'"title"\s*:\s*"([^"]*)"',
                    r'"标题"\s*:\s*"([^"]*)"',
                    r'"章节"\s*:\s*"([^"]*)"'
                ]
                
                time_patterns = [
                    r'"start_time"\s*:\s*"?(\d+(?:\.\d+)?)"?',
                    r'"开始时间"\s*:\s*"?(\d+(?:\.\d+)?)"?',
                    r'"时间"\s*:\s*"?(\d+(?:\.\d+)?)"?'
                ]
                
                # 尝试找到所有可能的章节
                for title_pattern in title_patterns:
                    title_matches = list(re.finditer(title_pattern, text))
                    for title_match in title_matches:
                        title = title_match.group(1)
                        # 在标题附近查找时间
                        context_start = max(0, title_match.start() - 200)
                        context_end = min(len(text), title_match.end() + 200)
                        context = text[context_start:context_end]
                        
                        for time_pattern in time_patterns:
                            time_match = re.search(time_pattern, context)
                            if time_match:
                                try:
                                    start_time = float(time_match.group(1))
                                    obj = {
                                        'title': title,
                                        'start_time': start_time,
                                        'description': '',
                                        'key_points': []
                                    }
                                    objects.append(obj)
                                    break
                                except:
                                    pass
            
            if objects:
                logger.info(f"使用方法5提取了 {len(objects)} 个对象")
                return objects
            
            # 所有方法都失败
            logger.error(f"所有解析方法都失败")
            logger.debug(f"响应文本前1000字符: {response_text[:1000]}")
            logger.debug(f"响应文本后1000字符: {response_text[-1000:]}")
            return []
                
        except Exception as e:
            logger.error(f"解析 LLM 响应时发生异常: {e}", exc_info=True)
            return []
    
    @staticmethod
    def _extract_outline_list(data: Any) -> List[Dict[str, Any]]:
        """从解析的数据中提取大纲列表"""
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            if 'outline' in data:
                return data['outline']
            elif 'chapters' in data:
                return data['chapters']
            elif 'sections' in data:
                return data['sections']
            else:
                # 如果字典的键都是数字，可能是列表格式的字典
                if all(str(k).isdigit() for k in data.keys()):
                    return [data[k] for k in sorted(data.keys(), key=int)]
                return []
        else:
            return []
    
    @staticmethod
    def _validate_and_fill_times(
        outline: List[OutlineEntry],
        subtitles: List[SubtitleEntry]
    ) -> List[OutlineEntry]:
        """验证和补充时间信息，确保覆盖整个视频"""
        if not subtitles:
            return outline
        
        video_end_time = subtitles[-1].get('end_time', 0)
        result: List[OutlineEntry] = []
        
        # 如果大纲为空或最后一个章节的时间点太早，记录警告
        if outline:
            last_time = max(item.get('start_time', 0) for item in outline)
            if last_time < video_end_time * 0.7:  # 如果最后一个章节不到视频70%的位置
                logger.warning(
                    f"[OutlineService] 大纲可能未覆盖整个视频："
                    f"最后一个章节时间 {last_time:.1f}s，视频结束时间 {video_end_time:.1f}s"
                )
        
        for item in outline:
            start_time = item.get('start_time', 0)
            
            # 如果时间不在字幕范围内，尝试根据描述匹配
            if start_time == 0 or start_time > video_end_time:
                # 根据标题或描述在字幕中查找匹配的时间点
                title = item.get('title', '')
                description = item.get('description', '')
                for subtitle in subtitles:
                    subtitle_text = subtitle.get('text', '').lower()
                    if title.lower() in subtitle_text or (description and description.lower() in subtitle_text):
                        start_time = subtitle['start_time']
                        break
            
            # 确保时间在有效范围内
            if start_time < 0:
                start_time = 0
            if start_time > video_end_time:
                # 如果超过视频结束时间，调整到合理位置（倒数5-10%的时间段）
                start_time = max(video_end_time * 0.9, video_end_time - 60)  # 至少提前1分钟或10%
            
            # 检查是否是最后一个章节，如果是，确保不是最后一秒
            is_last_chapter = (item == outline[-1]) if outline else False
            if is_last_chapter:
                # 最后一个章节应该在倒数5-15%的时间段，不能是最后一秒
                min_last_time = video_end_time * 0.85
                max_last_time = video_end_time * 0.95
                if start_time >= video_end_time * 0.98:  # 如果太接近结束（98%以后）
                    # 调整到合理位置
                    start_time = max(min_last_time, video_end_time * 0.9)
                    logger.warning(
                        f"[OutlineService] 最后一个章节时间 {start_time:.1f}s 太接近结束，"
                        f"调整为 {start_time:.1f}s"
                    )
            
            # 计算结束时间（下一个章节的开始时间，或视频结束时间）
            end_time = None
            if result:
                # 如果已有结果，当前章节的结束时间是下一个章节的开始时间
                pass  # 会在后面处理
            else:
                # 第一个章节，查找下一个章节的开始时间
                next_item = None
                for next_outline in outline:
                    if next_outline.get('start_time', 0) > start_time:
                        next_item = next_outline
                        break
                if next_item:
                    end_time = next_item.get('start_time', 0)
                elif subtitles:
                    end_time = subtitles[-1].get('end_time', start_time + 60)
            
            # 确保 key_points 是数组格式
            key_points = item.get('key_points', [])
            if isinstance(key_points, str):
                # 如果是字符串，尝试解析为数组
                try:
                    import json
                    key_points = json.loads(key_points)
                except:
                    # 如果解析失败，按逗号分割
                    key_points = [p.strip() for p in key_points.split(',') if p.strip()]
            elif not isinstance(key_points, list):
                # 如果不是列表，转换为列表
                key_points = []
            
            result.append({
                'title': item.get('title', '未知章节'),
                'start_time': float(start_time),
                'description': item.get('description', ''),
                'key_points': key_points,  # 关键知识点/内容点（确保是数组）
                'end_time': float(end_time) if end_time else None
            })
        
        # 补充结束时间
        for i, item in enumerate(result):
            if not item.get('end_time'):
                if i < len(result) - 1:
                    item['end_time'] = result[i + 1]['start_time']
                elif subtitles:
                    item['end_time'] = subtitles[-1].get('end_time', item['start_time'] + 60)
                else:
                    item['end_time'] = item['start_time'] + 60
        
        # 验证关键点数量（后处理检查）
        total_key_points = sum(len(item.get('key_points', [])) for item in result)
        video_minutes = video_end_time / 60
        
        if video_minutes <= 15 and total_key_points < 5:
            logger.warning(
                f"[OutlineService] 关键点数量不足：视频 {video_minutes:.1f} 分钟，"
                f"应该有至少5个关键点，实际只有 {total_key_points} 个。"
                f"这可能是由于本地模型（0.5B）理解能力有限导致的。"
            )
        
        return result

