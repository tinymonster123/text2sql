from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Any
import logging

from ...schema.api_responses import (
    Text2SqlRequest,
    Text2SqlResult,
    Text2SqlResponse,
    ErrorResponse,
)

logger = logging.getLogger(__name__)

# Text2SQL 路由
router = APIRouter(
    prefix="/app/text2sql",
    tags=["Text2SQL"],
    responses={
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"},
        503: {"description": "Service Unavailable"},
    },
)


def get_middleware() -> Optional[Any]:
    """依赖注入占位器：目前返回 None（未实现中间件注入）。"""
    return None


@router.post(
    "/generate_sql",
    response_model=Text2SqlResponse,
    summary="生成 SQL",
    description="将自然语言查询转换为 SQL（模拟实现，需中间件支持）。",
    responses={
        200: {
            "description": "SQL 生成成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "timestamp": "2025-09-22T16:00:00Z",
                        "message": "SQL 生成成功",
                        "data": {
                            "sql": "SELECT * FROM albums WHERE genre = 'pop'",
                            "confidence": 0.95,
                            "columns": [
                                "id",
                                "title",
                                "artist_id",
                                "release_date",
                                "genre",
                            ],
                            "similar_examples": [],
                            "schema_info": "albums table schema",
                            "metadata": {"processing_time": "0.5s"},
                        },
                    }
                }
            },
        },
        422: {
            "description": "请求参数错误或无法生成 SQL",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "timestamp": "2025-09-22T16:00:00Z",
                        "message": "SQL 生成失败",
                        "error_code": "SQL_GENERATION_FAILED",
                        "error_details": {"reason": "invalid input"},
                    }
                }
            },
        },
    },
)
async def generate_sql(
    request: Text2SqlRequest, middleware=Depends(get_middleware)
) -> Text2SqlResponse:
    """将自然语言查询转换为 SQL（目前为模拟返回，依赖中间件实现真实逻辑）。

    Args:
        request: Text2SqlRequest 包含 query, user_id, session_id, options 等字段。
        middleware: 通过依赖注入获得的中间件实例（目前返回 None）。

    Returns:
        Text2SqlResponse: 包含生成的 SQL 及相关元数据。
    """
    if not middleware:
        # 中间件未注入，返回服务不可用（注意：上层会将此转为 HTTP 503）
        raise HTTPException(status_code=503, detail="中间件未初始化，无法生成真实 SQL")

    try:
        logger.info(
            f"Text2SQL request: user_id={request.user_id}, query='{request.query}'"
        )

        # 简单校验
        if not request.query or len(request.query.strip()) == 0:
            raise HTTPException(status_code=422, detail="查询内容为空")

        temp_sql = f"-- NL Query: {request.query}\n-- Generated SQL (placeholder)"

        result = Text2SqlResult(
            sql=temp_sql,
            confidence=0.0,
            columns=[],
            similar_examples=[],
            schema_info=None,
            metadata={
                "status": "pending_middleware_implementation",
                "query_length": len(request.query),
                "user_id": request.user_id,
                "session_id": request.session_id,
            },
        )

        return Text2SqlResponse(success=True, data=result, message="模拟 SQL 生成成功")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Text2SQL error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SQL 生成失败: {str(e)}")


@router.get(
    "/generate_sql",
    response_model=Text2SqlResponse,
    summary="生成 SQL (GET)",
    description="通过 GET 请求生成 SQL（仅用于快速测试，功能同 POST /generate_sql）。",
)
async def generate_sql_get(
    query: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    middleware=Depends(get_middleware),
) -> Text2SqlResponse:
    """GET 版本的生成 SQL 接口，内部复用 POST 实现。"""
    request = Text2SqlRequest(
        query=query, user_id=user_id, session_id=session_id, options={}
    )
    return await generate_sql(request, middleware)


@router.get(
    "/capabilities",
    summary="Text2SQL 能力说明",
    description="返回当前 Text2SQL 服务支持的数据库、语言和特性说明（静态信息）。",
)
async def get_text2sql_capabilities():
    """返回 Text2SQL 服务的静态能力信息。"""
    return {
        "success": True,
        "data": {
            "supported_databases": ["PostgreSQL"],
            "supported_languages": ["中文", "English"],
            "max_query_length": 1000,
            "supported_sql_operations": [
                "SELECT",
                "JOIN",
                "WHERE",
                "GROUP BY",
                "ORDER BY",
                "LIMIT",
            ],
            "features": {
                "natural_language_understanding": True,
                "schema_awareness": True,
                "example_learning": True,
                "confidence_scoring": True,
                "query_optimization_suggestions": False,
            },
        },
        "message": "Text2SQL 能力信息",
    }
