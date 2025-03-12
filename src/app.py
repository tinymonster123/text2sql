from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from .text_to_sql import Text2SQL
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI实例
app = FastAPI(
    title="Text2SQL API",
    description="将自然语言转换为SQL查询的API服务",
    version="1.0.0",
)

# 初始化Text2SQL服务
text2sql = Text2SQL()


# 定义请求和响应模型
class SQLRequest(BaseModel):
    query: str


class SQLResponse(BaseModel):
    success: bool
    sql: str | None = None
    error: str | None = None
    columns: list = []
    similar_examples: list = []


@app.get("/")
async def root():
    """返回API基本信息"""
    return {
        "name": "Text2SQL API",
        "version": "1.0.0",
        "description": "将自然语言转换为SQL查询的API服务",
    }


@app.get("/generate-sql", response_model=SQLResponse)
async def generate_sql_get(query: str = Query(..., description="自然语言查询")):
    """通过GET请求生成SQL查询"""
    try:
        logger.info(f"收到GET请求: {query}")
        result = text2sql.generate_sql(query)
        return result
    except Exception as e:
        logger.error(f"处理请求时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")


@app.post("/generate-sql", response_model=SQLResponse)
async def generate_sql_post(request: SQLRequest):
    """通过POST请求生成SQL查询"""
    try:
        logger.info(f"收到POST请求: {request.query}")
        result = text2sql.generate_sql(request.query)
        return result
    except Exception as e:
        logger.error(f"处理请求时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")
