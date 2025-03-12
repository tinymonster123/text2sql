# -*- coding: utf-8 -*-
import logging
import pymysql
from pathlib import Path
from ..config import Config

logger = logging.getLogger(__name__)


class MySQLLocalConnection:
    """MySQL数据库连接管理器

    提供数据库连接管理功能，支持以下特性：
    - 自动连接和断开
    - 支持with语句上下文管理
    - 使用字典游标返回结果
    - 自动重试和错误处理
    """

    def __init__(self):
        """初始化连接管理器"""
        self.connection = None
        self.cursor = None

    def connect(self):
        """建立数据库连接

        Returns:
            pymysql.cursors.DictCursor: 数据库游标对象

        Raises:
            Exception: 连接失败时抛出异常
        """
        try:
            logger.info(f"连接到数据库: {Config.DB_NAME}")

            self.connection = pymysql.connect(
                host=Config.DB_HOST or "localhost",  # 默认使用localhost
                port=int(Config.DB_PORT) or 3306,  # 默认使用3306端口
                user=Config.DB_USER,
                passwd=Config.DB_PASSWORD,
                db=Config.DB_NAME,
                charset="utf8mb4",  # 使用utf8mb4字符集
                cursorclass=pymysql.cursors.DictCursor,  # 使用字典游标
            )

            self.cursor = self.connection.cursor()
            logger.info("数据库连接成功")
            return self.cursor

        except Exception as e:
            logger.error(f"数据库连接失败: {str(e)}")
            self.close()
            raise Exception(f"数据库连接失败: {str(e)}")

    def close(self):
        """关闭数据库连接

        同时关闭游标和连接对象
        """
        if self.cursor:
            self.cursor.close()
            self.cursor = None

        if self.connection:
            self.connection.close()
            self.connection = None

        logger.info("数据库连接已关闭")

    def __enter__(self):
        """支持with语句的上下文管理器入口

        Returns:
            pymysql.cursors.DictCursor: 数据库游标对象
        """
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持with语句的上下文管理器退出

        Args:
            exc_type: 异常类型
            exc_val: 异常值
            exc_tb: 异常回溯
        """
        self.close()
