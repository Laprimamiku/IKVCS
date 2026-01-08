"""
Prompt 压缩工具

功能：
1. 压缩冗长的Prompt，减少Token消耗
2. 保留关键信息，确保功能不受影响
3. 支持多种压缩策略
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PromptCompressor:
    """Prompt压缩器"""
    
    @staticmethod
    def compress_prompt(prompt: str, strategy: str = "aggressive") -> str:
        """
        压缩Prompt
        
        Args:
            prompt: 原始Prompt
            strategy: 压缩策略 (conservative/moderate/aggressive)
        
        Returns:
            str: 压缩后的Prompt
        """
        if not prompt:
            return prompt
        
        compressed = prompt
        
        # 1. 移除多余空白
        compressed = re.sub(r'\n{3,}', '\n\n', compressed)  # 多个换行合并为两个
        compressed = re.sub(r'[ \t]+', ' ', compressed)  # 多个空格合并为一个
        compressed = compressed.strip()
        
        # 2. 压缩JSON格式说明
        compressed = PromptCompressor._compress_json_format(compressed)
        
        # 3. 压缩示例（Few-Shot）
        if strategy in ("moderate", "aggressive"):
            compressed = PromptCompressor._compress_examples(compressed, strategy)
        
        # 4. 压缩评分标准说明
        if strategy == "aggressive":
            compressed = PromptCompressor._compress_scoring_criteria(compressed)
        
        # 5. 移除冗余说明
        compressed = PromptCompressor._remove_redundant_text(compressed)
        
        return compressed
    
    @staticmethod
    def _compress_json_format(prompt: str) -> str:
        """压缩JSON格式说明"""
        # 查找并替换冗长的JSON格式说明
        json_format_pattern = r'\{[^}]*"score"[^}]*"is_inappropriate"[^}]*\}'
        
        # 简化的JSON格式说明
        simplified_format = '{"score":0-100,"category":"类别","reason":"理由","is_highlight":bool,"is_inappropriate":bool}'
        
        # 替换冗长的格式说明
        prompt = re.sub(
            r'输出格式要求.*?\{[^}]*"score"[^}]*\}',
            f'输出JSON: {simplified_format}',
            prompt,
            flags=re.DOTALL
        )
        
        # 移除Markdown代码块标记说明
        prompt = re.sub(
            r'（不要包含.*?```.*?）',
            '',
            prompt
        )
        
        return prompt
    
    @staticmethod
    def _compress_examples(prompt: str, strategy: str) -> str:
        """压缩示例（Few-Shot）"""
        if strategy == "moderate":
            # 保留所有示例，但压缩格式
            # 将多行示例压缩为单行
            prompt = re.sub(
                r'输入: "([^"]+)"\s*输出: (\{[^}]+\})',
                r'输入:"\1" 输出:\2',
                prompt
            )
        elif strategy == "aggressive":
            # 只保留关键示例（高分、低分、违规）
            # 移除中等分数的示例
            lines = prompt.split('\n')
            filtered_lines = []
            skip_next = False
            for i, line in enumerate(lines):
                if skip_next:
                    skip_next = False
                    continue
                
                # 保留高分（90+）和低分（<60）的示例
                if '输入:' in line and i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if '"score": 9' in next_line or '"score": 8' in next_line or '"score": [0-5]' in next_line:
                        filtered_lines.append(line)
                        filtered_lines.append(next_line)
                        skip_next = True
                    elif '"score": 7' in next_line:
                        # 跳过中等分数示例
                        skip_next = True
                        continue
                    else:
                        filtered_lines.append(line)
                else:
                    filtered_lines.append(line)
            
            prompt = '\n'.join(filtered_lines)
        
        return prompt
    
    @staticmethod
    def _compress_scoring_criteria(prompt: str) -> str:
        """压缩评分标准说明"""
        # 将详细的评分标准压缩为简洁版本
        prompt = re.sub(
            r'- \*\*90-100分.*?\*\*:\s*\n\s*- ([^\n]+)',
            r'- 90-100: \1',
            prompt
        )
        prompt = re.sub(
            r'- \*\*70-89分.*?\*\*:\s*\n\s*- ([^\n]+)',
            r'- 70-89: \1',
            prompt
        )
        prompt = re.sub(
            r'- \*\*60-69分.*?\*\*:\s*\n\s*- ([^\n]+)',
            r'- 60-69: \1',
            prompt
        )
        prompt = re.sub(
            r'- \*\*0-59分.*?\*\*:\s*\n\s*- ([^\n]+)',
            r'- 0-59: \1',
            prompt
        )
        
        # 移除多余的列表项换行
        prompt = re.sub(r'-\s+([^\n]+)\n\s+-', r'- \1\n-', prompt)
        
        return prompt
    
    @staticmethod
    def _remove_redundant_text(prompt: str) -> str:
        """移除冗余文本"""
        # 移除重复的说明
        prompt = re.sub(r'核心原则.*?客观公正', '核心原则：评分一致性、客观公正', prompt, flags=re.DOTALL)
        
        # 移除多余的"请"、"务必"等强调词
        prompt = re.sub(r'请务必|请一定|务必', '请', prompt)
        
        # 压缩"必须"、"应该"等重复强调
        prompt = re.sub(r'必须.*?必须', '必须', prompt)
        
        return prompt
    
    @staticmethod
    def estimate_token_savings(original: str, compressed: str) -> float:
        """
        估算Token节省比例
        
        注意：这是粗略估算，实际Token数取决于使用的分词器
        """
        if not original:
            return 0.0
        
        # 简单的字符数比例估算（中文1字符≈1token，英文1词≈1token）
        original_len = len(original)
        compressed_len = len(compressed)
        
        if original_len == 0:
            return 0.0
        
        savings_ratio = (original_len - compressed_len) / original_len
        return max(0.0, min(1.0, savings_ratio))


# 全局实例
prompt_compressor = PromptCompressor()

