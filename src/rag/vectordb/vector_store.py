import numpy as np
import os
import pickle
from ...config import Config


class InMemoryVectorStore:
    def __init__(self):
        self.vectors = []
        self.metadata = []
        self.save_path = "data/vector_store.pkl"

    def add_vector(self, vector, metadata):
        """添加向量及其元数据到存储

        Args:
            vector: numpy数组格式的向量
            metadata: 与向量相关的元数据
        """
        self.vectors.append(vector)
        self.metadata.append(metadata)

    def search(self, query_vector, top_k=5):
        """搜索最相似的向量

        Args:
            query_vector: 查询向量
            top_k: 返回的结果数量

        Returns:
            列表，包含(相似度, 元数据)元组
        """
        if not self.vectors:
            return []

        # 计算余弦相似度
        similarities = []
        for vec in self.vectors:
            sim = self._cosine_similarity(query_vector, vec)
            similarities.append(sim)

        # 获取top_k个结果
        indices = np.argsort(similarities)[-top_k:][::-1]
        results = [(similarities[i], self.metadata[i]) for i in indices]

        return results

    def _cosine_similarity(self, vec1, vec2):
        """计算两个向量的余弦相似度"""
        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        return dot / (norm1 * norm2)

    def save(self):
        """保存向量存储到磁盘"""
        os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
        with open(self.save_path, "wb") as f:
            pickle.dump({"vectors": self.vectors, "metadata": self.metadata}, f)

    def load(self):
        """从磁盘加载向量存储"""
        if os.path.exists(self.save_path):
            with open(self.save_path, "rb") as f:
                data = pickle.load(f)
                self.vectors = data["vectors"]
                self.metadata = data["metadata"]
            return True
        return False
