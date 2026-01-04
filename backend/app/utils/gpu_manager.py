"""
GPU 管理工具模块
用于解决 LLM 推理时的电感啸叫问题

核心功能：
1. 系统级：频率锁定（Clock Locking）- 消除电压跳变
2. 硬件级：功耗压制（Power Limiting）- 削平瞬时电流峰值
3. 代码级：生命周期管理（Lifecycle Management）- 仅在 AI 服务运行时生效

工作原理：
- 启动时：开启持久化模式、锁定核心频率、设置功耗上限
- 运行中：GPU 维持在设定区间，避免剧烈电压跳变
- 关闭时：自动复位 GPU 设置，恢复默认状态
"""

import subprocess
import logging
import shutil
from typing import Optional, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class GPUManager:
    """GPU 管理类，负责在 AI 推理服务生命周期内管理 GPU 频率和功耗"""
    
    def __init__(
        self,
        enabled: bool = True,
        gpu_id: int = 0,
        locked_clock: int = 1500,
        power_limit_ratio: float = 0.75
    ):
        """
        初始化 GPU 管理器
        
        Args:
            enabled: 是否启用 GPU 管理（默认启用）
            gpu_id: GPU 设备 ID（默认 0）
            locked_clock: 锁定的核心频率（MHz），默认 1500MHz
            power_limit_ratio: 功耗限制比例（0-1），默认 0.75（75%）
        """
        self.enabled = enabled
        self.gpu_id = gpu_id
        self.locked_clock = locked_clock
        self.power_limit_ratio = power_limit_ratio
        
        # 存储原始状态，用于恢复
        self._original_power_limit: Optional[int] = None
        self._original_clock_state: Optional[str] = None
        self._is_configured = False
        
        # 检查 nvidia-smi 是否可用
        self._nvidia_smi_available = self._check_nvidia_smi()
        
        if not self._nvidia_smi_available:
            logger.warning("nvidia-smi 不可用，GPU 管理功能将被禁用")
            self.enabled = False
    
    def _check_nvidia_smi(self) -> bool:
        """检查 nvidia-smi 命令是否可用"""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def _run_nvidia_smi(self, command: str, timeout: int = 10) -> Tuple[bool, str]:
        """
        执行 nvidia-smi 命令
        
        Args:
            command: nvidia-smi 命令参数（不包含 nvidia-smi 本身）
            timeout: 超时时间（秒）
            
        Returns:
            (成功标志, 输出信息)
        """
        if not self._nvidia_smi_available:
            return False, "nvidia-smi 不可用"
        
        try:
            full_command = ["nvidia-smi", "-i", str(self.gpu_id)] + command.split()
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                
                # 检测权限错误
                error_lower = error_msg.lower()
                if "permission" in error_lower or "access denied" in error_lower or "拒绝访问" in error_msg:
                    return False, f"权限不足: {error_msg}。提示：nvidia-smi 可能需要管理员权限。在 Windows 上，请以管理员身份运行服务，或使用任务计划程序配置。"
                elif "not found" in error_lower or "找不到" in error_msg:
                    return False, f"命令未找到: {error_msg}"
                else:
                    return False, f"命令执行失败: {error_msg}"
                
        except subprocess.TimeoutExpired:
            return False, "命令执行超时"
        except FileNotFoundError:
            return False, "nvidia-smi 命令未找到，请确保已安装 NVIDIA 驱动"
        except Exception as e:
            return False, f"执行异常: {str(e)}"
    
    def _get_power_limit(self) -> Optional[int]:
        """获取当前 GPU 的默认功耗上限（W）"""
        # 使用 nvidia-smi 查询功耗上限（跨平台兼容）
        success, output = self._run_nvidia_smi(
            "--query-gpu=power.max_limit --format=csv,noheader,nounits"
        )
        
        if success and output:
            try:
                # 输出可能是 "250.00" 这样的格式
                power_value = float(output.strip())
                return int(power_value)
            except (ValueError, AttributeError):
                pass
        
        # 如果无法获取，返回 None（将使用默认值）
        logger.warning("无法获取 GPU 默认功耗上限，将跳过功耗限制设置")
        return None
    
    def configure_for_ai_inference(self) -> bool:
        """
        配置 GPU 用于 AI 推理（启动时调用）
        
        执行步骤：
        1. 开启持久化模式（Persistence Mode）
        2. 锁定核心频率（Locked Clocks）
        3. 设置功耗上限（Power Limit）
        
        Returns:
            是否配置成功
        """
        if not self.enabled:
            logger.info("GPU 管理已禁用，跳过配置")
            return True
        
        if self._is_configured:
            logger.warning("GPU 已配置，跳过重复配置")
            return True
        
        logger.info(f"开始配置 GPU {self.gpu_id} 用于 AI 推理（静音模式）...")
        
        # 步骤 1: 开启持久化模式
        logger.info("步骤 1/3: 开启持久化模式...")
        success, msg = self._run_nvidia_smi("-pm 1")
        if not success:
            # 权限错误时提供更详细的提示
            if "权限不足" in msg or "permission" in msg.lower():
                logger.error(f"开启持久化模式失败: {msg}")
                logger.warning(
                    "GPU 管理需要管理员权限。解决方案：\n"
                    "1. 以管理员身份运行 FastAPI 服务\n"
                    "2. 或在 Windows 任务计划程序中配置服务以管理员权限运行\n"
                    "3. 或禁用 GPU 管理功能（设置 GPU_MANAGEMENT_ENABLED=false）"
                )
            else:
                logger.error(f"开启持久化模式失败: {msg}")
            return False
        logger.info("持久化模式已开启")
        
        # 步骤 2: 锁定核心频率
        logger.info(f"步骤 2/3: 锁定核心频率至 {self.locked_clock}MHz...")
        success, msg = self._run_nvidia_smi(f"-lgc {self.locked_clock}")
        if not success:
            logger.error(f"锁定核心频率失败: {msg}")
            # 尝试恢复持久化模式
            self._run_nvidia_smi("-pm 0")
            return False
        logger.info(f"核心频率已锁定至 {self.locked_clock}MHz")
        
        # 步骤 3: 设置功耗上限
        logger.info("步骤 3/3: 设置功耗上限...")
        
        # 获取默认功耗上限
        default_power = self._get_power_limit()
        if default_power is None:
            logger.warning("无法获取默认功耗上限，跳过功耗限制设置")
        else:
            # 保存原始功耗上限
            self._original_power_limit = default_power
            
            # 计算目标功耗（按比例限制）
            target_power = int(default_power * self.power_limit_ratio)
            
            success, msg = self._run_nvidia_smi(f"-pl {target_power}")
            if not success:
                logger.error(f"设置功耗上限失败: {msg}")
                # 尝试恢复频率和持久化模式
                self._run_nvidia_smi("-rgc")
                self._run_nvidia_smi("-pm 0")
                return False
            
            logger.info(
                f"功耗上限已设置: {self._original_power_limit}W -> {target_power}W "
                f"({self.power_limit_ratio * 100:.0f}%)"
            )
        
        self._is_configured = True
        logger.info(f"GPU {self.gpu_id} 配置完成，已优化用于 AI 推理（静音模式）")
        return True
    
    def reset_to_default(self) -> bool:
        """
        重置 GPU 到默认状态（关闭时调用）
        
        执行步骤：
        1. 复位图形时钟（Reset Graphics Clocks）
        2. 恢复功耗上限（如果之前修改过）
        3. 关闭持久化模式（可选，通常保持开启）
        
        Returns:
            是否重置成功
        """
        if not self.enabled:
            logger.info("GPU 管理已禁用，跳过重置")
            return True
        
        if not self._is_configured:
            logger.info("GPU 未配置，无需重置")
            return True
        
        logger.info(f"开始重置 GPU {self.gpu_id} 到默认状态...")
        
        # 步骤 1: 复位图形时钟
        logger.info("步骤 1/3: 复位图形时钟...")
        success, msg = self._run_nvidia_smi("-rgc")
        if not success:
            logger.error(f"复位图形时钟失败: {msg}")
        else:
            logger.info("图形时钟已复位")
        
        # 步骤 2: 恢复功耗上限（如果之前修改过）
        if self._original_power_limit is not None:
            logger.info(f"步骤 2/3: 恢复功耗上限至 {self._original_power_limit}W...")
            success, msg = self._run_nvidia_smi(f"-pl {self._original_power_limit}")
            if not success:
                logger.error(f"恢复功耗上限失败: {msg}")
            else:
                logger.info(f"功耗上限已恢复至 {self._original_power_limit}W")
        else:
            logger.info("步骤 2/3: 跳过功耗上限恢复（未修改过）")
        
        # 步骤 3: 关闭持久化模式（可选）
        # 注意：持久化模式通常可以保持开启，不影响其他应用
        # 如果需要关闭，可以取消下面的注释
        # logger.info("步骤 3/3: 关闭持久化模式...")
        # success, msg = self._run_nvidia_smi("-pm 0")
        # if not success:
        #     logger.warning(f"关闭持久化模式失败: {msg}")
        # else:
        #     logger.info("持久化模式已关闭")
        
        logger.info("步骤 3/3: 保持持久化模式开启（不影响其他应用）")
        
        self._is_configured = False
        self._original_power_limit = None
        logger.info(f"GPU {self.gpu_id} 已重置到默认状态")
        return True
    
    def get_status(self) -> dict:
        """
        获取当前 GPU 状态
        
        Returns:
            GPU 状态字典
        """
        status = {
            "enabled": self.enabled,
            "gpu_id": self.gpu_id,
            "nvidia_smi_available": self._nvidia_smi_available,
            "is_configured": self._is_configured,
            "locked_clock": self.locked_clock if self._is_configured else None,
            "power_limit_ratio": self.power_limit_ratio if self._is_configured else None,
        }
        
        if self._nvidia_smi_available:
            # 获取当前频率
            success, output = self._run_nvidia_smi(
                "--query-gpu=clocks.current.graphics --format=csv,noheader,nounits"
            )
            if success and output:
                try:
                    status["current_clock"] = int(output.strip())
                except ValueError:
                    pass
            
            # 获取当前功耗
            success, output = self._run_nvidia_smi(
                "--query-gpu=power.draw --format=csv,noheader,nounits"
            )
            if success and output:
                try:
                    status["current_power"] = float(output.strip())
                except ValueError:
                    pass
        
        return status


# 全局 GPU 管理器实例（延迟初始化）
_gpu_manager: Optional[GPUManager] = None


def get_gpu_manager() -> Optional[GPUManager]:
    """获取全局 GPU 管理器实例"""
    return _gpu_manager


def initialize_gpu_manager(
    enabled: bool = True,
    gpu_id: int = 0,
    locked_clock: int = 1500,
    power_limit_ratio: float = 0.75
) -> GPUManager:
    """
    初始化全局 GPU 管理器
    
    Args:
        enabled: 是否启用 GPU 管理
        gpu_id: GPU 设备 ID
        locked_clock: 锁定的核心频率（MHz）
        power_limit_ratio: 功耗限制比例（0-1）
        
    Returns:
        GPU 管理器实例
    """
    global _gpu_manager
    _gpu_manager = GPUManager(
        enabled=enabled,
        gpu_id=gpu_id,
        locked_clock=locked_clock,
        power_limit_ratio=power_limit_ratio
    )
    return _gpu_manager


@contextmanager
def gpu_inference_context():
    """
    GPU 推理上下文管理器
    
    用法：
        with gpu_inference_context():
            # 执行本地模型推理
            result = await local_model_service.predict(...)
    
    功能：
        - 进入时：自动配置 GPU（锁频 + 功耗限制）
        - 退出时：自动恢复 GPU 到默认状态
        - 异常安全：即使发生异常也会恢复 GPU 设置
    """
    gpu_manager = get_gpu_manager()
    
    if not gpu_manager or not gpu_manager.enabled:
        # GPU 管理未启用，直接执行，不进行任何配置
        yield
        return
    
    # 检查是否已经配置（避免重复配置）
    was_configured = gpu_manager._is_configured
    
    try:
        # 进入时：配置 GPU（如果尚未配置）
        if not was_configured:
            success = gpu_manager.configure_for_ai_inference()
            if not success:
                logger.warning(
                    "GPU 配置失败（可能是权限不足），但将继续执行推理。"
                    "提示：nvidia-smi 可能需要管理员权限，或检查 GPU 是否可用。"
                )
        
        # 执行推理代码
        yield
        
    finally:
        # 退出时：恢复 GPU（仅在本次配置的情况下恢复）
        if not was_configured and gpu_manager._is_configured:
            try:
                gpu_manager.reset_to_default()
            except Exception as e:
                logger.error(f"GPU 恢复失败: {e}", exc_info=True)
                # 即使恢复失败也不抛出异常，避免影响业务逻辑

