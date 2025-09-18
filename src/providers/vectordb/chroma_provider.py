from typing import Dict, Any, List, Tuple
import logging
from .base_provider import BaseVectorDBProvider

logger = logging.getLogger(__name__)


class ChromaProvider(BaseVectorDBProvider):
    """ChromaDB向量数据库提供商"""

    def __init__(self):
        super().__init__("chroma")
        self.client = None
        self.collection = None
        self.collection_name = "text2sql_collection"

    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化ChromaDB提供商"""
        try:
            import chromadb
            from chromadb.config import Settings

            host = config.get("host", "localhost")
            port = config.get("port", 8000)
            self.collection_name = config.get("collection_name", "text2sql_collection")

            # 连接到ChromaDB
            self.client = chromadb.HttpClient(
                host=host,
                port=port,
                settings=Settings(allow_reset=True)
            )

            # 获取或创建集合
            try:
                self.collection = self.client.get_collection(self.collection_name)
            except:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Text2SQL query embeddings"}
                )

            self.is_initialized = True
            logger.info(f"ChromaDB提供商初始化成功: {host}:{port}")
            return True

        except Exception as e:
            logger.error(f"ChromaDB提供商初始化失败: {e}")
            return False

    def add_vector(self, vector: List[float], metadata: Dict[str, Any], doc_id: str = None) -> bool:
        """添加向量到ChromaDB"""
        if not self.is_initialized:
            raise RuntimeError("Provider not initialized")

        try:
            import uuid
            if not doc_id:
                doc_id = str(uuid.uuid4())

            self.collection.add(
                embeddings=[vector],
                metadatas=[metadata],
                ids=[doc_id]
            )

            logger.debug(f"向量添加成功: {doc_id}")
            return True

        except Exception as e:
            logger.error(f"添加向量失败: {e}")
            return False

    def search(self, query_vector: List[float], k: int = 5, threshold: float = 0.0) -> List[Tuple[float, Dict[str, Any]]]:
        """搜索相似向量"""
        if not self.is_initialized:
            raise RuntimeError("Provider not initialized")

        try:
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=k
            )

            # 转换结果格式
            search_results = []
            if results["metadatas"] and results["distances"]:
                for metadata, distance in zip(results["metadatas"][0], results["distances"][0]):
                    # 将距离转换为相似度分数
                    similarity = 1.0 - distance
                    if similarity >= threshold:
                        search_results.append((similarity, metadata))

            logger.debug(f"搜索到 {len(search_results)} 个相似结果")
            return search_results

        except Exception as e:
            logger.error(f"搜索向量失败: {e}")
            return []

    def delete_vector(self, doc_id: str) -> bool:
        """删除指定向量"""
        if not self.is_initialized:
            raise RuntimeError("Provider not initialized")

        try:
            self.collection.delete(ids=[doc_id])
            logger.debug(f"向量删除成功: {doc_id}")
            return True

        except Exception as e:
            logger.error(f"删除向量失败: {e}")
            return False

    def save(self) -> bool:
        """保存向量数据库（ChromaDB自动持久化）"""
        return True

    def get_info(self) -> Dict[str, Any]:
        """获取提供商信息"""
        info = super().get_info()
        if self.is_initialized and self.collection:
            try:
                count = self.collection.count()
                info.update({
                    "collection_name": self.collection_name,
                    "vector_count": count
                })
            except:
                pass
        return info