from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import logging
from .text2sql import router as text2sql_router
from .health import router as health_router
from ...schema.api_responses import ApiInfo

logger = logging.getLogger(__name__)


def create_app(middleware=None, **kwargs) -> FastAPI:
    app = FastAPI(
        title="Melomane AI Middleware",
        description="Melomane AI 中间件 - 智能自然语言转SQL工具和音乐推荐系统",
        version="1.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={"name": "Melomane AI Team", "email": "lfhxgs123@gmail.com"},
        license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
        **kwargs,
    )

    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # API版本前缀
    API_PREFIX = "/api/v1"

    # 注册路由
    app.include_router(text2sql_router, prefix=API_PREFIX)
    app.include_router(health_router, prefix=API_PREFIX)

    # 根路径端点
    @app.get(
        "/",
        response_model=Dict[str, Any],
        summary="API信息",
        description="获取API基本信息和可用端点列表",
        tags=["基础信息"],
    )
    async def root() -> Dict[str, Any]:
        return {
            "name": "Melomane AI Middleware",
            "version": "1.1.0",
            "description": "智能自然语言转SQL工具和音乐推荐系统",
            "api_version": "v1",
            "status": "running",
            "endpoints": {
                "docs": "/docs",
                "redoc": "/redoc",
                "openapi": "/openapi.json",
                "health": f"{API_PREFIX}/system/health",
                "health_detailed": f"{API_PREFIX}/system/health/detailed",
                "text2sql": f"{API_PREFIX}/app/text2sql/generate_sql",
                "text2sql_get": f"{API_PREFIX}/app/text2sql/generate_sql",
                "text2sql_capabilities": f"{API_PREFIX}/app/text2sql/capabilities",
            },
            "features": ["自然语言转SQL", "系统健康监控"],
            "supported_databases": ["PostgreSQL"],
            "middleware_initialized": middleware is not None,
        }

    # 添加启动和关闭事件处理
    @app.on_event("startup")
    async def startup_event():
        """应用启动事件处理"""
        logger.info("Melomane AI Middleware 启动中...")
        if middleware:
            logger.info("中间件已注入，系统功能完整可用")
        else:
            logger.warning("中间件未注入，部分功能将返回模拟数据")
        logger.info("应用启动完成")

    @app.on_event("shutdown")
    async def shutdown_event():
        """应用关闭事件处理"""
        logger.info("Melomane AI Middleware 正在关闭...")
        if middleware and hasattr(middleware, "cleanup"):
            try:
                await middleware.cleanup()
                logger.info("中间件清理完成")
            except Exception as e:
                logger.error(f"中间件清理失败: {e}")
        logger.info("应用已关闭")

    # 添加全局异常处理器
    @app.exception_handler(500)
    async def internal_server_error_handler(request, exc):
        """全局500错误处理器"""
        logger.error(f"内部服务器错误: {exc}", exc_info=True)
        return {
            "success": False,
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "内部服务器错误，请稍后重试",
            "timestamp": "2025-09-22T16:00:00Z",
        }

    if middleware:
        app.state.middleware = middleware

        def get_middleware_instance():
            return app.state.middleware

    return app


app = create_app()


def get_app_info() -> ApiInfo:
    return ApiInfo(
        name="Melomane AI Middleware",
        version="1.1.0",
        description="智能自然语言转SQL工具和音乐推荐系统",
        api_version="v1",
        endpoints={
            "health": "/api/v1/system/health",
            "text2sql": "/api/v1/app/text2sql/generate_sql",
            "recommendation": "/api/v1/app/recommendation/songs",
        },
    )


def create_production_app(middleware=None) -> FastAPI:
    return create_app(
        middleware=middleware,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
