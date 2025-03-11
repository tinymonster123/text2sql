import sqlparse
import re
from .connection import MySQLSSHConnection


class SQLValidator:
    def __init__(self):
        self.connection = MySQLSSHConnection()

    def validate_syntax(self, sql_query):
        """
        验证SQL语法是否正确

        Args:
            sql_query: 要验证的SQL查询

        Returns:
            (bool, str): 元组，第一个元素表示是否有效，第二个元素是错误信息（如果有）
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
            return False, f"SQL验证错误: {str(e)}"

    def _is_safe_query(self, sql_query):
        """
        检查是否是安全的查询（只读操作）
        """
        normalized_query = sql_query.strip().upper()
        # 只允许SELECT语句
        return normalized_query.startswith("SELECT")

    def test_execute(self, sql_query):
        """
        测试执行SQL查询，但不返回结果

        Args:
            sql_query: SQL查询字符串

        Returns:
            (bool, str, list): 元组，第一个元素表示是否成功，第二个元素是错误信息，第三个元素是列名
        """
        try:
            # 首先验证语法
            valid, error_msg = self.validate_syntax(sql_query)
            if not valid:
                return False, error_msg, []

            cursor = self.connection.connect()

            # 设置超时以防止长时间运行的查询
            cursor.execute("SET SESSION MAX_EXECUTION_TIME=5000")  # 5秒超时
            cursor.execute(sql_query)

            # 获取列名
            column_names = (
                [desc[0] for desc in cursor.description] if cursor.description else []
            )

            # 不获取数据，只验证查询是否可以执行
            return True, "查询有效", column_names

        except Exception as e:
            return False, f"SQL执行错误: {str(e)}", []

        finally:
            self.connection.close()
