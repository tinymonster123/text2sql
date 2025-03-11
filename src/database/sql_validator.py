import sqlparse
import re
from .connection import MySQLSSHConnection


class SQLValidator:
    def __init__(self):
        self.connection = MySQLSSHConnection()

    def validate_syntax(self, sql_query):
        """
        ��֤SQL�﷨�Ƿ���ȷ

        Args:
            sql_query: Ҫ��֤��SQL��ѯ

        Returns:
            (bool, str): Ԫ�飬��һ��Ԫ�ر�ʾ�Ƿ���Ч���ڶ���Ԫ���Ǵ�����Ϣ������У�
        """
        try:
            # ʹ��sqlparse���л�����֤
            parsed = sqlparse.parse(sql_query)
            if not parsed or not parsed[0].tokens:
                return False, "�յĻ���Ч��SQL��ѯ"

            # ����Ƿ��ǰ�ȫ�Ĳ�ѯ��䣨ֻ����
            if not self._is_safe_query(sql_query):
                return False, "����ȫ��SQL������ֻ����SELECT��ѯ"

            return True, ""
        except Exception as e:
            return False, f"SQL��֤����: {str(e)}"

    def _is_safe_query(self, sql_query):
        """
        ����Ƿ��ǰ�ȫ�Ĳ�ѯ��ֻ��������
        """
        normalized_query = sql_query.strip().upper()
        # ֻ����SELECT���
        return normalized_query.startswith("SELECT")

    def test_execute(self, sql_query):
        """
        ����ִ��SQL��ѯ���������ؽ��

        Args:
            sql_query: SQL��ѯ�ַ���

        Returns:
            (bool, str, list): Ԫ�飬��һ��Ԫ�ر�ʾ�Ƿ�ɹ����ڶ���Ԫ���Ǵ�����Ϣ��������Ԫ��������
        """
        try:
            # ������֤�﷨
            valid, error_msg = self.validate_syntax(sql_query)
            if not valid:
                return False, error_msg, []

            cursor = self.connection.connect()

            # ���ó�ʱ�Է�ֹ��ʱ�����еĲ�ѯ
            cursor.execute("SET SESSION MAX_EXECUTION_TIME=5000")  # 5�볬ʱ
            cursor.execute(sql_query)

            # ��ȡ����
            column_names = (
                [desc[0] for desc in cursor.description] if cursor.description else []
            )

            # ����ȡ���ݣ�ֻ��֤��ѯ�Ƿ����ִ��
            return True, "��ѯ��Ч", column_names

        except Exception as e:
            return False, f"SQLִ�д���: {str(e)}", []

        finally:
            self.connection.close()
