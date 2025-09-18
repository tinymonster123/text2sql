from typing import Dict, Any, List, Tuple, Optional
import logging
from .base_provider import BaseDatabaseProvider

logger = logging.getLogger(__name__)


class PostgreSQLProvider(BaseDatabaseProvider):
    """PostgreSQL数据库提供商"""

    def __init__(self):
        super().__init__("postgresql")
        self.connection = None
        self.connection_params = {}

    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化PostgreSQL提供商"""
        try:
            import psycopg2
            from psycopg2 import sql

            self.connection_params = {
                "host": config.get("host", "localhost"),
                "port": config.get("port", 5432),
                "database": config.get("database", "postgres"),
                "user": config.get("user", "postgres"),
                "password": config.get("password", "")
            }

            # 测试连接
            self.connection = psycopg2.connect(**self.connection_params)
            self.connection.close()

            self.is_initialized = True
            logger.info(f"PostgreSQL提供商初始化成功: {self.connection_params['host']}:{self.connection_params['port']}")
            return True

        except Exception as e:
            logger.error(f"PostgreSQL提供商初始化失败: {e}")
            return False

    def _get_connection(self):
        """获取数据库连接"""
        import psycopg2
        return psycopg2.connect(**self.connection_params)

    def get_schema(self) -> Dict[str, Any]:
        """获取PostgreSQL数据库结构信息"""
        if not self.is_initialized:
            raise RuntimeError("Provider not initialized")

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

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
            for table_name, column_name, data_type, is_nullable, column_default, constraint_type in results:
                if table_name not in schema_info:
                    schema_info[table_name] = {
                        "columns": [],
                        "primary_keys": [],
                        "foreign_keys": []
                    }

                if column_name:  # 确保列名不为空
                    column_info = {
                        "name": column_name,
                        "type": data_type,
                        "nullable": is_nullable == "YES",
                        "default": column_default
                    }

                    schema_info[table_name]["columns"].append(column_info)

                    if constraint_type == "PRIMARY KEY":
                        schema_info[table_name]["primary_keys"].append(column_name)

            cursor.close()
            conn.close()

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
                default = f" DEFAULT {column['default']}" if column.get("default") else ""
                formatted_schema += f"  - {column['name']}: {column['type']} {nullable}{default}\n"

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
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(sql)

            # 获取列名
            column_names = []
            if cursor.description:
                column_names = [desc[0] for desc in cursor.description]

            conn.commit()
            cursor.close()
            conn.close()

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
            conn = self._get_connection()
            cursor = conn.cursor()

            # 使用EXPLAIN来验证SQL语法，不实际执行
            cursor.execute(f"EXPLAIN {sql}")

            cursor.close()
            conn.close()

            return True, None

        except Exception as e:
            error_message = str(e)
            logger.error(f"SQL验证失败: {error_message}")
            return False, error_message

    def get_info(self) -> Dict[str, Any]:
        """获取提供商信息"""
        info = super().get_info()
        if self.is_initialized:
            info.update({
                "host": self.connection_params.get("host"),
                "port": self.connection_params.get("port"),
                "database": self.connection_params.get("database")
            })
        return info