# pylint: disable=too-many-function-args
import logging
import uuid
import chromadb
from chromadb.api import ClientAPI
from ...config import Config

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    def __init__(self):
        try:
            self.client = self.get_chroma_client()

            self.client.heartbeat()

            self.collection_name = Config.CHROMA_COLLECTION_NAME

            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=None,
            )

        except Exception as e:
            logger.error(f"初始化ChromaVectorStore失败: {e}", exc_info=True)
            raise

    _client = None

    @staticmethod
    def get_chroma_client() -> ClientAPI:
        if _client is None:
            _client = chromadb.CloudClient(
                api_key=Config.CHROMA_API_KEY,
                tenant=Config.CHROMA_TENANT,
                database=Config.CHROMA_DATABASE,
            )
        return _client

    def add_vector(self, vector, metadata):
        self.add_vectors([vector], [metadata])

    def add_vectors(self, vectors, metadata_list):
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
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name
        )
        logger.info(f"Chroma集合 '{self.collection_name}' 已清空并重建")

    def save(self):
        logger.info("ChromaDB Cloud 会自动持久化数据")

    def load(self):
        try:
            self.client.get_collection(name=self.collection_name)
            logger.info(f"成功连接到已存在的Chroma集合 '{self.collection_name}'")
            return True
        except Exception as e:
            logger.warning(f"Chroma集合 '{self.collection_name}' 不存在或无法访问: {e}")
            return False

    def __len__(self):
        return self.collection.count()
