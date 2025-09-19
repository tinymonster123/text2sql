from .ai_engine import EngineCapability
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type
from dataclasses import dataclass, field
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class EngineType(Enum):
    """AI引擎类型枚举"""

    TEXT_TO_SQL = "text_to_sql"
    TEXT_TO_CODE = "text_to_code"
    DOCUMENT_QA = "document_qa"
    CHAT = "chat"
    EMBEDDING = "embedding"
    CUSTOM = "custom"


@dataclass
class ProcessingContext:
    """处理上下文"""

    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)


class AIMiddleware:
    """AI中间件核心类

    管理多个AI引擎，提供统一的接口和路由功能
    支持插件式架构，可动态注册和卸载引擎
    """

    def __init__(self):
        self._engines: Dict[str, "AIEngine"] = {}
        self._engine_types: Dict[EngineType, List[str]] = {}
        self._middleware_hooks: List["MiddlewareHook"] = []
        self.is_initialized = False

    def register_engine(
        self, engine: "AIEngine", engine_type: EngineType = EngineType.CUSTOM
    ) -> bool:
        """注册AI引擎

        Args:
            engine: AI引擎实例
            engine_type: 引擎类型

        Returns:
            bool: 是否注册成功
        """
        try:
            if engine.name in self._engines:
                logger.warning(f"引擎 {engine.name} 已存在，将被覆盖")

            self._engines[engine.name] = engine

            if engine_type not in self._engine_types:
                self._engine_types[engine_type] = []
            self._engine_types[engine_type].append(engine.name)

            logger.info(f"成功注册引擎: {engine.name} (类型: {engine_type.value})")
            return True

        except Exception as e:
            logger.error(f"注册引擎失败: {e}")
            return False

    def unregister_engine(self, engine_name: str) -> bool:
        """注销AI引擎"""
        try:
            if engine_name not in self._engines:
                logger.warning(f"引擎 {engine_name} 不存在")
                return False

            del self._engines[engine_name]

            # 从类型映射中移除
            for engine_type, names in self._engine_types.items():
                if engine_name in names:
                    names.remove(engine_name)
                    break

            logger.info(f"成功注销引擎: {engine_name}")
            return True

        except Exception as e:
            logger.error(f"注销引擎失败: {e}")
            return False

    def get_engine(self, engine_name: str) -> Optional["AIEngine"]:
        """获取指定引擎"""
        return self._engines.get(engine_name)

    def get_engines_by_type(self, engine_type: EngineType) -> List["AIEngine"]:
        """根据类型获取引擎列表"""
        engine_names = self._engine_types.get(engine_type, [])
        return [self._engines[name] for name in engine_names if name in self._engines]

    def add_middleware_hook(self, hook: "MiddlewareHook"):
        """添加中间件钩子"""
        self._middleware_hooks.append(hook)

    async def process_request(
        self,
        engine_name: str,
        input_data: Dict[str, Any],
        context: Optional[ProcessingContext] = None,
    ) -> Dict[str, Any]:
        """处理请求的统一入口

        Args:
            engine_name: 引擎名称
            input_data: 输入数据
            context: 处理上下文

        Returns:
            Dict[str, Any]: 处理结果
        """
        if context is None:
            context = ProcessingContext()

        try:
            # 前置钩子
            for hook in self._middleware_hooks:
                input_data = await hook.before_process(engine_name, input_data, context)

            # 获取引擎并处理
            engine = self.get_engine(engine_name)
            if not engine:
                raise ValueError(f"引擎 {engine_name} 不存在")

            if not engine.is_initialized:
                raise RuntimeError(f"引擎 {engine_name} 未初始化")

            result = engine.process(input_data)

            # 后置钩子
            for hook in self._middleware_hooks:
                result = await hook.after_process(engine_name, result, context)

            return {
                "success": True,
                "data": result,
                "engine": engine_name,
                "context": {
                    "user_id": context.user_id,
                    "session_id": context.session_id,
                },
            }

        except Exception as e:
            logger.error(f"处理请求失败: {e}")
            return {"success": False, "error": str(e), "engine": engine_name}

    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            "middleware_version": "1.0.0",
            "total_engines": len(self._engines),
            "engine_types": {k.value: len(v) for k, v in self._engine_types.items()},
            "engines": {
                name: engine.get_info() for name, engine in self._engines.items()
            },
            "hooks_count": len(self._middleware_hooks),
        }


class MiddlewareHook(ABC):
    """中间件钩子抽象基类"""

    @abstractmethod
    async def before_process(
        self, engine_name: str, input_data: Dict[str, Any], context: ProcessingContext
    ) -> Dict[str, Any]:
        """处理前钩子"""
        pass

    @abstractmethod
    async def after_process(
        self, engine_name: str, result: Dict[str, Any], context: ProcessingContext
    ) -> Dict[str, Any]:
        """处理后钩子"""
        pass


# 内置钩子实现
class LoggingHook(MiddlewareHook):
    """日志记录钩子"""

    async def before_process(
        self, engine_name: str, input_data: Dict[str, Any], context: ProcessingContext
    ) -> Dict[str, Any]:
        logger.info(f"开始处理请求 - 引擎: {engine_name}, 用户: {context.user_id}")
        return input_data

    async def after_process(
        self, engine_name: str, result: Dict[str, Any], context: ProcessingContext
    ) -> Dict[str, Any]:
        success = result.get("success", False)
        logger.info(f"请求处理完成 - 引擎: {engine_name}, 成功: {success}")
        return result


class MetricsHook(MiddlewareHook):
    """指标收集钩子"""

    def __init__(self):
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0

    async def before_process(
        self, engine_name: str, input_data: Dict[str, Any], context: ProcessingContext
    ) -> Dict[str, Any]:
        self.request_count += 1
        return input_data

    async def after_process(
        self, engine_name: str, result: Dict[str, Any], context: ProcessingContext
    ) -> Dict[str, Any]:
        if result.get("success", False):
            self.success_count += 1
        else:
            self.error_count += 1
        return result

    def get_metrics(self) -> Dict[str, int]:
        return {
            "total_requests": self.request_count,
            "successful_requests": self.success_count,
            "failed_requests": self.error_count,
            "success_rate": self.success_count / max(self.request_count, 1) * 100,
        }
