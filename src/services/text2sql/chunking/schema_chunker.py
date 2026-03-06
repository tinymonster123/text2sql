import hashlib
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class SchemaChunker:
    """Schema分块器

    将数据库Schema按表拆分为独立的chunk，
    支持向量化存储和相关表检索。
    表描述和关联关系从数据库外键元数据自动提取。
    """

    def __init__(self):
        self._indexed_hash = None

    def _extract_relations(self, table_name: str, schema_info: Dict) -> str:
        """从 schema_info 的外键信息自动提取表关联描述"""
        relations = []

        # 当前表的外键（指向其他表）
        for fk in schema_info.get(table_name, {}).get("foreign_keys", []):
            relations.append(f"通过 {fk['from_column']} 关联 {fk['to_table']}")

        # 其他表指向当前表的外键
        for other_table, other_info in schema_info.items():
            if other_table == table_name:
                continue
            for fk in other_info.get("foreign_keys", []):
                if fk["to_table"] == table_name:
                    relations.append(f"被 {other_table} 通过 {fk['from_column']} 引用")

        return "、".join(relations) if relations else ""

    def _extract_column_summary(self, table_info: Dict) -> str:
        """从列名自动生成列摘要"""
        columns = table_info.get("columns", [])
        col_names = [col["name"] for col in columns]
        return ", ".join(col_names)

    def chunk_schema(self, schema_info: Dict[str, Any]) -> List[Dict]:
        """将schema按表拆分为chunk列表

        Args:
            schema_info: SchemaManager.extract_schema() 返回的schema字典

        Returns:
            chunk列表，每个chunk包含table_name、text和metadata
        """
        chunks = []
        for table_name, table_info in schema_info.items():
            text = self._format_table_text(table_name, table_info, schema_info)
            chunks.append({
                "table_name": table_name,
                "text": text,
                "metadata": {"table_name": table_name},
            })
        return chunks

    def _format_table_text(self, table_name: str, table_info: Dict, schema_info: Dict) -> str:
        """格式化单张表的schema为语义增强文本"""
        lines = [f"表名: {table_name}"]

        # 自动提取关联关系
        relations = self._extract_relations(table_name, schema_info)
        if relations:
            lines.append(f"关联: {relations}")

        # 列信息
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
        """计算schema的hash值，用于判断是否需要重新索引

        包含外键信息，确保 schema 结构变更时触发重建。
        """
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

    def _find_primary_table(self, schema_info: Dict) -> str:
        """自动识别主表：被其他表外键引用最多的表"""
        ref_count = {}
        for table_name, table_info in schema_info.items():
            for fk in table_info.get("foreign_keys", []):
                target = fk["to_table"]
                ref_count[target] = ref_count.get(target, 0) + 1
        if ref_count:
            return max(ref_count, key=ref_count.get)
        return ""

    def retrieve_relevant_tables(self, query_vector, vector_store, top_k=3, schema_info=None) -> List[str]:
        """检索与查询相关的表名

        如果检索到子表但未包含主表，自动补充主表。
        主表通过外键引用关系自动识别。

        Args:
            query_vector: 查询文本的嵌入向量
            vector_store: ChromaVectorStore实例（schema专用集合）
            top_k: 返回的表数量
            schema_info: schema字典，用于自动识别主表

        Returns:
            相关表名列表
        """
        results = vector_store.search(query_vector, top_k=top_k)
        table_names = [metadata.get("table_name") for _, metadata in results if metadata.get("table_name")]

        # 自动识别主表并补充
        if schema_info:
            primary_table = self._find_primary_table(schema_info)
            if primary_table and primary_table not in table_names:
                # 检查是否有子表引用了主表
                has_sub_table = False
                for t in table_names:
                    for fk in schema_info.get(t, {}).get("foreign_keys", []):
                        if fk["to_table"] == primary_table:
                            has_sub_table = True
                            break
                if has_sub_table:
                    table_names.insert(0, primary_table)
                    logger.info(f"自动补充主表 {primary_table}")

        logger.info(f"Schema Chunking 检索到相关表: {table_names}")
        return table_names
