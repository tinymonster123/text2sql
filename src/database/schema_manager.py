from .connection import MySQLSSHConnection
import json
import os


class SchemaManager:
    def __init__(self):
        self.connection = MySQLSSHConnection()
        self.schema_cache_path = "data/schema_cache.json"

    def extract_schema(self, force_refresh=False):
        """
        ��ȡ���ݿ�Schema��Ϣ

        Args:
            force_refresh: �Ƿ�ǿ��ˢ�»���

        Returns:
            ���ַ�����ʽ�������ݿ�Schema��Ϣ
        """
        # ��黺��
        if not force_refresh and os.path.exists(self.schema_cache_path):
            with open(self.schema_cache_path, "r", encoding="utf-8") as f:
                return json.load(f)

        schema_info = {}
        cursor = None

        try:
            cursor = self.connection.connect()

            # ��ȡ���б�
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]

            # ��ȡÿ�������ϸ��Ϣ
            for table in tables:
                # ��ȡ��ṹ
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

                    # ��¼����
                    if key_type == "PRI":
                        table_info["primary_keys"].append(column_name)

                # ��ȡ�����Ϣ
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
                    # ĳЩ����¿����޷���ȡ�����Ϣ
                    pass

                schema_info[table] = table_info

            # ������
            os.makedirs(os.path.dirname(self.schema_cache_path), exist_ok=True)
            with open(self.schema_cache_path, "w", encoding="utf-8") as f:
                json.dump(schema_info, f, ensure_ascii=False, indent=2)

            return schema_info

        finally:
            self.connection.close()

    def format_schema_for_prompt(self, schema_info=None):
        """
        ��Schema��Ϣ��ʽ��Ϊ�ʺ���ʾ���ı���ʽ

        Returns:
            ��ʽ�����Schema�ַ���
        """
        if schema_info is None:
            schema_info = self.extract_schema()

        formatted_text = []
        formatted_text.append("���ݿ�ܹ���Ϣ:")

        for table_name, table_info in schema_info.items():
            formatted_text.append(f"\n����: {table_name}")

            # �������Ϣ
            formatted_text.append("��:")
            for column in table_info["columns"]:
                nullable = "NULL" if column["nullable"] else "NOT NULL"
                default = f"DEFAULT {column['default']}" if column["default"] else ""
                formatted_text.append(
                    f"  - {column['name']} {column['type']} {nullable} {default}"
                )

            # ���������Ϣ
            if table_info["primary_keys"]:
                formatted_text.append("����:")
                for pk in table_info["primary_keys"]:
                    formatted_text.append(f"  - {pk}")

            # ��������Ϣ
            if table_info["foreign_keys"]:
                formatted_text.append("���:")
                for fk in table_info["foreign_keys"]:
                    formatted_text.append(
                        f"  - {fk['column']} -> {fk['referenced_table']}.{fk['referenced_column']}"
                    )

        return "\n".join(formatted_text)
