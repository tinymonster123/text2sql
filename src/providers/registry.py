from typing import Dict, Any, Type, Optional
import logging

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """提供商注册器

    管理所有AI功能提供商的注册和获取
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProviderRegistry, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._llm_providers: Dict[str, Type] = {}
            self._vectordb_providers: Dict[str, Type] = {}
            self._database_providers: Dict[str, Type] = {}
            self._register_default_providers()
            self._initialized = True

    def _register_default_providers(self):
        """注册默认提供商"""
        try:
            # 注册LLM提供商
            from .llm.openai_provider import OpenAIProvider
            self.register_llm_provider("openai", OpenAIProvider)
            self.register_llm_provider("deepseek", OpenAIProvider)  # DeepSeek使用OpenAI兼容接口
            self.register_llm_provider("qwen", OpenAIProvider)     # Qwen使用OpenAI兼容接口

            # 注册向量数据库提供商
            from .vectordb.chroma_provider import ChromaProvider
            self.register_vectordb_provider("chroma", ChromaProvider)

            # 注册数据库提供商
            from .database.postgresql_provider import PostgreSQLProvider
            self.register_database_provider("postgresql", PostgreSQLProvider)

            logger.info("默认提供商注册完成")

        except Exception as e:
            logger.error(f"注册默认提供商失败: {e}")

    def register_llm_provider(self, name: str, provider_class: Type):
        """注册LLM提供商"""
        self._llm_providers[name] = provider_class
        logger.debug(f"LLM提供商已注册: {name}")

    def register_vectordb_provider(self, name: str, provider_class: Type):
        """注册向量数据库提供商"""
        self._vectordb_providers[name] = provider_class
        logger.debug(f"向量数据库提供商已注册: {name}")

    def register_database_provider(self, name: str, provider_class: Type):
        """注册数据库提供商"""
        self._database_providers[name] = provider_class
        logger.debug(f"数据库提供商已注册: {name}")

    def get_llm_provider(self, name: str):
        """获取LLM提供商实例"""
        provider_class = self._llm_providers.get(name)
        if provider_class:
            return provider_class()
        else:
            logger.error(f"LLM提供商不存在: {name}")
            return None

    def get_vectordb_provider(self, name: str):
        """获取向量数据库提供商实例"""
        provider_class = self._vectordb_providers.get(name)
        if provider_class:
            return provider_class()
        else:
            logger.error(f"向量数据库提供商不存在: {name}")
            return None

    def get_database_provider(self, name: str):
        """获取数据库提供商实例"""
        provider_class = self._database_providers.get(name)
        if provider_class:
            return provider_class()
        else:
            logger.error(f"数据库提供商不存在: {name}")
            return None

    def list_providers(self) -> Dict[str, Any]:
        """列出所有注册的提供商"""
        return {
            "llm": list(self._llm_providers.keys()),
            "vectordb": list(self._vectordb_providers.keys()),
            "database": list(self._database_providers.keys())
        }

    def get_provider_info(self) -> Dict[str, Any]:
        """获取所有提供商的详细信息"""
        info = {"providers": self.list_providers()}

        # 可以添加更多详细信息
        info["total_providers"] = (
            len(self._llm_providers) +
            len(self._vectordb_providers) +
            len(self._database_providers)
        )

        return info