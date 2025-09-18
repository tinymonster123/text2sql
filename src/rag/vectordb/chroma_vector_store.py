import logging
import uuid
import chromadb
from ...config import Config

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    def __init__(self, save_path=None, host: str = None, port: int = None):
        try:
            chroma_host = host if host is not None else Config.CHROMA_HOST
            chroma_port = port if port is not None else Config.CHROMA_PORT

            logger.info("正在尝试连接到ChromaDB服务器...")
            logger.info(f"使用的Chroma主机: {chroma_host}")
            logger.info(f"使用的Chroma端口: {chroma_port}")

            self.client = chromadb.HttpClient(
                host=chroma_host,
                port=chroma_port,
            )
            logger.info("成功创建ChromaDB HttpClient。")

            logger.info("正在检查与ChromaDB服务器的心跳...")
            self.client.heartbeat()
            logger.info("ChromaDB服务器心跳正常，连接成功。")

            self.collection_name = Config.CHROMA_COLLECTION_NAME
            logger.info(f"准备获取或创建集合: '{self.collection_name}'")

            self.collection = self.client.get_or_create_collection(
                name=self.collection_name
            )
            logger.info(f"成功加载或创建Chroma集合 '{self.collection_name}'")

        except Exception as e:
            logger.error(f"初始化ChromaVectorStore失败: {e}", exc_info=True)
            raise

    def add_vector(self, vector, metadata):
        """添加向量及其元数据到存储

        Args:
            vector: numpy数组，表示文本的嵌入向量
            metadata: 与向量关联的元数据（例如问题-SQL对）
        """
        self.add_vectors([vector], [metadata])

    def add_vectors(self, vectors, metadata_list):
        """批量添加向量及其元数据

        Args:
            vectors: 向量列表
            metadata_list: 元数据列表
        """
        if not vectors or not metadata_list:
            return

        assert len(vectors) == len(metadata_list), "向量和元数据数量必须一致"

        embeddings = [v.flatten().tolist() for v in vectors]
        documents = [item.get("question", "") for item in metadata_list]
        ids = [str(uuid.uuid4()) for _ in metadata_list]

        self.collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadata_list,
            ids=ids,
        )
        logger.info(
            f"向Chroma集合 '{self.collection_name}' 中批量插入 {len(vectors)} 个向量"
        )

    def search(self, query_vector, top_k=5):
        """搜索与查询向量最相似的向量

        Args:
            query_vector: 查询向量
            top_k: 返回的最相似向量数量

        Returns:
            列表，包含元组(相似度, 元数据)，按相似度降序排序
        """
        if len(query_vector.shape) > 1:
            query_vector = query_vector.flatten()

        results = self.collection.query(
            query_embeddings=[query_vector.tolist()],
            n_results=top_k,
        )

        formatted_results = []
        if results and results["metadatas"] and results["distances"]:
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]
            for i in range(len(metadatas)):
                metadata = metadatas[i]
                similarity = 1 - distances[i]
                formatted_results.append((similarity, metadata))

        formatted_results.sort(key=lambda x: x[0], reverse=True)

        return formatted_results

    def clear(self):
        """清空向量存储（删除并重建集合）"""
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name
        )
        logger.info(f"Chroma集合 '{self.collection_name}' 已清空并重建")

    def save(self):
        """保存向量存储到文件（在ChromaDB中此操作是服务器端的）"""
        logger.info(f"服务器 '{Config.CHROMA_HOST}' 上的 ChromaDB 会自动持久化数据")

    def load(self):
        """从文件加载向量存储（在ChromaDB中此操作是连接和检查）"""
        try:
            self.client.get_collection(name=self.collection_name)
            logger.info(f"成功连接到已存在的Chroma集合 '{self.collection_name}'")
            return True
        except Exception as e:
            logger.warning(f"Chroma集合 '{self.collection_name}' 不存在或无法访问: {e}")
            return False

    def __len__(self):
        """返回存储的向量数量"""
        return self.collection.count()