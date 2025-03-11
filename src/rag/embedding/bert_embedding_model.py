import random
import torch
from sentence_transformers import SentenceTransformer
from ...config import Config
from sklearn.metrics.pairwise import cosine_similarity
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BertEmbedding:
    """BERT文本嵌入模型

    使用SentenceTransformer获取文本的向量表示。
    """

    def __init__(self, device=None, cache_size=1000):
        """初始化BERT嵌入模型

        Args:
            device: 运行模型的设备，默认为None，会自动选择可用的GPU或CPU
            cache_size: 向量缓存大小，默认为1000
        """
        self.model = None
        self.model_name = Config.BERT_MODEL_NAME
        self.vector_size = None
        self.device = (
            device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self.cache = {}
        self.cache_size = cache_size

        self.set_random_seed()
        self.load_model()

    def set_random_seed(self, seed=42):
        """设置随机种子以确保结果可重现

        Args:
            seed: 随机种子，默认为42
        """
        random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        logger.info(f"已设置随机种子: {seed}")

    def load_model(self):
        """加载预训练的SentenceTransformer模型"""
        try:
            self.model = SentenceTransformer(self.model_name, device=self.device)
            self.vector_size = self.model.get_sentence_embedding_dimension()
            logger.info(
                f"BERT模型 '{self.model_name}' 在 {self.device} 上加载成功，向量维度: {self.vector_size}"
            )
        except Exception as e:
            logger.error(f"加载BERT模型失败: {str(e)}")
            raise

    def get_embedding(self, text):
        """获取单个文本的嵌入向量

        Args:
            text: 输入文本

        Returns:
            numpy数组，表示文本的嵌入向量

        Raises:
            ValueError: 当模型未加载时
        """
        if self.model is None:
            raise ValueError("模型未加载，请先调用load_model方法")

        # 检查缓存
        if text in self.cache:
            return self.cache[text]

        with torch.no_grad():
            embedding = self.model.encode(text, convert_to_numpy=True)

        # 更新缓存
        if len(self.cache) >= self.cache_size:
            # 简单的LRU策略: 移除一个随机键
            self.cache.pop(next(iter(self.cache)))

        self.cache[text] = embedding
        return embedding

    def get_embeddings(self, texts, batch_size=32):
        """获取多个文本的嵌入向量（批处理）

        Args:
            texts: 输入文本列表
            batch_size: 批处理大小，默认为32

        Returns:
            numpy数组，每行表示一个文本的嵌入向量

        Raises:
            ValueError: 当模型未加载时
        """
        if self.model is None:
            raise ValueError("模型未加载，请先调用load_model方法")

        with torch.no_grad():
            embeddings = self.model.encode(
                texts, batch_size=batch_size, convert_to_numpy=True
            )

        return embeddings

    def compute_similarity(self, text1, text2):
        """计算两个文本之间的相似度

        Args:
            text1: 第一个文本
            text2: 第二个文本

        Returns:
            float: 表示两个文本的余弦相似度，范围[-1, 1]
        """
        emb1 = self.get_embedding(text1).reshape(1, -1)
        emb2 = self.get_embedding(text2).reshape(1, -1)

        return cosine_similarity(emb1, emb2)[0][0]

    @property
    def embedding_dim(self):
        """获取嵌入向量的维度

        Returns:
            int: 嵌入向量的维度
        """
        return self.vector_size
