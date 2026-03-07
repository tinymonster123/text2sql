import logging
import os
import torch
from sentence_transformers import CrossEncoder
from src.core.config import Config
from typing import Dict, List

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Cross-Encoder重排序器

    使用Cross-Encoder模型对候选示例进行精排，
    提升few-shot示例的质量。
    """

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = Config.RERANKER_MODEL_NAME

        hf_endpoint = Config.HF_ENDPOINT
        if hf_endpoint:
            os.environ["HF_ENDPOINT"] = hf_endpoint

        self.model = CrossEncoder(self.model_name, device=self.device)
        logger.info(
            f"Cross-Encoder重排序模型 '{self.model_name}' 在 {self.device} 上加载成功"
        )

    def rerank(self, query: str, candidates: List[Dict], top_n: int = 3) -> List[Dict]:
        """对候选示例进行重排序

        Args:
            query: 用户查询文本
            candidates: 候选示例列表，每个元素包含 'question' 和 'sql' 字段
            top_n: 返回的top-N结果数量

        Returns:
            重排序后的top-N示例列表
        """
        if not candidates:
            return []

        if len(candidates) <= top_n:
            return candidates

        pairs = [(query, candidate.get("question", "")) for candidate in candidates]
        scores = self.model.predict(pairs)

        scored_candidates = list(zip(scores, candidates))
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        reranked = [candidate for _, candidate in scored_candidates[:top_n]]

        logger.info(
            f"Re-ranking 完成: {len(candidates)} 个候选 → top-{top_n}, "
            f"分数范围: [{scored_candidates[-1][0]:.4f}, {scored_candidates[0][0]:.4f}]"
        )

        return reranked
