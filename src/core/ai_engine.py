from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class EngineCapability:
    """引擎能力描述"""
    name: str
    description: str
    input_types: List[str]
    output_types: List[str]
    parameters: Dict[str, Any] = field(default_factory=dict)


class AIEngine(ABC):
    """AI引擎抽象基类

    定义了所有AI引擎的通用接口，支持不同类型的AI功能扩展
    符合可扩展AI中间件架构标准
    """

    def __init__(self, name: str, version: str = "1.0.0", description: str = ""):
        self.name = name
        self.version = version
        self.description = description
        self.is_initialized = False
        self._capabilities: List[EngineCapability] = []

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化引擎

        Args:
            config: 引擎配置参数

        Returns:
            bool: 是否初始化成功
        """
        pass

    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理输入数据

        Args:
            input_data: 输入数据

        Returns:
            Dict[str, Any]: 处理结果
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> List[EngineCapability]:
        """获取引擎能力描述

        Returns:
            List[EngineCapability]: 能力描述列表
        """
        pass

    def add_capability(self, capability: EngineCapability):
        """添加引擎能力"""
        self._capabilities.append(capability)

    def get_info(self) -> Dict[str, Any]:
        """获取引擎基本信息"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "status": "initialized" if self.is_initialized else "not_initialized",
            "capabilities_count": len(self._capabilities)
        }

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "healthy": self.is_initialized,
            "engine": self.name,
            "version": self.version,
            "timestamp": None  # 实现时添加时间戳
        }

    def shutdown(self) -> bool:
        """关闭引擎，释放资源"""
        try:
            self.is_initialized = False
            logger.info(f"引擎 {self.name} 已关闭")
            return True
        except Exception as e:
            logger.error(f"关闭引擎 {self.name} 失败: {e}")
            return False