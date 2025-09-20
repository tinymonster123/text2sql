from fastapi import FastAPI, HTTPException, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# 基础响应模型
class BaseResponse(BaseModel):
    """基础响应模型，包含通用字段"""

    success: bool = Field(..., description="请求是否成功")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")
    message: Optional[str] = Field(None, description="可选消息")


class ErrorResponse(BaseResponse):
    """错误响应模型"""

    success: bool = Field(False, description="错误响应始终为false")
    error_code: str = Field(..., description="错误代码")
    error_details: Optional[Dict[str, Any]] = Field(None, description="附加错误详情")


# Text2SQL 业务模型
class Text2SqlRequest(BaseModel):
    """Text2SQL生成请求"""

    query: str = Field(..., min_length=1, description="自然语言查询")
    user_id: Optional[str] = Field(None, description="用户标识符")
    session_id: Optional[str] = Field(None, description="会话标识符")
    options: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="附加选项"
    )


class Text2SqlResult(BaseModel):
    """Text2SQL生成结果"""

    sql: str = Field(..., description="生成的SQL查询")
    confidence: Optional[float] = Field(None, description="置信度分数")
    columns: List[str] = Field(default_factory=list, description="预期结果列")
    similar_examples: List[Dict[str, Any]] = Field(
        default_factory=list, description="使用的相似示例"
    )
    schema_info: Optional[str] = Field(None, description="使用的模式信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元数据")


class Text2SqlResponse(BaseResponse):
    """Text2SQL生成响应"""

    data: Text2SqlResult = Field(..., description="SQL生成结果")


# 系统健康检查模型
class HealthCheckResponse(BaseResponse):
    """健康检查响应"""

    data: Dict[str, Any] = Field(..., description="健康检查详情")


def create_app(middleware=None) -> FastAPI:
    """
    创建并配置FastAPI应用程序。

    Args:
        middleware: AI中间件实例

    Returns:
        配置好的FastAPI应用程序
    """
    app = FastAPI(
        title="Melomane AI Middleware",
        description="Melomane AI 中间件 - 智能自然语言转SQL工具",
        version="1.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # API版本前缀
    API_PREFIX = "/api/v1"

    @app.get("/", response_model=Dict[str, Any])
    async def root():
        """API根端点，提供基本信息"""
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
        """获取系统健康状态"""
        try:
            if not middleware:
                return JSONResponse(
                    status_code=503,
                    content=ErrorResponse(
                        error_code="MIDDLEWARE_NOT_INITIALIZED",
                        message="中间件未初始化",
                    ).dict(),
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

    # text2sql
    @app.post(
        f"{API_PREFIX}/app/text2sql/generate_sql", response_model=Text2SqlResponse
    )
    async def generate_sql(request: Text2SqlRequest):
        """从自然语言查询生成SQL"""
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

            # 使用text2sql引擎处理
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
