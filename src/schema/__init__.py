# -*- coding: utf-8 -*-
"""
Schema模块

包含项目的数据库Schema定义和API响应结构模型。
"""

from .database_schema import (
    DatabaseSchema,
    TableSchema,
    TableColumnInfo,
    TableConstraint,
    MELOMANE_DATABASE_SCHEMA,
    MUSIC_DATABASE_TABLES,
    USER_DATABASE_TABLES,
    get_schema_for_table,
    get_all_table_names,
    format_schema_for_llm,
)

from .api_responses import (
    BaseResponse,
    ErrorResponse,
    SuccessResponse,
    Text2SqlRequest,
    Text2SqlResult,
    Text2SqlResponse,
    ComponentHealth,
    SystemHealthData,
    HealthCheckResponse,
    RecommendationRequest,
    RecommendationItem,
    RecommendationResponse,
    ApiEndpoint,
    ApiInfo,
    API_RESPONSE_MODELS,
    API_ENDPOINTS,
    get_response_model_schema,
    get_all_response_models,
    format_api_documentation,
)

__all__ = [
    # 数据库Schema相关
    "DatabaseSchema",
    "TableSchema",
    "TableColumnInfo",
    "TableConstraint",
    "MELOMANE_DATABASE_SCHEMA",
    "MUSIC_DATABASE_TABLES",
    "USER_DATABASE_TABLES",
    "get_schema_for_table",
    "get_all_table_names",
    "format_schema_for_llm",
    # API响应相关
    "BaseResponse",
    "ErrorResponse",
    "SuccessResponse",
    "Text2SqlRequest",
    "Text2SqlResult",
    "Text2SqlResponse",
    "ComponentHealth",
    "SystemHealthData",
    "HealthCheckResponse",
    "RecommendationRequest",
    "RecommendationItem",
    "RecommendationResponse",
    "ApiEndpoint",
    "ApiInfo",
    "API_RESPONSE_MODELS",
    "API_ENDPOINTS",
    "get_response_model_schema",
    "get_all_response_models",
    "format_api_documentation",
]
