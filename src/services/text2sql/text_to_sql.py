# pylint: disable=astroid-error
# -*- coding: utf-8 -*-
from src.providers.database.schema_manager import SchemaManager
from src.providers.database.sql_validator import SQLValidator
from src.providers.vectordb.chroma_vector_store import ChromaVectorStore
from .embedding.bert_embedding_model import BertEmbedding
from .chunking.schema_chunker import SchemaChunker
from .reranking.cross_encoder_reranker import CrossEncoderReranker
from .llm.llm import LLM
from src.core.config import Config
from deepeval.tracing import observe, update_current_span
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class Text2SQL:
    """自然语言转SQL查询系统

    将自然语言转换为SQL查询语句的系统，包括以下功能：
    - 提取数据库结构信息
    - 使用BERT模型进行文本嵌入
    - 向量存储和相似查询
    - 使用LLM生成SQL
    - SQL验证
    """

    def __init__(self):
        """初始化Text2SQL系统的各个组件"""
        logger.debug("Text2SQL.__init__ 调用")
        self.schema_manager = SchemaManager()
        self.bert_embedding_model = BertEmbedding()
        self.vector_store = ChromaVectorStore()
        self.schema_vector_store = ChromaVectorStore(
            collection_name=Config.SCHEMA_COLLECTION_NAME
        )
        self.llm = LLM()
        self.sql_validator = SQLValidator()
        self.schema_chunker = SchemaChunker()
        self.reranker = CrossEncoderReranker()

    @observe(name="embed_query", type="embedding")
    def _embed_query(self, prompt: str):
        """将用户查询转换为向量"""
        vector = self.bert_embedding_model.get_embedding(prompt)
        update_current_span(input=prompt, output=f"vector dim={len(vector)}")
        return vector

    @observe(name="schema_chunking", type="tool")
    def _schema_chunking(self, schema_info, query_vector):
        """Schema Chunking：检索相关表"""
        self.schema_chunker.ensure_indexed(
            schema_info, self.bert_embedding_model, self.schema_vector_store
        )
        relevant_tables = self.schema_chunker.retrieve_relevant_tables(
            query_vector, self.schema_vector_store, top_k=3, schema_info=schema_info
        )
        format_schema = self.schema_manager.format_partial_schema(
            relevant_tables, schema_info
        )
        update_current_span(
            input=f"query_vector (dim={len(query_vector)})",
            output=f"tables: {relevant_tables}",
        )
        return relevant_tables, format_schema

    @observe(name="example_retrieval", type="retriever")
    def _retrieve_examples(self, prompt: str, query_vector):
        """召回 + Re-ranking"""
        similar_example = self.vector_store.search(query_vector, top_k=10)
        candidates = [metadata for _, metadata in similar_example]
        examples = self.reranker.rerank(prompt, candidates, top_n=3)
        update_current_span(
            input=prompt,
            output=f"candidates={len(candidates)} -> reranked={len(examples)}",
        )
        return examples

    @observe(name="llm_generate_sql", type="llm")
    def _llm_generate(self, prompt: str, format_schema: str, examples: list):
        """LLM 生成 SQL"""
        sql = self.llm.get_response(prompt, format_schema, few_shot_example=examples)
        update_current_span(input=prompt, output=sql)
        return sql

    @observe(name="sql_validation", type="tool")
    def _validate_sql(self, sql: str):
        """SQL 验证"""
        is_safe, error_message, columns = self.sql_validator.test_execute(sql)
        if not is_safe and any(
            error in error_message.lower()
            for error in ["space left on device", "disk full"]
        ):
            is_safe, syntax_error = self.sql_validator.validate_syntax(sql)
            if is_safe:
                columns = []
                error_message = "SQL语法正确，但服务器磁盘空间不足，无法执行"
            else:
                error_message = syntax_error
        update_current_span(
            input=sql,
            output=f"valid={is_safe}, columns={columns}",
        )
        return is_safe, error_message, columns

    MAX_CORRECTION_RETRIES = 2

    @observe(name="sql_auto_correction", type="llm")
    def _auto_correct_sql(self, prompt: str, sql: str, error_message: str, format_schema: str):
        """基于执行错误反馈自动纠正 SQL"""
        correction_prompt = (
            f"以下 SQL 执行出错，请根据错误信息修正。\n\n"
            f"用户问题: {prompt}\n"
            f"原始 SQL: {sql}\n"
            f"错误信息: {error_message}\n\n"
            f"数据库结构:\n{format_schema}\n"
            f"请仅返回修正后的 SQL，不要解释。"
        )
        corrected_sql = self.llm.get_response(correction_prompt, format_schema)
        update_current_span(input=f"error: {error_message}", output=corrected_sql)
        logger.info(f"自动纠错生成的SQL: {corrected_sql}")
        return corrected_sql

    @observe(name="text2sql_pipeline", type="agent")
    def generate_sql(self, prompt: str) -> Dict[str, Any]:
        """生成SQL查询语句

        Args:
            prompt (str): 用户的自然语言查询

        Returns:
            Dict[str, Any]: 包含以下字段的结果字典：
                - success (bool): 是否成功生成有效的SQL
                - sql (str): 生成的SQL语句
                - error (Optional[str]): 错误信息（如果有）
                - columns (List[str]): 查询结果的列名
                - similar_examples (List[Dict]): 相似的查询示例
        """
        try:
            # 提取表结构
            logger.info("开始提取数据库结构")
            schema_info = self.schema_manager.extract_schema()

            # 将prompt转换为嵌入向量
            logger.info(f"开始处理用户查询: {prompt}")
            prompt_to_vector = self._embed_query(prompt)

            # Schema Chunking：检索相关表，生成精简schema
            logger.info("开始Schema Chunking")
            relevant_tables, format_schema = self._schema_chunking(schema_info, prompt_to_vector)
            logger.info(f"Schema Chunking完成，选中 {len(relevant_tables)} 个相关表")

            # 召回 + Re-ranking
            logger.info("开始检索和Re-ranking")
            examples = self._retrieve_examples(prompt, prompt_to_vector)
            logger.info(f"Re-ranking完成，选出 {len(examples)} 个高质量示例")

            # 使用LLM生成SQL语句
            logger.info("开始生成SQL语句")
            sql = self._llm_generate(prompt, format_schema, examples)
            logger.info(f"生成的SQL: {sql}")

            # 验证生成的SQL
            logger.info("开始验证SQL")
            is_sql_safe, error_message, columns = self._validate_sql(sql)

            # 执行反馈自动纠错：验证失败时重试
            for retry in range(self.MAX_CORRECTION_RETRIES):
                if is_sql_safe:
                    break
                logger.warning(f"SQL验证失败（第{retry+1}次纠错）: {error_message}")
                sql = self._auto_correct_sql(prompt, sql, error_message, format_schema)
                logger.info(f"纠错后的SQL: {sql}")
                is_sql_safe, error_message, columns = self._validate_sql(sql)

            # 处理验证结果
            if is_sql_safe:
                logger.info("SQL验证通过，保存到向量存储")
                metadata = {"question": prompt, "sql": sql}
                self.vector_store.add_vector(prompt_to_vector, metadata)
                self.vector_store.save()
            else:
                logger.warning(f"SQL验证失败: {error_message}")

            # 返回结果
            return {
                "success": is_sql_safe,
                "sql": sql,
                "error": error_message if not is_sql_safe else None,
                "columns": columns if is_sql_safe else [],
                "similar_examples": examples[:3],
                "schema_info": format_schema,
            }

        except Exception as e:
            logger.error(f"SQL生成过程出错: {str(e)}", exc_info=True)
            return {
                "success": False,
                "sql": "",
                "error": f"SQL生成过程出错: {str(e)}",
                "columns": [],
                "similar_examples": [],
                "schema_info": "",
            }
