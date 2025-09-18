# -*- coding: utf-8 -*-
from .connection import MySQLSSHConnection
import json
import os
import logging

logger = logging.getLogger(__name__)


class SchemaManager:
    """数据库Schema管理器

    负责提取和格式化数据库结构信息。
    """

    def __init__(self):
        """初始化Schema管理器"""
        self.connection = MySQLSSHConnection()
        self.schema_cache_path = "data/schema_cache.json"

    def extract_schema(self, force_refresh=False):
        """提取数据库Schema信息

        Args:
            force_refresh (bool): 是否强制刷新缓存

        Returns:
            dict: 数据库Schema信息

        Raises:
            Exception: 提取Schema失败时抛出异常
        """
        # 检查缓存
        if not force_refresh and os.path.exists(self.schema_cache_path):
            with open(self.schema_cache_path, "r", encoding="utf-8") as f:
                logger.info("从缓存加载Schema信息")
                return json.load(f)

        schema_info = {}
        cursor = None

        try:
            cursor = self.connection.connect()
            logger.info("开始提取数据库Schema信息")

            # 获取所有表
            cursor.execute("SHOW TABLES")
            tables_result = cursor.fetchall()

            # 适配不同类型的cursor返回结果
            if isinstance(tables_result[0], dict):
                table_key = list(tables_result[0].keys())[0]
                tables = [table[table_key] for table in tables_result]
            else:
                tables = [table[0] for table in tables_result]

            logger.info(f"发现 {len(tables)} 个表")

            # 获取每个表的详细信息
            for table in tables:
                logger.info(f"正在处理表: {table}")
                table_info = self._extract_table_info(cursor, table)
                schema_info[table] = table_info

            # 缓存结果
            self._save_schema_cache(schema_info)
            logger.info("Schema信息提取完成")

            return schema_info

        except Exception as e:
            logger.error(f"提取数据库结构失败: {str(e)}")
            raise
        finally:
            self.connection.close()

    def _extract_table_info(self, cursor, table):
        """提取单个表的详细信息

        Args:
            cursor: 数据库游标
            table (str): 表名

        Returns:
            dict: 表的详细信息
        """
        table_info = {"columns": [], "primary_keys": [], "foreign_keys": []}

        # 获取表结构
        cursor.execute(f"DESCRIBE `{table}`")
        columns = cursor.fetchall()

        # 处理列信息
        self._process_columns(columns, table_info)

        # 获取外键信息
        self._process_foreign_keys(cursor, table, table_info)

        return table_info

    def _process_columns(self, columns, table_info):
        """处理表的列信息

        Args:
            columns (list): 列信息列表
            table_info (dict): 表信息字典
        """
        if isinstance(columns[0], dict):
            for col in columns:
                column_info = {
                    "name": col["Field"],
                    "type": col["Type"],
                    "nullable": col["Null"] == "YES",
                    "default": col["Default"],
                }
                table_info["columns"].append(column_info)

                if col["Key"] == "PRI":
                    table_info["primary_keys"].append(col["Field"])
        else:
            for col in columns:
                column_info = {
                    "name": col[0],
                    "type": col[1],
                    "nullable": col[2] == "YES",
                    "default": col[4],
                }
                table_info["columns"].append(column_info)

                if col[3] == "PRI":
                    table_info["primary_keys"].append(col[0])

    def _process_foreign_keys(self, cursor, table, table_info):
        """处理表的外键信息

        Args:
            cursor: 数据库游标
            table (str): 表名
            table_info (dict): 表信息字典
        """
        try:
            cursor.execute(
                """
                SELECT 
                    COLUMN_NAME, 
                    REFERENCED_TABLE_NAME, 
                    REFERENCED_COLUMN_NAME
                FROM 
                    INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE 
                    TABLE_NAME = %s
                    AND REFERENCED_TABLE_NAME IS NOT NULL
                    AND CONSTRAINT_SCHEMA = DATABASE()
            """,
                (table,),
            )

            foreign_keys = cursor.fetchall()

            if foreign_keys:
                if isinstance(foreign_keys[0], dict):
                    for fk in foreign_keys:
                        table_info["foreign_keys"].append(
                            {
                                "column": fk["COLUMN_NAME"],
                                "referenced_table": fk["REFERENCED_TABLE_NAME"],
                                "referenced_column": fk["REFERENCED_COLUMN_NAME"],
                            }
                        )
                else:
                    for fk in foreign_keys:
                        table_info["foreign_keys"].append(
                            {
                                "column": fk[0],
                                "referenced_table": fk[1],
                                "referenced_column": fk[2],
                            }
                        )

        except Exception as e:
            logger.warning(f"获取表 {table} 的外键信息失败: {str(e)}")

    def _save_schema_cache(self, schema_info):
        """保存Schema信息到缓存文件

        Args:
            schema_info (dict): Schema信息
        """
        try:
            os.makedirs(os.path.dirname(self.schema_cache_path), exist_ok=True)
            with open(self.schema_cache_path, "w", encoding="utf-8") as f:
                json.dump(schema_info, f, ensure_ascii=False, indent=2)
            logger.info(f"Schema信息已缓存到: {self.schema_cache_path}")
        except Exception as e:
            logger.error(f"缓存Schema信息失败: {str(e)}")

    def format_schema_for_prompt(self, schema_info=None):
        """将Schema信息格式化为适合提示的文本形式

        Args:
            schema_info (dict, optional): Schema信息。如果为None，则重新提取

        Returns:
            str: 格式化后的Schema字符串
        """
        if schema_info is None:
            schema_info = self.extract_schema()

        formatted_text = ["数据库架构信息:"]

        for table_name, table_info in schema_info.items():
            # 添加表名
            formatted_text.append(f"\n表名: {table_name}")

            # 添加列信息
            formatted_text.append("列:")
            for column in table_info["columns"]:
                nullable = "NULL" if column["nullable"] else "NOT NULL"
                default = f"DEFAULT {column['default']}" if column["default"] else ""
                formatted_text.append(
                    f"  - {column['name']} {column['type']} {nullable} {default}".strip()
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
