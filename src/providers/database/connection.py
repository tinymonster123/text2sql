import pymysql
from pathlib import Path
from sshtunnel import SSHTunnelForwarder
from ..config import Config

class MySQLSSHConnection:
    def __init__(self):
        self.tunnel = None
        self.connection = None
        self.cursor = None

    def connect(self):
        try:
            self.tunnel = SSHTunnelForwarder(
                ssh_address_or_host=(Config.SSH_HOST, 22),
                ssh_username=Config.SSH_USER,
                ssh_pkey=Config.SSH_KEY_PATH,
                remote_bind_address=(Config.DB_HOST, 3306),
            )
            self.tunnel.start()

            self.connection = pymysql.connect(
                user=Config.DB_USER,
                passwd=Config.DB_PASSWORD,
                host='127.0.0.1',  # 使用本地地址
                db=Config.DB_NAME,
                port=self.tunnel.local_bind_port,
            )
            self.cursor = self.connection.cursor()
            return self.cursor
        except Exception as e:
            self.close()
            raise Exception(f"数据库连接失败: {str(e)}")

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        if self.tunnel:
            self.tunnel.close()

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

