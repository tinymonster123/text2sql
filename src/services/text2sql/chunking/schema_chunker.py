import hashlib
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class SchemaChunker:
    """Schema分块器

    将数据库Schema按表拆分为独立的chunk，
    支持向量化存储和相关表检索。
    """

    def __init__(self):
        self._indexed_hash = None

    def chunk_schema(self, schema_info: Dict[str, Any]) -> List[Dict]:
        """将schema按表拆分为chunk列表

        Args:
            schema_info: SchemaManager.extract_schema() 返回的schema字典

        Returns:
            chunk列表，每个chunk包含table_name、text和metadata
        """
        chunks = []
        for table_name, table_info in schema_info.items():
            text = self._format_table_text(table_name, table_info)
            chunks.append({
                "table_name": table_name,
                "text": text,
                "metadata": {"table_name": table_name},
            })
        return chunks

    def _format_table_text(self, table_name: str, table_info: Dict) -> str:
        """格式化单张表的schema为文本"""
        lines = [f"表名: {table_name}"]

        columns = table_info.get("columns", [])
        if columns:
            col_parts = []
            for col in columns:
                col_parts.append(f"{col['name']} ({col['type']})")
            lines.append(f"列: {', '.join(col_parts)}")

        pks = table_info.get("primary_keys", [])
        if pks:
            lines.append(f"主键: {', '.join(pks)}")

        return "\n".join(lines)

    def _compute_schema_hash(self, schema_info: Dict[str, Any]) -> str:
        """计算schema的hash值，用于判断是否需要重新索引"""
        raw = json.dumps(schema_info, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(raw.encode()).hexdigest()

    def ensure_indexed(self, schema_info, embedding_model, vector_store):
        """确保schema已索引到向量库（幂等操作）

        仅在schema变更或首次调用时重建索引。

        Args:
            schema_info: schema字典
            embedding_model: BertEmbedding实例
            vector_store: ChromaVectorStore实例（schema专用集合）
        """
        current_hash = self._compute_schema_hash(schema_info)
        if self._indexed_hash == current_hash:
            return

        logger.info("Schema发生变更或首次索引，开始重建schema向量索引")
        chunks = self.chunk_schema(schema_info)

        # 清空旧数据并重新写入
        vector_store.clear()

        texts = [chunk["text"] for chunk in chunks]
        embeddings = embedding_model.get_embeddings(texts)
        metadata_list = [chunk["metadata"] for chunk in chunks]

        vector_store.add_vectors(list(embeddings), metadata_list)
        vector_store.save()

        self._indexed_hash = current_hash
        logger.info(f"Schema向量索引重建完成，共 {len(chunks)} 个表")

    def retrieve_relevant_tables(self, query_vector, vector_store, top_k=3) -> List[str]:
        """检索与查询相关的表名

        Args:
            query_vector: 查询文本的嵌入向量
            vector_store: ChromaVectorStore实例（schema专用集合）
            top_k: 返回的表数量

        Returns:
            相关表名列表
        """
        results = vector_store.search(query_vector, top_k=top_k)
        table_names = [metadata.get("table_name") for _, metadata in results if metadata.get("table_name")]
        logger.info(f"Schema Chunking 检索到相关表: {table_names}")
        return table_names
