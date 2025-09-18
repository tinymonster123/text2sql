from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseLLMProvider(ABC):
    """LLM提供商抽象基类"""

    def __init__(self, name: str):
        self.name = name
        self.is_initialized = False

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化LLM提供商"""
        pass

    @abstractmethod
    def generate_sql(self, input_data: Dict[str, Any]) -> str:
        """生成SQL查询

        Args:
            input_data: 包含query、schema、examples等信息的字典

        Returns:
            生成的SQL字符串
        """
        pass

    @abstractmethod
    def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """生成通用响应"""
        pass

    def get_info(self) -> Dict[str, Any]:
        """获取提供商信息"""
        return {
            "name": self.name,
            "type": "llm",
            "initialized": self.is_initialized
        }