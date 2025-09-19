from typing import Dict, Any, List
from ..core.ai_engine import AIEngine, EngineCapability
from ..text_to_sql import Text2SQL
import logging

logger = logging.getLogger(__name__)


class Text2SQLEngine(AIEngine):
    """Text2SQL引擎实现

    将Text2SQL功能封装为可插拔的AI引擎
    """

    def __init__(self):
        super().__init__(
            name="text2sql_engine", version="1.0.0", description="自然语言转SQL查询引擎"
        )
        self.text2sql_service: Text2SQL = None

    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化Text2SQL引擎"""
        try:
            # 初始化Text2SQL服务 (不再需要配置参数)
            self.text2sql_service = Text2SQL()

            # 添加能力描述
            self.add_capability(
                EngineCapability(
                    name="natural_language_to_sql",
                    description="将自然语言查询转换为SQL语句",
                    input_types=["text"],
                    output_types=["sql", "json"],
                    parameters={
                        "supports_validation": True,
                        "supports_few_shot": True,
                        "supports_schema_extraction": True,
                    },
                )
            )

            self.is_initialized = True
            logger.info(f"Text2SQL引擎初始化成功")
            return True

        except Exception as e:
            logger.error(f"Text2SQL引擎初始化失败: {e}")
            return False

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理自然语言转SQL请求"""
        if not self.is_initialized:
            raise RuntimeError("引擎未初始化")

        try:
            # 提取查询文本
            query = input_data.get("query", "")
            if not query:
                raise ValueError("缺少查询文本")

            # 调用Text2SQL服务
            result = self.text2sql_service.generate_sql(query)

            # 标准化输出格式
            return {
                "success": result.get("success", False),
                "sql": result.get("sql", ""),
                "error": result.get("error"),
                "columns": result.get("columns", []),
                "similar_examples": result.get("similar_examples", []),
                "schema_info": result.get("schema_info", ""),
                "metadata": {
                    "engine": self.name,
                    "version": self.version,
                    "query": query,
                },
            }

        except Exception as e:
            logger.error(f"Text2SQL引擎处理失败: {e}")
            return {
                "success": False,
                "sql": "",
                "error": f"处理失败: {str(e)}",
                "columns": [],
                "similar_examples": [],
                "schema_info": "",
                "metadata": {
                    "engine": self.name,
                    "version": self.version,
                    "query": input_data.get("query", ""),
                },
            }

    def get_capabilities(self) -> List[EngineCapability]:
        """获取引擎能力"""
        return self._capabilities

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        base_health = super().health_check()

        # 添加具体的健康检查逻辑
        try:
            if self.text2sql_service:
                # 可以添加更具体的健康检查，如数据库连接测试
                base_health["components"] = {
                    "text2sql_service": "healthy",
                    "schema_manager": "healthy",
                    "vector_store": "healthy",
                    "llm": "healthy",
                }
            else:
                base_health["healthy"] = False
                base_health["error"] = "Text2SQL服务未初始化"

        except Exception as e:
            base_health["healthy"] = False
            base_health["error"] = str(e)

        return base_health
