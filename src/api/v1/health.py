from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any
import logging
from datetime import datetime
import psutil
import platform
from ...schema.api_responses import (
    HealthCheckResponse,
    SystemHealthData,
    ComponentHealth,
    ErrorResponse,
)

logger = logging.getLogger(__name__)

# 创建健康检查路由器
router = APIRouter(
    prefix="/system",
    tags=["系统监控"],
    responses={
        503: {"description": "服务不可用"},
        500: {"description": "内部服务器错误"},
    },
)


def get_middleware():
    """获取中间件实例的依赖注入函数"""
    return None


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="系统健康检查",
    description="检查系统和所有组件的健康状态",
    responses={
        200: {
            "description": "系统健康",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "timestamp": "2025-09-22T16:00:00Z",
                        "message": "健康检查完成",
                        "data": {
                            "status": "healthy",
                            "middleware": {"initialized": True},
                            "engines": {},
                            "total_engines": 0,
                            "healthy_engines": 0,
                            "uptime": "2h 30m",
                            "version": "1.1.0",
                        },
                    }
                }
            },
        },
        503: {
            "description": "系统不健康",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "timestamp": "2025-09-22T16:00:00Z",
                        "message": "系统状态异常",
                        "error_code": "SYSTEM_DEGRADED",
                        "error_details": {
                            "unhealthy_components": ["database", "llm_service"]
                        },
                    }
                }
            },
        },
    },
)
async def get_system_health(middleware=Depends(get_middleware)):
    """
    获取系统健康状态

    检查系统各个组件的运行状态，包括：
    - 中间件状态
    - 各个引擎状态
    - 系统资源使用情况

    Returns:
        HealthCheckResponse: 系统健康检查结果
    """
    try:
        # 基础系统信息
        system_info = {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "architecture": platform.architecture()[0],
            "hostname": platform.node(),
        }

        # 如果中间件未初始化
        if not middleware:
            health_data = SystemHealthData(
                status="degraded",
                middleware={
                    "initialized": False,
                    "message": "中间件未初始化",
                    **system_info,
                },
                engines={},
                total_engines=0,
                healthy_engines=0,
                version="1.1.0",
            )

            return JSONResponse(
                status_code=503,
                content=HealthCheckResponse(
                    success=False, data=health_data, message="中间件未初始化"
                ).model_dump(),
            )

        # 检查中间件和引擎状态
        try:
            middleware_info = (
                middleware.get_system_info()
                if hasattr(middleware, "get_system_info")
                else {}
            )
            middleware_info.update(system_info)
        except Exception as e:
            middleware_info = {**system_info, "error": str(e)}

        engine_health = {}
        all_healthy = True

        # 检查所有引擎的健康状态
        if hasattr(middleware, "_engines"):
            for engine_name, engine in middleware._engines.items():
                try:
                    health = (
                        engine.health_check()
                        if hasattr(engine, "health_check")
                        else {"healthy": False, "message": "健康检查方法不存在"}
                    )
                    engine_health[engine_name] = ComponentHealth(
                        name=engine_name,
                        status=(
                            "healthy" if health.get("healthy", False) else "unhealthy"
                        ),
                        message=health.get("message", ""),
                        details=health,
                    )
                    if not health.get("healthy", False):
                        all_healthy = False
                except Exception as e:
                    engine_health[engine_name] = ComponentHealth(
                        name=engine_name,
                        status="unhealthy",
                        message=f"健康检查失败: {str(e)}",
                        details={"error": str(e)},
                    )
                    all_healthy = False

        health_data = SystemHealthData(
            status="healthy" if all_healthy else "degraded",
            middleware={"initialized": True, **middleware_info},
            engines=engine_health,
            total_engines=len(engine_health),
            healthy_engines=sum(
                1 for h in engine_health.values() if h.status == "healthy"
            ),
            version="1.1.0",
        )

        status_code = 200 if all_healthy else 503
        return JSONResponse(
            status_code=status_code,
            content=HealthCheckResponse(
                success=all_healthy, data=health_data, message="健康检查完成"
            ).model_dump(),
        )

    except Exception as e:
        logger.error(f"健康检查失败: {e}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                error_code="HEALTH_CHECK_FAILED", message=f"健康检查失败: {str(e)}"
            ).model_dump(),
        )


@router.get(
    "/health/detailed",
    summary="详细系统健康检查",
    description="获取包含系统资源使用情况的详细健康信息",
)
async def get_detailed_system_health(middleware=Depends(get_middleware)):
    """获取详细的系统健康信息，包含系统资源使用情况"""
    try:
        # 获取基础健康信息
        basic_health_response = await get_system_health(middleware)
        basic_health = basic_health_response.body

        # 添加系统资源信息
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            resource_info = {
                "cpu": {"usage_percent": cpu_usage, "cores": psutil.cpu_count()},
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "usage_percent": memory.percent,
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "usage_percent": (disk.used / disk.total) * 100,
                },
            }

            # 更新健康数据
            if isinstance(basic_health, bytes):
                import json

                health_data = json.loads(basic_health.decode())
            else:
                health_data = basic_health

            health_data["data"]["system_resources"] = resource_info

            return JSONResponse(
                status_code=basic_health_response.status_code, content=health_data
            )

        except Exception as resource_error:
            logger.warning(f"获取系统资源信息失败: {resource_error}")
            # 如果获取资源信息失败，仍返回基础健康信息
            return basic_health_response

    except Exception as e:
        logger.error(f"详细健康检查失败: {e}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                error_code="DETAILED_HEALTH_CHECK_FAILED",
                message=f"详细健康检查失败: {str(e)}",
            ).model_dump(),
        )


@router.get(
    "/health/components",
    summary="组件健康状态列表",
    description="获取所有注册组件的健康状态列表",
)
async def get_components_health(middleware=Depends(get_middleware)):
    """获取所有组件的健康状态列表"""
    try:
        if not middleware:
            return {
                "success": False,
                "message": "中间件未初始化",
                "data": {
                    "components": [],
                    "total_components": 0,
                    "healthy_components": 0,
                },
            }

        components = []

        if hasattr(middleware, "_engines"):
            for engine_name, engine in middleware._engines.items():
                try:
                    health = (
                        engine.health_check()
                        if hasattr(engine, "health_check")
                        else {"healthy": False}
                    )
                    components.append(
                        {
                            "name": engine_name,
                            "type": "engine",
                            "status": (
                                "healthy"
                                if health.get("healthy", False)
                                else "unhealthy"
                            ),
                            "message": health.get("message", ""),
                            "last_check": datetime.now().isoformat(),
                        }
                    )
                except Exception as e:
                    components.append(
                        {
                            "name": engine_name,
                            "type": "engine",
                            "status": "error",
                            "message": f"健康检查错误: {str(e)}",
                            "last_check": datetime.now().isoformat(),
                        }
                    )

        healthy_count = sum(1 for c in components if c["status"] == "healthy")

        return {
            "success": True,
            "message": "组件健康状态获取成功",
            "data": {
                "components": components,
                "total_components": len(components),
                "healthy_components": healthy_count,
            },
        }

    except Exception as e:
        logger.error(f"获取组件健康状态失败: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="COMPONENT_HEALTH_CHECK_FAILED",
                message=f"获取组件健康状态失败: {str(e)}",
            ).model_dump(),
        )
