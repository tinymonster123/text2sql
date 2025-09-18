#!/usr/bin/env python3
"""
Text2SQL AI中间件启动脚本

统一的应用启动入口，支持多种运行模式
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.middleware import AIMiddleware, LoggingHook, MetricsHook, EngineType
from engines.text2sql_engine import Text2SQLEngine
from app import create_app
import uvicorn

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log') if os.path.exists('/app') else logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def load_config():
    """加载配置"""
    return {
        "chroma_host": os.getenv("CHROMA_HOST", "localhost"),
        "chroma_port": int(os.getenv("CHROMA_PORT", "8888")),
        "db_host": os.getenv("DB_HOST", "localhost"),
        "db_port": int(os.getenv("DB_PORT", "5432")),
        "server_host": os.getenv("HOST", "0.0.0.0"),
        "server_port": int(os.getenv("PORT", "8000")),
        "log_level": os.getenv("AI_MIDDLEWARE_LOG_LEVEL", "INFO"),
        "mode": os.getenv("AI_MIDDLEWARE_MODE", "development")
    }


async def initialize_middleware():
    """初始化AI中间件"""
    logger.info("🚀 启动Text2SQL AI中间件...")

    # 创建中间件实例
    middleware = AIMiddleware()

    # 添加钩子
    middleware.add_middleware_hook(LoggingHook())
    middleware.add_middleware_hook(MetricsHook())

    # 加载配置
    config = load_config()

    # 创建并注册Text2SQL引擎
    text2sql_engine = Text2SQLEngine()
    if text2sql_engine.initialize(config):
        middleware.register_engine(text2sql_engine, EngineType.TEXT_TO_SQL)
        logger.info("✅ Text2SQL引擎注册成功")
    else:
        logger.error("❌ Text2SQL引擎初始化失败")
        return None

    logger.info("✅ AI中间件初始化完成")
    logger.info(f"📊 系统信息: {middleware.get_system_info()}")

    return middleware


def main():
    """主函数"""
    try:
        # 加载配置
        config = load_config()

        # 设置日志级别
        logging.getLogger().setLevel(getattr(logging, config["log_level"]))

        # 初始化中间件
        middleware = asyncio.run(initialize_middleware())
        if not middleware:
            logger.error("中间件初始化失败，退出...")
            sys.exit(1)

        # 创建FastAPI应用
        app = create_app(middleware)

        logger.info(f"🌐 启动服务器: {config['server_host']}:{config['server_port']}")
        logger.info(f"📋 运行模式: {config['mode']}")
        logger.info(f"🏥 健康检查: http://{config['server_host']}:{config['server_port']}/health")
        logger.info(f"📚 API文档: http://{config['server_host']}:{config['server_port']}/docs")

        # 启动服务器
        uvicorn.run(
            app,
            host=config["server_host"],
            port=config["server_port"],
            log_level=config["log_level"].lower(),
            access_log=True,
            reload=config["mode"] == "development"
        )

    except KeyboardInterrupt:
        logger.info("🛑 收到停止信号，正在关闭...")
    except Exception as e:
        logger.error(f"❌ 启动失败: {e}")
        sys.exit(1)
    finally:
        logger.info("👋 Text2SQL AI中间件已关闭")


if __name__ == "__main__":
    main()