from .database.schema_manager import SchemaManager
from .database.sql_validator import SQLValidator
from .rag.embedding.bert_embedding_model import BertEmbedding
from .rag.vectordb.vector_store import InMemoryVectorStore
from .llm.deepseek import Deepseek
import logging

logger = logging.getLogger(__name__)


class Text2SQL:
    def __init__(self):
        self.schema_manager = SchemaManager()
        self.bert_embedding_model = BertEmbedding()
        self.vectore_store = InMemoryVectorStore()
        self.deepseek = Deepseek()
        self.sql_validator = SQLValidator()

    def generate_sql(self, prompt):
        try:
            # 提取表结构
            schema_info = self.schema_manager.extract_schema()
            format_schema_for_prompt = self.schema_manager.format_schema_for_prompt(
                schema_info
            )
            # 将 prompt 转换为嵌入向量
            prompt_to_vector = self.bert_embedding_model.get_embedding(prompt)

            # 从向量存储库中搜索问题及其 sql
            similar_example = self.vectore_store.search(prompt_to_vector)
            examples = []
            for _, metadata in similar_example:
                examples.append(metadata)

            # 使用 LLM 生成 SQL 语句
            sql = self.deepseek.get_response(prompt, format_schema_for_prompt)

            # 验证生成的SQL
            is_sql_safe, error_message, columns = self.sql_validator.test_execute(sql)

            if is_sql_safe:
                # 添加新的元数据
                metadata = {"question": prompt, "sql": sql}
                self.vectore_store.add_vector(prompt_to_vector, metadata)
                self.vectore_store.save()
            else:
                logger.warning(f"SQL验证失败: {error_message}")

            return {
                "success": is_sql_safe,
                "sql": sql,
                "error": error_message if not is_sql_safe else None,
                "columns": columns if is_sql_safe else [],
                "similar_examples": examples[:3],  # 仅返回前3个示例
            }

        except Exception as e:
            logger.error(f"生成 SQL 过程出错:{e}")
            return {
                "success": False,
                "sql": "",
                "error": f"SQL生成过程出错: {str(e)}",
                "columns": [],
                "similar_examples": [],
            }
