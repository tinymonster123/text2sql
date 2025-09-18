from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple


class BaseVectorDBProvider(ABC):
    """向量数据库提供商抽象基类"""

    def __init__(self, name: str):
        self.name = name
        self.is_initialized = False

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化向量数据库提供商"""
        pass

    @abstractmethod
    def add_vector(self, vector: List[float], metadata: Dict[str, Any], doc_id: str = None) -> bool:
        """添加向量到数据库"""
        pass

    @abstractmethod
    def search(self, query_vector: List[float], k: int = 5, threshold: float = 0.0) -> List[Tuple[float, Dict[str, Any]]]:
        """搜索相似向量

        Returns:
            List of (similarity_score, metadata) tuples
        """
        pass

    @abstractmethod
    def delete_vector(self, doc_id: str) -> bool:
        """删除指定向量"""
        pass

    @abstractmethod
    def save(self) -> bool:
        """保存向量数据库"""
        pass

    def get_info(self) -> Dict[str, Any]:
        """获取提供商信息"""
        return {
            "name": self.name,
            "type": "vectordb",
            "initialized": self.is_initialized
        }