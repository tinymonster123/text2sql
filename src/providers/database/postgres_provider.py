from typing import Dict, Any, List, Tuple, Optional
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from .base_provider import BaseDatabaseProvider

logger = logging.getLogger(__name__)


class PostgreSQLProvider(BaseDatabaseProvider):
    """PostgreSQL数据库提供商 - 用于NeonDB serverless"""

    def __init__(self):
        super().__init__("postgresql")
        self.connection_config = {}
        self.connection = None

    def initialize(self, database_url: str) -> bool:
        """初始化PostgreSQL提供商"""
        try:
            if not database_url:
                raise ValueError("DATABASE_URL is required")

            # 直接使用DATABASE_URL连接
            self.database_url = database_url

            # 测试连接
            test_conn = psycopg2.connect(database_url)
            test_conn.close()

            self.is_initialized = True
            logger.info(f"PostgreSQL提供商初始化成功")
            return True

        except Exception as e:
            logger.error(f"PostgreSQL提供商初始化失败: {e}")
            return False

    def _get_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(self.database_url)

    def get_schema(self) -> Dict[str, Any]:
        """获取PostgreSQL数据库结构信息"""
        if not self.is_initialized:
            raise RuntimeError("Provider not initialized")

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # 查询表结构
                    schema_query = """
                    SELECT
                        t.table_name,
                        c.column_name,
                        c.data_type,
                        c.is_nullable,
                        c.column_default,
                        tc.constraint_type
                    FROM information_schema.tables t
                    LEFT JOIN information_schema.columns c ON t.table_name = c.table_name
                    LEFT JOIN information_schema.key_column_usage kcu ON c.table_name = kcu.table_name AND c.column_name = kcu.column_name
                    LEFT JOIN information_schema.table_constraints tc ON kcu.constraint_name = tc.constraint_name
                    WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
                    ORDER BY t.table_name, c.ordinal_position;
                    """

                    cursor.execute(schema_query)
                    results = cursor.fetchall()

                    # 组织数据结构
                    schema_info = {}
                    for row in results:
                        table_name = row["table_name"]
                        column_name = row["column_name"]

                        if table_name not in schema_info:
                            schema_info[table_name] = {
                                "columns": [],
                                "primary_keys": [],
                                "foreign_keys": [],
                            }

                        if column_name:  # 确保列名不为空
                            column_info = {
                                "name": column_name,
                                "type": row["data_type"],
                                "nullable": row["is_nullable"] == "YES",
                                "default": row["column_default"],
                            }

                            # 避免重复添加列
                            if not any(
                                col["name"] == column_name
                                for col in schema_info[table_name]["columns"]
                            ):
                                schema_info[table_name]["columns"].append(column_info)

                            if row["constraint_type"] == "PRIMARY KEY":
                                if (
                                    column_name
                                    not in schema_info[table_name]["primary_keys"]
                                ):
                                    schema_info[table_name]["primary_keys"].append(
                                        column_name
                                    )

                    # 查询外键关系
                    fk_query = """
                    SELECT
                        tc.table_name AS from_table,
                        kcu.column_name AS from_column,
                        ccu.table_name AS to_table,
                        ccu.column_name AS to_column
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage ccu
                        ON tc.constraint_name = ccu.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_schema = 'public';
                    """
                    cursor.execute(fk_query)
                    fk_results = cursor.fetchall()

                    for fk in fk_results:
                        from_table = fk["from_table"]
                        if from_table in schema_info:
                            fk_info = {
                                "from_column": fk["from_column"],
                                "to_table": fk["to_table"],
                                "to_column": fk["to_column"],
                            }
                            if fk_info not in schema_info[from_table]["foreign_keys"]:
                                schema_info[from_table]["foreign_keys"].append(fk_info)

                    return schema_info

        except Exception as e:
            logger.error(f"获取数据库结构失败: {e}")
            return {}

    def format_schema(self, schema_info: Dict[str, Any]) -> str:
        """格式化数据库结构为LLM可理解的文本"""
        if not schema_info:
            return "数据库结构信息为空"

        formatted_schema = "数据库表结构：\n\n"

        for table_name, table_info in schema_info.items():
            formatted_schema += f"表：{table_name}\n"

            # 列信息
            for column in table_info.get("columns", []):
                nullable = "NULL" if column["nullable"] else "NOT NULL"
                default = (
                    f" DEFAULT {column['default']}" if column.get("default") else ""
                )
                formatted_schema += (
                    f"  - {column['name']}: {column['type']} {nullable}{default}\n"
                )

            # 主键
            if table_info.get("primary_keys"):
                formatted_schema += f"  主键: {', '.join(table_info['primary_keys'])}\n"

            formatted_schema += "\n"

        return formatted_schema

    def execute_sql(self, sql: str) -> Tuple[bool, Optional[str], Optional[List[str]]]:
        """执行SQL语句"""
        if not self.is_initialized:
            raise RuntimeError("Provider not initialized")

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(sql)

                    # 获取列名
                    column_names = []
                    if cursor.description:
                        column_names = [desc[0] for desc in cursor.description]

                    return True, None, column_names

        except Exception as e:
            error_message = str(e)
            logger.error(f"SQL执行失败: {error_message}")
            return False, error_message, None

    def validate_sql(self, sql: str) -> Tuple[bool, Optional[str]]:
        """验证SQL语法"""
        if not self.is_initialized:
            raise RuntimeError("Provider not initialized")

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # 使用EXPLAIN来验证SQL语法，不实际执行
                    cursor.execute(f"EXPLAIN {sql}")

                    return True, None

        except Exception as e:
            error_message = str(e)
            logger.error(f"SQL验证失败: {error_message}")
            return False, error_message

    def get_info(self) -> Dict[str, Any]:
        """获取提供商信息"""
        info = super().get_info()
        if self.is_initialized:
            info.update({"database_url": "***configured***"})  # 隐藏敏感信息
        return info
