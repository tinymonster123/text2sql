# Text2SQL AI中间件

> 🚀 **可扩展的AI中间件平台** - 将Text2SQL功能重构为现代化、可扩展的AI中间件架构

## ✨ 特性

- 🏗️ **可扩展架构**: 基于插件式AI引擎设计，支持动态注册和管理多种AI功能
- 🔌 **中间件模式**: 支持请求/响应钩子，便于添加日志、指标、认证等功能
- 🐳 **容器化部署**: 使用Docker和uv进行现代化的项目管理和部署
- 🔍 **健康监控**: 内置健康检查和系统监控功能
- 📊 **性能指标**: 自动收集和报告性能指标
- 🌐 **RESTful API**: 完整的REST API接口，支持多种调用方式

## 🏗️ 架构概览

```
text2sql/
├── src/
│   ├── core/                 # 核心中间件架构
│   │   ├── ai_engine.py     # AI引擎抽象基类
│   │   └── middleware.py    # 中间件核心逻辑
│   ├── engines/              # AI引擎实现
│   │   ├── text2sql_engine.py # Text2SQL引擎
│   │   └── __init__.py
│   ├── database/             # 数据库相关模块
│   ├── llm/                  # LLM相关模块
│   ├── rag/                  # RAG相关模块
│   ├── app.py               # FastAPI应用
│   └── text_to_sql.py       # 原有Text2SQL实现
├── scripts/
│   ├── startup.py           # 统一启动脚本
│   └── download_model.py    # 模型预下载脚本
├── pyproject.toml           # 项目配置（uv管理）
├── Dockerfile               # 容器化配置
├── docker-compose.yml       # 服务编排
└── .env.example            # 环境配置示例
```

## 🚀 快速开始

### 使用Docker Compose（推荐）

```bash
# 1. 克隆项目
git clone <repository-url>
cd text2sql

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置必要的配置

# 3. 启动所有服务
docker-compose up -d

# 4. 检查服务状态
curl http://localhost:8000/health
```

### 本地开发

```bash
# 1. 安装uv（如果尚未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 同步依赖
uv sync

# 3. 配置环境变量
cp .env.example .env

# 4. 启动服务
uv run python scripts/startup.py
```

## 📡 API接口

### 核心接口

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 获取API基本信息 |
| `/health` | GET | 健康检查 |
| `/engines` | GET | 列出所有引擎 |
| `/engines/{name}/capabilities` | GET | 获取引擎能力 |

### Text2SQL接口

| 端点 | 方法 | 描述 |
|------|------|------|
| `/generate-sql` | GET/POST | 生成SQL查询 |

#### 请求示例

```bash
# GET请求
curl "http://localhost:8000/generate-sql?query=查询所有用户的姓名和邮箱"

# POST请求
curl -X POST "http://localhost:8000/generate-sql" \
  -H "Content-Type: application/json" \
  -d '{"query": "查询所有用户的姓名和邮箱", "user_id": "user123"}'
```

#### 响应格式

```json
{
  "success": true,
  "sql": "SELECT name, email FROM users;",
  "error": null,
  "columns": ["name", "email"],
  "similar_examples": [],
  "metadata": {
    "engine": "text2sql_engine",
    "version": "1.0.0",
    "query": "查询所有用户的姓名和邮箱"
  }
}
```

## 🔧 配置

### 环境变量

| 变量名 | 默认值 | 描述 |
|--------|--------|------|
| `AI_MIDDLEWARE_MODE` | `development` | 运行模式 |
| `AI_MIDDLEWARE_LOG_LEVEL` | `INFO` | 日志级别 |
| `HOST` | `0.0.0.0` | 服务器地址 |
| `PORT` | `8000` | 服务器端口 |
| `DB_HOST` | `localhost` | 数据库地址 |
| `CHROMA_HOST` | `localhost` | 向量数据库地址 |

### 自定义引擎

```python
from core.ai_engine import AIEngine, EngineCapability
from core.middleware import AIMiddleware, EngineType

class CustomEngine(AIEngine):
    def __init__(self):
        super().__init__("custom_engine", "1.0.0", "自定义AI引擎")

    def initialize(self, config):
        # 初始化逻辑
        self.is_initialized = True
        return True

    def process(self, input_data):
        # 处理逻辑
        return {"result": "处理结果"}

    def get_capabilities(self):
        return [EngineCapability(
            name="custom_capability",
            description="自定义能力",
            input_types=["text"],
            output_types=["json"]
        )]

# 注册引擎
middleware = AIMiddleware()
custom_engine = CustomEngine()
custom_engine.initialize({})
middleware.register_engine(custom_engine, EngineType.CUSTOM)
```

## 🔍 监控和指标

### 健康检查

```bash
curl http://localhost:8000/health
```

返回系统健康状态和各引擎状态。

### 系统信息

```bash
curl http://localhost:8000/engines
```

返回所有注册的引擎信息和类型。

## 🛠️ 开发

### 项目结构

- **核心架构** (`src/core/`): AI中间件的核心组件
- **引擎实现** (`src/engines/`): 各种AI引擎的具体实现
- **原有模块**: 数据库、LLM、RAG等功能模块保持不变

### 添加新引擎

1. 继承 `AIEngine` 基类
2. 实现必要的抽象方法
3. 在启动脚本中注册引擎

### 钩子和中间件

支持添加自定义钩子来扩展功能：

```python
class CustomHook(MiddlewareHook):
    async def before_process(self, engine_name, input_data, context):
        # 前置处理
        return input_data

    async def after_process(self, engine_name, result, context):
        # 后置处理
        return result

middleware.add_middleware_hook(CustomHook())
```

## 🐳 部署

### Docker

```bash
# 构建镜像
docker build -t text2sql-middleware .

# 运行容器
docker run -d \
  --name text2sql \
  -p 8000:8000 \
  --env-file .env \
  text2sql-middleware
```

### Docker Compose

项目包含完整的 `docker-compose.yml`，包括：
- Text2SQL AI中间件服务
- ChromaDB向量数据库
- PostgreSQL数据库

## 📈 性能优化

- 模型预下载：构建时预下载AI模型
- 多阶段构建：优化Docker镜像大小
- 缓存机制：充分利用各种缓存
- 异步处理：支持异步请求处理

## 🔄 从单体到中间件的迁移

原有的Text2SQL功能已完全封装为AI引擎，保持100%向后兼容：

- ✅ API接口保持不变
- ✅ 响应格式保持不变
- ✅ 所有功能特性保持不变
- ➕ 新增中间件管理能力
- ➕ 新增健康检查和监控
- ➕ 新增引擎注册和管理

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目！

## 📄 许可证

本项目采用 MIT 许可证。