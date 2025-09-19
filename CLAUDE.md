# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Text2SQL AI Middleware** project that implements an extensible AI middleware architecture for converting natural language queries to SQL. The project has been refactored from a monolithic Text2SQL implementation into a modern, scalable AI middleware platform that supports multiple AI engines through a plugin-based architecture.

## Development Commands

### Dependency Management
```bash
# Install/sync dependencies (using uv)
uv sync

# Add new dependency
uv add <package-name>

# Install dev dependencies
uv sync --dev
```

### Development Server
```bash
# Start development server
uv run python src/main.py

# Run with specific host/port
HOST=0.0.0.0 PORT=8000 uv run python src/main.py
```

### Code Quality
```bash
# Format code with Black
uv run black src/

# Run tests
uv run pytest

# Run tests with verbose output
uv run pytest -v
```

## Architecture Overview

The project follows a **middleware-based architecture** with the following key components:

### Core Architecture (`src/app/core/`)
- **`ai_engine.py`**: Abstract base class `AIEngine` defining the interface for all AI engines
- **`middleware.py`**: Core `AIMiddleware` class that manages engine registration, routing, and request processing

### Engine System (`src/app/engines/`)
- **Plugin-based AI Engines**: Each AI functionality is implemented as a separate engine
- **`text2sql_engine.py`**: Main Text2SQL conversion engine
- Engines implement the `AIEngine` interface for standardized integration

### Service Layers (`src/app/services/`)
- **Text2SQL Services**: Original Text2SQL implementation components
  - LLM integration (`llm/`)
  - Embedding models (`embedding/`)
  - Core conversion logic (`text_to_sql.py`)

### Provider System (`src/app/providers/`)
- **Database Providers**: Abstracted database connection and schema management
  - PostgreSQL provider with connection pooling
  - Schema introspection and validation
- **Vector Database**: ChromaDB integration for RAG functionality

### Application Layer (`src/`)
- **`app.py`**: FastAPI application factory with middleware integration
- **`main.py`**: Entry point and server startup logic
- **`config.py`**: Configuration management

## Key Design Patterns

### AI Engine Pattern
All AI functionality is implemented as engines that inherit from `AIEngine`:
```python
class CustomEngine(AIEngine):
    def initialize(self, config: Dict[str, Any]) -> bool:
        # Engine initialization logic
        return True

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Main processing logic
        return result

    def get_capabilities(self) -> List[EngineCapability]:
        # Define engine capabilities
        return capabilities
```

### Middleware Hooks
The system supports pre/post processing hooks for cross-cutting concerns:
- **LoggingHook**: Request/response logging
- **MetricsHook**: Performance metrics collection
- Custom hooks for authentication, rate limiting, etc.

### Request Processing Flow
1. Request received by FastAPI app
2. Middleware routes to appropriate engine
3. Pre-processing hooks execute
4. Engine processes the request
5. Post-processing hooks execute
6. Response returned to client

## API Endpoints

### Core Endpoints
- `GET /` - API information and available engines
- `GET /health` - Health check for all engines
- `GET /engines` - List all registered engines
- `GET /engines/{name}/capabilities` - Get engine capabilities

### Text2SQL Endpoints
- `GET /generate-sql` - Generate SQL from natural language (query parameter)
- `POST /generate-sql` - Generate SQL from natural language (JSON body)
- `POST /engines/{name}/process` - Generic engine processing endpoint

## Configuration

The project uses environment variables for configuration. Key variables from `.env.example`:

### Required Configuration
- `LLM_MODEL`: LLM model name (default: "qwen3-max-preview")
- `BASE_URL`: LLM service base URL
- `API_KEY`: LLM service API key
- `USER_DATABASE_URL`: User authentication database connection
- `MUSIC_DATABASE_URL`: Music data database connection

### Optional Configuration
- `BERT_MODEL_NAME`: Embedding model (default: "paraphrase-multilingual-MiniLM-L12-v2")
- `CHROMA_API_KEY`: ChromaDB API key
- `CHROMA_TENANT`: ChromaDB tenant
- `CHROMA_DATABASE`: ChromaDB database name
- `CHROMA_COLLECTION_NAME`: ChromaDB collection (default: "melomane_collection")

## Testing

Currently no test files are present in the repository. To add tests:
- Create `tests/` directory in project root
- Test files should follow `test_*.py` or `*_test.py` patterns
- Run with `uv run pytest` for basic execution
- Use `uv run pytest -v` for verbose output

## Key Implementation Details

### Text2SQL Processing Pipeline
The core Text2SQL functionality follows this pipeline:
1. **Schema Extraction**: `SchemaManager` extracts database structure
2. **Text Embedding**: `BertEmbedding` converts queries to vectors using multilingual BERT
3. **Vector Similarity**: `ChromaVectorStore` finds similar examples using ChromaDB
4. **SQL Generation**: `LLM` generates SQL using context and examples
5. **Validation**: `SQLValidator` validates generated SQL syntax

### Engine Registration
Engines are registered in the startup process and must implement:
- `initialize(config)`: Setup with configuration
- `process(input_data)`: Main processing logic
- `get_capabilities()`: Return engine capabilities
- `health_check()`: Return health status

### Import Path Structure
The project uses absolute imports from `src/app/`:
- Core: `from app.core.ai_engine import AIEngine`
- Services: `from app.services.text2sql.text_to_sql import Text2SQL`
- Providers: `from app.providers.database.schema_manager import SchemaManager`

## Adding New Engines

1. Create new engine class inheriting from `AIEngine` in `src/app/engines/`
2. Implement required abstract methods (`initialize`, `process`, `get_capabilities`)
3. Register engine in application startup using `middleware.register_engine()`
4. Define appropriate `EngineType` for categorization
5. Add health check logic specific to your engine's dependencies

## Development Notes

- Project name in pyproject.toml is "melomane_ai"
- Requires Python >=3.13
- The project maintains 100% backward compatibility with the original Text2SQL API
- Use `uv` for all dependency management (modern Python package manager)
- Follow the existing code patterns for consistency
- All engines should implement proper health checks and error handling
- Use the middleware hooks system for cross-cutting concerns rather than modifying core logic
- Configuration is loaded from `.env` file using python-dotenv
- The system supports both user authentication and music data databases