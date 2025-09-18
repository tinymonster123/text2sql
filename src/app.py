from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# 请求和响应模型
class SQLRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class SQLResponse(BaseModel):
    success: bool
    sql: Optional[str] = None
    error: Optional[str] = None
    columns: list = []
    similar_examples: list = []
    metadata: dict = {}


class HealthResponse(BaseModel):
    status: str
    middleware_info: dict = {}
    engines: dict = {}


def create_app(middleware=None):
    """创建FastAPI应用实例

    Args:
        middleware: AI中间件实例

    Returns:
        FastAPI: 配置好的应用实例
    """
    app = FastAPI(
        title="Text2SQL AI Middleware",
        description="可扩展的AI中间件 - 自然语言转SQL查询服务",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    @app.get("/", response_model=dict)
    async def root():
        """返回API基本信息"""
        return {
            "name": "Text2SQL AI Middleware",
            "version": "1.0.0",
            "description": "可扩展的AI中间件 - 自然语言转SQL查询服务",
            "engines": list(middleware._engines.keys()) if middleware else [],
            "docs": "/docs",
            "health": "/health",
        }

    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """健康检查端点"""
        try:
            if not middleware:
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "unhealthy",
                        "error": "middleware not initialized",
                    },
                )

            # 获取系统信息
            system_info = middleware.get_system_info()

            # 检查所有引擎健康状态
            engine_health = {}
            all_healthy = True

            for engine_name, engine in middleware._engines.items():
                health = engine.health_check()
                engine_health[engine_name] = health
                if not health.get("healthy", False):
                    all_healthy = False

            status_code = 200 if all_healthy else 503
            return JSONResponse(
                status_code=status_code,
                content={
                    "status": "healthy" if all_healthy else "unhealthy",
                    "middleware_info": system_info,
                    "engines": engine_health,
                },
            )

        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return JSONResponse(
                status_code=503, content={"status": "error", "error": str(e)}
            )

    @app.get("/engines")
    async def list_engines():
        """列出所有可用引擎"""
        if not middleware:
            raise HTTPException(status_code=503, detail="中间件未初始化")

        return {
            "engines": {
                name: engine.get_info() for name, engine in middleware._engines.items()
            },
            "engine_types": {k.value: v for k, v in middleware._engine_types.items()},
        }

    @app.get("/engines/{engine_name}/capabilities")
    async def get_engine_capabilities(engine_name: str):
        """获取指定引擎的能力"""
        if not middleware:
            raise HTTPException(status_code=503, detail="中间件未初始化")

        engine = middleware.get_engine(engine_name)
        if not engine:
            raise HTTPException(status_code=404, detail=f"引擎 {engine_name} 不存在")

        return {
            "engine": engine_name,
            "capabilities": [
                {
                    "name": cap.name,
                    "description": cap.description,
                    "input_types": cap.input_types,
                    "output_types": cap.output_types,
                    "parameters": cap.parameters,
                }
                for cap in engine.get_capabilities()
            ],
        }

    @app.get("/generate-sql", response_model=SQLResponse)
    async def generate_sql_get(
        query: str = Query(..., description="自然语言查询"),
        user_id: Optional[str] = Query(None, description="用户ID"),
        session_id: Optional[str] = Query(None, description="会话ID"),
    ):
        """通过GET请求生成SQL查询"""
        request = SQLRequest(query=query, user_id=user_id, session_id=session_id)
        return await process_sql_request(request, middleware)

    @app.post("/generate-sql", response_model=SQLResponse)
    async def generate_sql_post(request: SQLRequest):
        """通过POST请求生成SQL查询"""
        return await process_sql_request(request, middleware)

    @app.post("/engines/{engine_name}/process")
    async def process_with_engine(engine_name: str, data: dict):
        """使用指定引擎处理请求"""
        if not middleware:
            raise HTTPException(status_code=503, detail="中间件未初始化")

        try:
            from core.middleware import ProcessingContext

            context = ProcessingContext(
                user_id=data.get("user_id"),
                session_id=data.get("session_id"),
                metadata=data.get("metadata", {}),
                headers=data.get("headers", {}),
            )

            result = await middleware.process_request(
                engine_name=engine_name,
                input_data=data.get("input_data", {}),
                context=context,
            )

            return result

        except Exception as e:
            logger.error(f"引擎处理失败: {e}")
            raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

    return app


async def process_sql_request(request: SQLRequest, middleware) -> SQLResponse:
    """处理SQL请求的通用函数"""
    if not middleware:
        raise HTTPException(status_code=503, detail="中间件未初始化")

    try:
        logger.info(f"收到SQL生成请求: {request.query}")

        from core.middleware import ProcessingContext

        context = ProcessingContext(
            user_id=request.user_id, session_id=request.session_id
        )

        # 使用中间件处理请求
        result = await middleware.process_request(
            engine_name="text2sql_engine",
            input_data={"query": request.query},
            context=context,
        )

        if result["success"]:
            data = result["data"]
            return SQLResponse(
                success=data["success"],
                sql=data.get("sql"),
                error=data.get("error"),
                columns=data.get("columns", []),
                similar_examples=data.get("similar_examples", []),
                metadata=data.get("metadata", {}),
            )
        else:
            return SQLResponse(
                success=False,
                error=result.get("error", "未知错误"),
                sql="",
                columns=[],
                similar_examples=[],
            )

    except Exception as e:
        logger.error(f"处理SQL请求失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")


app = create_app()
