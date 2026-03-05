from fastapi import FastAPI
from .text2sql import router as text2sql_router
from .health import router as health_router
import logging

logger = logging.getLogger(__name__)


def get_app_info():
    """获取应用信息"""
    return {
        "name": "Melomane AI",
        "version": "1.0.1",
        "description": "可扩展的AI中间件",
    }


def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    info = get_app_info()
    application = FastAPI(
        title=info["name"],
        version=info["version"],
        description=info["description"],
    )

    # 注册路由
    application.include_router(text2sql_router, prefix="/api/v1")
    application.include_router(health_router, prefix="/api/v1")

    logger.info("FastAPI应用创建完成")
    return application


def create_production_app() -> FastAPI:
    """创建生产环境的FastAPI应用实例"""
    return create_app()


app = create_app()
