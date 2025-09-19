# -*- coding: utf-8 -*-
from ..database import PostgreSQLProvider
from ...config import Config
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
        self.db_provider = PostgreSQLProvider()
        self.schema_cache_path = "data/schema_cache.json"

        # 初始化数据库连接 (使用音乐数据库)
        self.db_provider.initialize(Config.MUSIC_DATABASE_URL)

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

        try:
            logger.info("开始提取数据库Schema信息")

            # 使用PostgreSQL provider获取schema信息
            schema_info = self.db_provider.get_schema()

            logger.info(f"发现 {len(schema_info)} 个表")

            # 缓存结果
            self._save_schema_cache(schema_info)
            logger.info("Schema信息提取完成")

            return schema_info

        except Exception as e:
            logger.error(f"提取数据库结构失败: {str(e)}")
            raise

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

        # 使用PostgreSQL provider的format_schema方法
        return self.db_provider.format_schema(schema_info)
