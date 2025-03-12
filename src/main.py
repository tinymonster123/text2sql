import uvicorn
import logging
from .app import app

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def start_server(host="0.0.0.0", port=8000, reload=True):
    """启动FastAPI服务器"""
    logger.info(f"启动服务器，监听地址: {host}:{port}")
    uvicorn.run("src.app:app", host=host, port=port, reload=reload, log_level="info")


if __name__ == "__main__":
    start_server()
