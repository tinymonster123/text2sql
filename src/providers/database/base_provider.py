from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple, Optional


class BaseDatabaseProvider(ABC):
    """数据库提供商抽象基类"""

    def __init__(self, name: str):
        self.name = name
        self.is_initialized = False

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化数据库提供商"""
        pass

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """获取数据库结构信息"""
        pass

    @abstractmethod
    def format_schema(self, schema_info: Dict[str, Any]) -> str:
        """格式化数据库结构为LLM可理解的文本"""
        pass

    @abstractmethod
    def execute_sql(self, sql: str) -> Tuple[bool, Optional[str], Optional[List[str]]]:
        """执行SQL语句

        Returns:
            (is_success, error_message, column_names)
        """
        pass

    @abstractmethod
    def validate_sql(self, sql: str) -> Tuple[bool, Optional[str]]:
        """验证SQL语法

        Returns:
            (is_valid, error_message)
        """
        pass

    def get_info(self) -> Dict[str, Any]:
        """获取提供商信息"""
        return {
            "name": self.name,
            "type": "database",
            "initialized": self.is_initialized,
        }
