import numpy as np
import os
import pickle
from ...config import Config
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)

class InMemoryVectorStore:
    def __init__(self, save_path=None):
        """初始化内存向量存储
        
        Args:
            save_path: 向量存储保存路径，默认为None，使用配置中的路径
        """
        self.vectors = []  # 存储向量列表
        self.metadata = []  # 存储元数据列表
        self.save_path = save_path or "data/vector_store.pkl"
        
    def add_vector(self, vector, metadata):
        """添加向量及其元数据到存储
        
        Args:
            vector: numpy数组，表示文本的嵌入向量
            metadata: 与向量关联的元数据（例如问题-SQL对）
        """
        # 确保向量是一维数组
        if len(vector.shape) > 1:
            vector = vector.flatten()
            
        self.vectors.append(vector)
        self.metadata.append(metadata)
        logger.debug(f"添加向量，当前存储量: {len(self.vectors)}")
        
    def add_vectors(self, vectors, metadata_list):
        """批量添加向量及其元数据
        
        Args:
            vectors: 向量列表
            metadata_list: 元数据列表
        """
        assert len(vectors) == len(metadata_list), "向量和元数据数量必须一致"
        
        for vector, metadata in zip(vectors, metadata_list):
            self.add_vector(vector, metadata)
            
    def search(self, query_vector, top_k=5):
        """搜索与查询向量最相似的向量
        
        Args:
            query_vector: 查询向量
            top_k: 返回的最相似向量数量
            
        Returns:
            列表，包含元组(相似度, 元数据)，按相似度降序排序
        """
        if not self.vectors:
            logger.warning("向量存储为空，无法执行搜索")
            return []
            
        # 确保查询向量是一维数组
        if len(query_vector.shape) > 1:
            query_vector = query_vector.flatten()
            
        # 向量化计算相似度，性能更好
        vectors_array = np.array(self.vectors)
        query_vector = query_vector.reshape(1, -1)
        
        # 使用sklearn的余弦相似度计算，支持批量计算
        similarities = cosine_similarity(query_vector, vectors_array)[0]
        
        # 获取top_k个最相似的索引
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        # 构建结果列表
        results = [(similarities[i], self.metadata[i]) for i in top_indices]
        
        return results
    
    def clear(self):
        """清空向量存储"""
        self.vectors = []
        self.metadata = []
        logger.info("向量存储已清空")
        
    def save(self):
        """保存向量存储到文件"""
        os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
        with open(self.save_path, "wb") as f:
            pickle.dump({"vectors": self.vectors, "metadata": self.metadata}, f)
        logger.info(f"向量存储已保存到 {self.save_path}，共 {len(self.vectors)} 个向量")
            
    def load(self):
        """从文件加载向量存储"""
        if os.path.exists(self.save_path):
            try:
                with open(self.save_path, "rb") as f:
                    data = pickle.load(f)
                    self.vectors = data["vectors"]
                    self.metadata = data["metadata"]
                logger.info(f"从 {self.save_path} 加载了 {len(self.vectors)} 个向量")
                return True
            except Exception as e:
                logger.error(f"加载向量存储失败: {str(e)}")
                return False
        else:
            logger.warning(f"向量存储文件 {self.save_path} 不存在")
            return False
            
    def __len__(self):
        """返回存储的向量数量"""
        return len(self.vectors)