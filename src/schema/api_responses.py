from typing import Dict, Any, List, Optional, Annotated
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ApiStatus(str, Enum):

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


class BaseResponse(BaseModel):
    success: bool = Field(description="操作是否成功")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")
    message: Optional[str] = Field(None, description="响应消息")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ErrorResponse(BaseResponse):
    success: bool = Field(default=False, description="操作失败")
    error_code: str = Field(description="错误代码")
    error_details: Optional[Dict[str, Any]] = Field(None, description="错误详细信息")


class SuccessResponse(BaseResponse):
    """成功响应模型"""

    success: bool = Field(default=True, description="操作成功")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")


class Text2SqlRequest(BaseModel):

    query: Annotated[str, Field(min_length=1)] = Field(description="自然语言查询")
    user_id: Optional[str] = Field(None, description="用户ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    options: Dict[str, Any] = Field(default_factory=dict, description="额外选项参数")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "查找所有流行音乐专辑",
                    "user_id": "user_123",
                    "session_id": "session_456",
                    "options": {"format": "detailed"},
                }
            ]
        }
    }


class Text2SqlResult(BaseModel):
    sql: str = Field(description="生成的SQL语句")
    confidence: Optional[float] = Field(None, description="生成置信度 (0.0-1.0)")
    columns: List[str] = Field(default_factory=list, description="查询结果列名")
    similar_examples: List[Dict[str, Any]] = Field(
        default_factory=list, description="相似示例"
    )
    schema_info: Optional[str] = Field(None, description="使用的数据库模式信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据信息")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "sql": "SELECT * FROM albums WHERE genre = 'pop'",
                    "confidence": 0.95,
                    "columns": ["id", "title", "artist_id", "release_date", "genre"],
                    "similar_examples": [],
                    "schema_info": "albums table schema",
                    "metadata": {"processing_time": "0.5s", "model_used": "qwen3-max"},
                }
            ]
        }
    }


class Text2SqlResponse(BaseResponse):
    """Text2SQL响应模型"""

    data: Text2SqlResult = Field(description="SQL生成结果数据")


class ComponentHealth(BaseModel):
    name: str = Field(description="组件名称")
    status: str = Field(description="健康状态 (healthy/degraded/unhealthy)")
    message: Optional[str] = Field(None, description="状态消息")
    last_check: datetime = Field(
        default_factory=datetime.now, description="最后检查时间"
    )
    details: Dict[str, Any] = Field(default_factory=dict, description="详细信息")


class SystemHealthData(BaseModel):

    status: str = Field(description="整体系统状态")
    middleware: Dict[str, Any] = Field(description="中间件信息")
    engines: Dict[str, ComponentHealth] = Field(description="引擎健康状态")
    total_engines: int = Field(description="引擎总数")
    healthy_engines: int = Field(description="健康引擎数")
    uptime: Optional[str] = Field(None, description="系统运行时间")
    version: str = Field(default="1.1.0", description="系统版本")


class HealthCheckResponse(BaseResponse):
    """健康检查响应模型"""

    data: SystemHealthData = Field(description="系统健康数据")


class ApiEndpoint(BaseModel):
    """API端点信息模型"""

    path: str = Field(description="端点路径")
    method: str = Field(description="HTTP方法")
    name: str = Field(description="端点名称")
    description: str = Field(description="端点描述")
    request_model: Optional[str] = Field(None, description="请求模型类名")
    response_model: Optional[str] = Field(None, description="响应模型类名")
    tags: List[str] = Field(default_factory=list, description="端点标签")


class ApiInfo(BaseModel):
    """API信息模型"""

    name: str = Field(description="API名称")
    version: str = Field(description="API版本")
    description: str = Field(description="API描述")
    api_version: str = Field(description="API版本号")
    endpoints: Dict[str, str] = Field(description="API端点映射")


# ===== API响应结构汇总 =====

API_RESPONSE_MODELS = {
    # 基础响应模型
    "BaseResponse": BaseResponse,
    "ErrorResponse": ErrorResponse,
    "SuccessResponse": SuccessResponse,
    # Text2SQL相关
    "Text2SqlRequest": Text2SqlRequest,
    "Text2SqlResult": Text2SqlResult,
    "Text2SqlResponse": Text2SqlResponse,
    # 健康检查相关
    "ComponentHealth": ComponentHealth,
    "SystemHealthData": SystemHealthData,
    "HealthCheckResponse": HealthCheckResponse,
    # API信息相关
    "ApiEndpoint": ApiEndpoint,
    "ApiInfo": ApiInfo,
}

API_ENDPOINTS = {
    # 基础端点
    "root": ApiEndpoint(
        path="/",
        method="GET",
        name="root",
        description="API根端点，返回API基础信息",
        response_model="ApiInfo",
        tags=["基础信息"],
    ),
    # 健康检查端点
    "health_check": ApiEndpoint(
        path="/api/v1/system/health",
        method="GET",
        name="get_system_health",
        description="系统健康检查，返回各组件状态",
        response_model="HealthCheckResponse",
        tags=["系统监控"],
    ),
    # Text2SQL端点
    "generate_sql": ApiEndpoint(
        path="/api/v1/app/text2sql/generate_sql",
        method="POST",
        name="generate_sql",
        description="自然语言转SQL接口",
        request_model="Text2SqlRequest",
        response_model="Text2SqlResponse",
        tags=["Text2SQL"],
    ),
}


def get_response_model_schema(model_name: str) -> Optional[Dict[str, Any]]:
    """获取响应模型的JSON Schema"""
    model_class = API_RESPONSE_MODELS.get(model_name)
    if model_class:
        return model_class.model_json_schema()
    return None


def get_all_response_models() -> Dict[str, Dict[str, Any]]:
    """获取所有响应模型的Schema"""
    schemas = {}
    for name, model_class in API_RESPONSE_MODELS.items():
        schemas[name] = model_class.model_json_schema()
    return schemas


def format_api_documentation() -> str:
    """格式化API文档"""
    doc = "# Melomane AI Middleware API 响应结构文档\n\n"
    doc += f"版本: 1.1.0\n"
    doc += f"生成时间: {datetime.now().isoformat()}\n\n"

    doc += "## API端点列表\n\n"
    for endpoint_name, endpoint in API_ENDPOINTS.items():
        doc += f"### {endpoint.name}\n"
        doc += f"- **路径**: `{endpoint.method} {endpoint.path}`\n"
        doc += f"- **描述**: {endpoint.description}\n"
        if endpoint.request_model:
            doc += f"- **请求模型**: {endpoint.request_model}\n"
        if endpoint.response_model:
            doc += f"- **响应模型**: {endpoint.response_model}\n"
        doc += f"- **标签**: {', '.join(endpoint.tags)}\n\n"

    doc += "## 响应模型结构\n\n"
    for model_name, model_class in API_RESPONSE_MODELS.items():
        doc += f"### {model_name}\n"
        doc += f"```python\n{model_class.__doc__ or '响应模型'}\n```\n"

        # 获取字段信息
        if hasattr(model_class, "model_fields"):
            doc += "字段说明:\n"
            for field_name, field_info in model_class.model_fields.items():
                field_type = getattr(field_info, "annotation", "Any")
                description = getattr(field_info, "description", "无描述")
                doc += f"- **{field_name}** ({field_type}): {description}\n"
        doc += "\n"

    return doc
