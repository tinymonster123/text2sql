from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Annotated
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseResponse(BaseModel):
    success: bool
    timestamp: datetime = Field(default_factory=datetime.now)
    message: Optional[str] = None


class ErrorResponse(BaseResponse):
    success: bool = False
    error_code: str
    error_details: Optional[Dict[str, Any]] = None


class Text2SqlRequest(BaseModel):
    query: Annotated[str, Field(min_length=1)]
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)


class Text2SqlResult(BaseModel):
    sql: str
    confidence: Optional[float] = None
    columns: List[str] = Field(default_factory=list)
    similar_examples: List[Dict[str, Any]] = Field(default_factory=list)
    schema_info: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Text2SqlResponse(BaseResponse):
    data: Text2SqlResult


class HealthCheckResponse(BaseResponse):
    data: Dict[str, Any]


def create_app(middleware=None) -> FastAPI:
    app = FastAPI(
        title="Melomane AI Middleware",
        description="Melomane AI 中间件 - 智能自然语言转SQL工具",
        version="1.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    API_PREFIX = "/api/v1"

    @app.get("/", response_model=Dict[str, Any])
    async def root():
        return {
            "name": "Melomane AI Middleware",
            "version": "1.1.0",
            "description": "智能自然语言转SQL工具",
            "api_version": "v1",
            "endpoints": {
                "docs": "/docs",
                "redoc": "/redoc",
                "health": f"{API_PREFIX}/system/health",
                "text2sql": f"{API_PREFIX}/app/text2sql",
                "guide": f"{API_PREFIX}/guide",
            },
        }

    @app.get(f"{API_PREFIX}/system/health", response_model=HealthCheckResponse)
    async def get_system_health():
        try:
            if not middleware:
                return JSONResponse(
                    status_code=503,
                    content=ErrorResponse(
                        error_code="MIDDLEWARE_NOT_INITIALIZED",
                        message="中间件未初始化",
                    ).dict(),
                )

            system_info = middleware.get_system_info()

            engine_health = {}
            all_healthy = True

            for engine_name, engine in middleware._engines.items():
                health = engine.health_check()
                engine_health[engine_name] = health
                if not health.get("healthy", False):
                    all_healthy = False

            health_data = {
                "status": "healthy" if all_healthy else "degraded",
                "middleware": system_info,
                "engines": engine_health,
                "total_engines": len(middleware._engines),
                "healthy_engines": sum(
                    1 for h in engine_health.values() if h.get("healthy", False)
                ),
            }

            status_code = 200 if all_healthy else 503
            return JSONResponse(
                status_code=status_code,
                content=HealthCheckResponse(
                    success=all_healthy,
                    data=health_data,
                    message="健康检查完成",
                ).dict(),
            )

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return JSONResponse(
                status_code=503,
                content=ErrorResponse(
                    error_code="HEALTH_CHECK_FAILED",
                    message=f"健康检查失败: {str(e)}",
                ).dict(),
            )

    @app.post(
        f"{API_PREFIX}/app/text2sql/generate_sql", response_model=Text2SqlResponse
    )
    async def generate_sql(request: Text2SqlRequest):
        if not middleware:
            raise HTTPException(status_code=503, detail="中间件未初始化")

        try:
            logger.info(f"Text2SQL请求: {request.query}")

            from app.core.middleware import ProcessingContext

            context = ProcessingContext(
                user_id=request.user_id,
                session_id=request.session_id,
                metadata=request.options or {},
            )

            result = await middleware.process_request(
                engine_name="text2sql_engine",
                input_data={"query": request.query},
                context=context,
            )

            if result["success"]:
                data = result["data"]
                sql_result = Text2SqlResult(
                    sql=data.get("sql", ""),
                    confidence=data.get("confidence"),
                    columns=data.get("columns", []),
                    similar_examples=data.get("similar_examples", []),
                    schema_info=data.get("schema_info"),
                    metadata=data.get("metadata", {}),
                )

                return Text2SqlResponse(
                    success=True, data=sql_result, message="SQL生成成功"
                )
            else:
                raise HTTPException(
                    status_code=422,
                    detail=f"SQL生成失败: {result.get('error', '未知错误')}",
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")

    return app


app = create_app()
