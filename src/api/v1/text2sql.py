# pylint: disable=astroid-error
from fastapi import APIRouter, HTTPException
from typing import Optional
import logging
import time

from ...schema.api_responses import (
    Text2SqlRequest,
    Text2SqlResult,
    Text2SqlResponse,
)
from ...services.text2sql import Text2SQL

logger = logging.getLogger(__name__)

# Text2SQL 路由
router = APIRouter(
    prefix="/app/text2sql",
    tags=["Text2SQL"],
    responses={
        404: {"description": "Not Found"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"},
    },
)

# 启动时初始化 Text2SQL 实例
text2sql = Text2SQL()


@router.post(
    "/generate_sql",
    response_model=Text2SqlResponse,
    summary="生成 SQL",
    description="将自然语言查询转换为 SQL。",
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
                            "columns": ["id", "title", "artist_id", "release_date", "genre"],
                            "similar_examples": [],
                            "schema_info": "albums table schema",
                            "metadata": {"processing_time": "0.5s"},
                        },
                    }
                }
            },
        },
    },
)
async def generate_sql(request: Text2SqlRequest) -> Text2SqlResponse:
    try:
        logger.info(
            f"Text2SQL request: user_id={request.user_id}, query='{request.query}'"
        )

        if not request.query or len(request.query.strip()) == 0:
            raise HTTPException(status_code=422, detail="查询内容为空")

        start_time = time.time()
        result_dict = text2sql.generate_sql(request.query)
        processing_time = f"{time.time() - start_time:.2f}s"

        if not result_dict["success"]:
            raise HTTPException(
                status_code=422,
                detail=result_dict.get("error", "SQL 生成失败"),
            )

        result = Text2SqlResult(
            sql=result_dict["sql"],
            columns=result_dict.get("columns", []),
            similar_examples=result_dict.get("similar_examples", []),
            schema_info=result_dict.get("schema_info"),
            metadata={
                "processing_time": processing_time,
                "user_id": request.user_id,
                "session_id": request.session_id,
            },
        )

        return Text2SqlResponse(success=True, data=result, message="SQL 生成成功")

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
) -> Text2SqlResponse:
    """GET 版本的生成 SQL 接口，内部复用 POST 实现。"""
    request = Text2SqlRequest(
        query=query, user_id=user_id, session_id=session_id, options={}
    )
    return await generate_sql(request)


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
