# -*- coding: utf-8 -*-
"""
Schema模块

包含项目的API响应结构模型。
"""

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
    ApiEndpoint,
    ApiInfo,
    API_RESPONSE_MODELS,
    API_ENDPOINTS,
    get_response_model_schema,
    get_all_response_models,
    format_api_documentation,
)

__all__ = [
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
    "ApiEndpoint",
    "ApiInfo",
    "API_RESPONSE_MODELS",
    "API_ENDPOINTS",
    "get_response_model_schema",
    "get_all_response_models",
    "format_api_documentation",
]
