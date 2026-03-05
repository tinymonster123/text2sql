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
            logger.info("数据库结构提取完成")

            # 将prompt转换为嵌入向量
            logger.info(f"开始处理用户查询: {prompt}")
            prompt_to_vector = self.bert_embedding_model.get_embedding(prompt)
            logger.info("向量嵌入完成")

            # Schema Chunking：检索相关表，生成精简schema
            logger.info("开始Schema Chunking")
            self.schema_chunker.ensure_indexed(
                schema_info, self.bert_embedding_model, self.schema_vector_store
            )
            relevant_tables = self.schema_chunker.retrieve_relevant_tables(
                prompt_to_vector, self.schema_vector_store, top_k=3
            )
            format_schema = self.schema_manager.format_partial_schema(
                relevant_tables, schema_info
            )
            logger.info(f"Schema Chunking完成，选中 {len(relevant_tables)} 个相关表")

            # 召回 top-10 相似示例
            logger.info("开始搜索相似查询")
            similar_example = self.vector_store.search(prompt_to_vector, top_k=10)
            candidates = [metadata for _, metadata in similar_example]
            logger.info(f"找到 {len(candidates)} 个候选查询")

            # Re-ranking：精排取 top-3
            logger.info("开始Re-ranking")
            examples = self.reranker.rerank(prompt, candidates, top_n=3)
            logger.info(f"Re-ranking完成，选出 {len(examples)} 个高质量示例")
            if examples:
                import json

                logger.info(
                    f"重排后的 Few-shot 示例:\n{json.dumps(examples, indent=2, ensure_ascii=False)}"
                )

            # 使用LLM生成SQL语句
            logger.info("开始生成SQL语句")
            sql = self.llm.get_response(
                prompt, format_schema, few_shot_example=examples
            )
            logger.info(f"生成的SQL: {sql}")

            # 验证生成的SQL
            logger.info("开始验证SQL")
            is_sql_safe, error_message, columns = self.sql_validator.test_execute(sql)

            if not is_sql_safe and any(
                error in error_message.lower()
                for error in ["space left on device", "disk full"]
            ):
                logger.warning("服务器磁盘空间不足，尝试仅进行语法验证")
                is_sql_safe, syntax_error = self.sql_validator.validate_syntax(sql)
                if is_sql_safe:
                    columns = []
                    error_message = "SQL语法正确，但服务器磁盘空间不足，无法执行"
                    logger.info("SQL语法验证通过")
                else:
                    error_message = syntax_error
                    logger.warning(f"SQL语法验证失败: {syntax_error}")

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
