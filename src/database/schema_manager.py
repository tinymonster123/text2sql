from .connection import MySQLSSHConnection
import json
import os


class SchemaManager:
    def __init__(self):
        self.connection = MySQLSSHConnection()
        self.schema_cache_path = "data/schema_cache.json"

    def extract_schema(self, force_refresh=False):
        """
        提取数据库Schema信息

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            以字符串形式返回数据库Schema信息
        """
        # 检查缓存
        if not force_refresh and os.path.exists(self.schema_cache_path):
            with open(self.schema_cache_path, "r", encoding="utf-8") as f:
                return json.load(f)

        schema_info = {}
        cursor = None

        try:
            cursor = self.connection.connect()

            # 获取所有表
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]

            # 获取每个表的详细信息
            for table in tables:
                # 获取表结构
                cursor.execute(f"DESCRIBE `{table}`")
                columns = cursor.fetchall()

                table_info = {"columns": [], "primary_keys": [], "foreign_keys": []}

                for col in columns:
                    column_name = col[0]
                    column_type = col[1]
                    is_nullable = col[2]
                    key_type = col[3]
                    default = col[4]

                    column_info = {
                        "name": column_name,
                        "type": column_type,
                        "nullable": is_nullable == "YES",
                        "default": default,
                    }

                    table_info["columns"].append(column_info)

                    # 记录主键
                    if key_type == "PRI":
                        table_info["primary_keys"].append(column_name)

                # 获取外键信息
                try:
                    cursor.execute(
                        f"""
                    SELECT 
                        COLUMN_NAME, 
                        REFERENCED_TABLE_NAME, 
                        REFERENCED_COLUMN_NAME
                    FROM 
                        INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                    WHERE 
                        TABLE_NAME = '{table}'
                        AND REFERENCED_TABLE_NAME IS NOT NULL
                        AND CONSTRAINT_SCHEMA = DATABASE()
                    """
                    )

                    foreign_keys = cursor.fetchall()
                    for fk in foreign_keys:
                        table_info["foreign_keys"].append(
                            {
                                "column": fk[0],
                                "referenced_table": fk[1],
                                "referenced_column": fk[2],
                            }
                        )
                except Exception:
                    # 某些情况下可能无法获取外键信息
                    pass

                schema_info[table] = table_info

            # 缓存结果
            os.makedirs(os.path.dirname(self.schema_cache_path), exist_ok=True)
            with open(self.schema_cache_path, "w", encoding="utf-8") as f:
                json.dump(schema_info, f, ensure_ascii=False, indent=2)

            return schema_info

        finally:
            self.connection.close()

    def format_schema_for_prompt(self, schema_info=None):
        """
        将Schema信息格式化为适合提示的文本形式

        Returns:
            格式化后的Schema字符串
        """
        if schema_info is None:
            schema_info = self.extract_schema()

        formatted_text = []
        formatted_text.append("数据库架构信息:")

        for table_name, table_info in schema_info.items():
            formatted_text.append(f"\n表名: {table_name}")

            # 添加列信息
            formatted_text.append("列:")
            for column in table_info["columns"]:
                nullable = "NULL" if column["nullable"] else "NOT NULL"
                default = f"DEFAULT {column['default']}" if column["default"] else ""
                formatted_text.append(
                    f"  - {column['name']} {column['type']} {nullable} {default}"
                )

            # 添加主键信息
            if table_info["primary_keys"]:
                formatted_text.append("主键:")
                for pk in table_info["primary_keys"]:
                    formatted_text.append(f"  - {pk}")

            # 添加外键信息
            if table_info["foreign_keys"]:
                formatted_text.append("外键:")
                for fk in table_info["foreign_keys"]:
                    formatted_text.append(
                        f"  - {fk['column']} -> {fk['referenced_table']}.{fk['referenced_column']}"
                    )

        return "\n".join(formatted_text)
