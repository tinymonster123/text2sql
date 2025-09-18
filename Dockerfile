FROM python:3.13-slim as base

WORKDIR /app

# 复制uv二进制文件
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 设置环境变量
ENV HF_ENDPOINT=https://hf-mirror.com
ENV HF_HUB_FALLBACK_ENDPOINT=https://huggingface.co
ENV HF_HOME=/app/huggingface_cache
ENV HF_HUB_DOWNLOAD_TIMEOUT=120
ENV REQUESTS_TIMEOUT=120
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:$PYTHONPATH"

# 设置AI中间件特定环境变量
ENV AI_MIDDLEWARE_MODE=production
ENV AI_MIDDLEWARE_LOG_LEVEL=INFO

# 构建阶段
FROM base as builder

# 复制项目配置文件
COPY pyproject.toml uv.lock* ./

# 同步依赖
RUN uv sync --frozen

# 复制模型下载脚本（如果存在）
COPY scripts/download_model.py ./scripts/download_model.py 2>/dev/null || echo "跳过模型下载脚本"

# 尝试预下载模型（允许失败）
RUN uv run python scripts/download_model.py || echo "模型下载失败，将在运行时下载"

# 最终阶段
FROM base as final

# 复制虚拟环境和缓存
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/huggingface_cache /app/huggingface_cache

# 复制源代码
COPY src ./src

# 复制配置文件
COPY .env.example .env

# 复制脚本目录（如果存在）
COPY scripts/ ./scripts/ 2>/dev/null || echo "跳过scripts目录"

# 创建数据目录
RUN mkdir -p /app/data

# 设置权限
RUN chmod -R 755 /app

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uv", "run", "python", "scripts/startup.py"]