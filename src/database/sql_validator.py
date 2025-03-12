# -*- coding: utf-8 -*-
import logging
import os
import re
import shutil
import sqlparse
from .connection import MySQLSSHConnection
from typing import Tuple, List, Optional

logger = logging.getLogger(__name__)


class SQLValidator:
    """SQL验证器

    用于验证SQL查询的语法正确性和安全性，并提供测试执行功能。
    主要功能包括：
    - SQL语法验证
    - 查询安全性检查
    - 查询执行测试
    - 磁盘空间检查
    - 结果集大小限制
    """

    def __init__(self):
        """初始化SQL验证器"""
        self.connection = MySQLSSHConnection()

    def validate_syntax(self, sql_query: str) -> Tuple[bool, str]:
        """验证SQL语法是否正确

        Args:
            sql_query: 要验证的SQL查询语句

        Returns:
            Tuple[bool, str]:
                - bool: 表示是否有效
                - str: 错误信息（如果有）
        """
        try:
            # 使用sqlparse进行基本验证
            parsed = sqlparse.parse(sql_query)
            if not parsed or not parsed[0].tokens:
                return False, "空的或无效的SQL查询"

            # 检查是否是安全的查询语句（只读）
            if not self._is_safe_query(sql_query):
                return False, "不安全的SQL操作：只允许SELECT查询"

            return True, ""

        except Exception as e:
            logger.error(f"SQL语法验证失败: {str(e)}")
            return False, f"SQL验证错误: {str(e)}"

    def test_execute(self, sql_query: str) -> Tuple[bool, str, List[str]]:
        """测试执行SQL查询

        Args:
            sql_query: 要执行的SQL查询语句

        Returns:
            Tuple[bool, str, List[str]]:
                - bool: 表示是否执行成功
                - str: 错误信息或成功消息
                - List[str]: 查询结果的列名列表
        """
        try:
            # 首先验证语法
            valid, error_msg = self.validate_syntax(sql_query)
            if not valid:
                return False, error_msg, []

            # 获取数据库连接和游标
            cursor = self.connection.connect()

            # 检查磁盘空间
            self._check_disk_space()

            # 设置查询超时和限制
            cursor.execute("SET SESSION MAX_EXECUTION_TIME=5000")  # 5秒超时

            # 限制结果集大小
            limited_query = self._limit_query_results(sql_query)
            logger.info(f"执行限制后的SQL: {limited_query}")

            # 执行查询
            cursor.execute(limited_query)

            # 获取并处理结果集信息
            return self._process_query_results(cursor)

        except Exception as e:
            return self._handle_execution_error(e)

        finally:
            self.connection.close()

    def _is_safe_query(self, sql_query: str) -> bool:
        """检查是否是安全的查询（只读操作）

        Args:
            sql_query: SQL查询语句

        Returns:
            bool: 是否是安全的查询
        """
        normalized_query = sql_query.strip().upper()
        return normalized_query.startswith("SELECT")

    def _check_disk_space(self) -> None:
        """检查服务器磁盘空间"""
        try:
            tmp_stats = os.statvfs("/tmp")
            free_space_mb = (tmp_stats.f_bavail * tmp_stats.f_frsize) / (1024 * 1024)

            if free_space_mb < 100:  # 小于100MB时警告
                logger.warning(f"服务器 /tmp 目录剩余空间不足: {free_space_mb:.2f}MB")

        except Exception as e:
            logger.warning(f"检查磁盘空间失败: {str(e)}")

    def _limit_query_results(self, sql_query: str) -> str:
        """限制查询结果集大小

        处理原始SQL查询，添加LIMIT子句以限制返回的结果数量，
        同时处理可能存在的结尾分号，保证语法正确。

        Args:
            sql_query: 原始SQL查询

        Returns:
            str: 添加了LIMIT子句的SQL查询
        """
        # 处理输入
        if not sql_query or not isinstance(sql_query, str):
            logger.warning("收到无效的SQL查询")
            return sql_query

        # 去除首尾空白字符
        sql = sql_query.strip()

        # 检查是否以分号结尾
        ends_with_semicolon = sql.endswith(";")
        if ends_with_semicolon:
            sql = sql[:-1]

        # 如果已经有LIMIT子句，不做修改
        if re.search(r"\bLIMIT\s+\d+", sql, re.IGNORECASE):
            return sql_query  # 返回原始查询

        # 添加LIMIT子句并处理分号
        limited_sql = f"{sql} LIMIT 10"
        if ends_with_semicolon:
            limited_sql += ";"

        logger.info(f"添加限制后的SQL: {limited_sql}")
        return limited_sql

    def _process_query_results(self, cursor) -> Tuple[bool, str, List[str]]:
        """处理查询结果

        Args:
            cursor: 数据库游标

        Returns:
            Tuple[bool, str, List[str]]: 执行结果、消息和列名列表
        """
        if hasattr(cursor, "description") and cursor.description:
            if isinstance(cursor.description[0], tuple):
                column_names = [desc[0] for desc in cursor.description]
            else:
                # 对于DictCursor
                column_names = [desc.name for desc in cursor.description]

            logger.info(f"SQL验证成功, 列名: {column_names}")
            return True, "查询有效", column_names
        else:
            logger.info("SQL验证成功，但无结果集")
            return True, "查询有效 (无结果集)", []

    def _handle_execution_error(self, error: Exception) -> Tuple[bool, str, List[str]]:
        """处理执行过程中的错误

        Args:
            error: 捕获的异常

        Returns:
            Tuple[bool, str, List[str]]: 错误处理结果
        """
        error_str = str(error)
        logger.error(f"SQL执行错误: {error_str}")

        # 特殊处理磁盘空间不足错误
        if "No space left on device" in error_str:
            logger.warning("服务器磁盘空间不足，但SQL语法检查通过")
            return True, "SQL语法正确，但服务器磁盘空间不足", []

        return False, f"SQL执行错误: {error_str}", []
