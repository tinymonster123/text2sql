# Chunking + Re-ranking 优化实施记录

## 概述

本次开发为 Melomane AI 的 Text2SQL 系统引入了 Schema Chunking 和 Cross-Encoder Re-ranking，优化了 RAG 管道的检索质量和生成精度。

## 优化前的流程

```
用户查询 → BERT 嵌入 → ChromaDB 检索 top-5 示例 → 全量 schema + 示例 → LLM 生成 SQL
```

**问题**：
1. 全量 schema 传入 LLM prompt，随着表数量增长浪费 token 且降低精度
2. 仅依赖 bi-encoder（BERT MiniLM）的余弦相似度，检索精度有限

## 优化后的流程

```
用户查询
  → BERT 嵌入
  → Schema Chunking：向量检索 top-3 相关表 → 精简 schema
  → 示例检索：ChromaDB 召回 top-10 相似示例
  → Re-ranking：Cross-Encoder 对 top-10 重排 → 取 top-3
  → LLM 生成 SQL（精简 schema + 高质量 few-shot）
  → SQL 验证 & 存储
```

## 新增文件

| 文件 | 说明 |
|------|------|
| `src/services/text2sql/chunking/__init__.py` | 导出 SchemaChunker |
| `src/services/text2sql/chunking/schema_chunker.py` | Schema 分块器：按表拆分 schema，向量化存储，检索相关表 |
| `src/services/text2sql/reranking/__init__.py` | 导出 CrossEncoderReranker |
| `src/services/text2sql/reranking/cross_encoder_reranker.py` | Cross-Encoder 重排序器，使用 BAAI/bge-reranker-base |
| `src/api/v1/api.py` | FastAPI 应用入口（修复路由重构后缺失的文件） |
| `tests/test_rag_eval.py` | DeepEval RAG 管道评估测试脚本 |
| `data/test_dataset.json` | 100 条测试数据集 |

## 修改文件

| 文件 | 改动 |
|------|------|
| `src/core/config.py` | 新增 `RERANKER_MODEL_NAME`、`SCHEMA_COLLECTION_NAME` 配置项 |
| `src/providers/vectordb/chroma_vector_store.py` | `__init__` 支持自定义 `collection_name` 参数；修复 `_client` 类变量引用 bug |
| `src/providers/database/schema_manager.py` | 新增 `format_partial_schema()` 方法，只格式化指定表 |
| `src/services/text2sql/text_to_sql.py` | 集成 chunking + re-ranking 完整流程 |
| `src/api/v1/text2sql.py` | 移除无用的 middleware 占位符，直接接入 Text2SQL 实例 |
| `src/schema/__init__.py` | 移除不存在的 `database_schema` 和 `Recommendation*` 导入 |
| `pyproject.toml` | 依赖版本更新，新增 deepeval |
| `.env.example` | 新增 `RERANKER_MODEL_NAME`、`SCHEMA_COLLECTION_NAME` |

## 修复的问题

### 1. 模块导入路径不统一
项目中混用 `from app.providers...` 和 `from melomane_ai.src...` 两种导入风格，统一改为 `from src...`。涉及 7 个文件。

### 2. ChromaVectorStore 类变量引用 bug
`get_chroma_client()` 是 `@staticmethod`，但内部直接引用 `_client` 而非 `ChromaVectorStore._client`，导致 `UnboundLocalError`。

### 3. 缺失的路由入口文件
`src/api/v1/api.py` 在之前路由重构时被删除但 `__init__.py` 未同步更新，导致 `ModuleNotFoundError`。

### 4. schema/__init__.py 导入不存在的模块
`database_schema.py` 和 `Recommendation*` 类不存在但被导入。

### 5. .env 变量名拼写错误
`ChROMA_API_KEY` 应为 `CHROMA_API_KEY`。

## 关键设计决策

### Schema Chunking 幂等性
`SchemaChunker.ensure_indexed()` 通过 MD5 哈希检测 schema 内容是否变更。相同 schema 不会重复索引，只在首次或 schema 变更时重建向量索引。

### 两阶段检索架构
- **粗排**：bi-encoder（BERT MiniLM）从全量数据召回 top-10，速度快
- **精排**：cross-encoder（bge-reranker-base）对 10 个候选联合编码打分，取 top-3，精度高

这是工业界标准的召回-排序范式。

### ChromaDB 多集合复用
通过给 `ChromaVectorStore.__init__` 添加 `collection_name` 参数，schema 向量使用独立集合 `melomane_schema_collection`，复用同一个 ChromaDB Cloud 客户端。

## 模型信息

| 模型 | 用途 | 大小 | 缓存位置 |
|------|------|------|---------|
| paraphrase-multilingual-MiniLM-L12-v2 | BERT 文本嵌入 | 458MB | `~/.cache/huggingface/hub/` |
| BAAI/bge-reranker-base | Cross-Encoder 重排序 | 134MB | `~/.cache/huggingface/hub/` |

模型首次下载后缓存在本地，后续启动直接从磁盘加载。

## 测试验证

### 接口测试
```bash
curl -s -X POST http://localhost:8000/api/v1/app/text2sql/generate_sql \
  -H "Content-Type: application/json" \
  -d '{"query": "查询所有歌手的名字"}'
```

返回结果确认：
- Schema Chunking 选中 3 张相关表（而非全量 schema）
- Re-ranking 完成示例重排
- LLM 生成正确 SQL：`SELECT "artist_name" FROM "music_main";`
- 耗时 5.67s（含 LLM 调用）

### 测试数据集
`data/test_dataset.json` 包含 100 条测试用例，覆盖：
- 单表查询（筛选、聚合、排序、分组、模糊搜索）
- 多表 JOIN（音频特征、主题得分、歌词查询）
- 三/四表 JOIN
- 子查询和窗口函数
- 100 条 SQL 全部通过数据库执行验证

### DeepEval 评估
使用 DeepEval 3.8.8 进行 RAG 管道评估，4 个指标：
- **AnswerRelevancyMetric**：生成的 SQL 是否与用户查询相关
- **FaithfulnessMetric**：SQL 是否忠于检索到的 schema 上下文
- **ContextualRelevancyMetric**：检索到的 schema 是否与查询相关
- **ContextualPrecisionMetric**：检索上下文排序是否合理

运行命令：
```bash
python tests/test_rag_eval.py --limit 10    # 快速测试
python tests/test_rag_eval.py --limit 100   # 全量测试
```

Judge 模型使用阿里云 `qwen-max`（JSON 输出最稳定）。
