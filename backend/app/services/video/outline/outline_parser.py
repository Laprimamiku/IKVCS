"""
大纲解析工具模块

职责：解析 LLM 响应，提取大纲数据
"""
import json
import logging
import re
from typing import List, Dict, Any

from app.core.types import OutlineEntry

logger = logging.getLogger(__name__)


def parse_llm_response(response_text: str) -> List[OutlineEntry]:
    """解析 LLM 响应（鲁棒解析，处理格式不完整的 JSON）"""
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
            return extract_outline_list(data)
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
            
            # 2. 修复未闭合的字符串
            if json_text and json_text[-1] != ']':
                last_brace = json_text.rfind('}')
                if last_brace > 0:
                    json_text = json_text[:last_brace + 1] + ']'
            
            try:
                data = json.loads(json_text)
                return extract_outline_list(data)
            except json.JSONDecodeError as e:
                logger.warning(f"方法2解析失败: {e}")
        
        # 方法3：使用正则表达式提取 JSON 数组（更宽松，支持多行）
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
                return extract_outline_list(data)
            except json.JSONDecodeError:
                pass
        
        # 方法4：尝试提取所有 JSON 对象，然后组合成数组
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
        objects = []
        
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


def extract_outline_list(data: Any) -> List[Dict[str, Any]]:
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

