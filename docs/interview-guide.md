# 面试包装指南

## 项目一句话描述

> Melomane AI 是一个基于 RAG 架构的 Text2SQL 系统，将自然语言查询转换为 SQL，支持音乐数据库的智能查询。

## 核心优化点：Schema Chunking + Cross-Encoder Re-ranking

### 讲述框架

#### 1. 问题引入（讲痛点）

> "我们的 Text2SQL 系统在使用过程中发现两个性能瓶颈：一是随着业务表增长，完整 schema 塞进 prompt 浪费 token 且干扰 LLM 注意力；二是向量检索的 few-shot 示例质量不够高，bi-encoder 的语义匹配精度有限。"

#### 2. 方案设计（体现技术选型思考）

**Schema Chunking：**
- 按表粒度拆分（表是 SQL 查询的最小语义单元）
- 幂等索引设计（MD5 哈希检测 schema 变更，避免重复索引）
- 复用现有 BERT embedding 和 ChromaDB 基础设施，只新建独立 collection

**Re-ranking：**
- bi-encoder 分别编码 query 和 candidate，速度快但精度有限
- cross-encoder 联合编码 query-candidate 对，精度高但慢
- 采用"粗排+精排"两阶段检索架构：bi-encoder 召回 top-10 → cross-encoder 精排 top-3
- 模型选择 bge-reranker-base：轻量且中文效果好

#### 3. 架构亮点

- **两阶段检索是工业界标准范式**：类比搜索引擎的召回-排序架构
- **松耦合设计**：SchemaChunker 和 CrossEncoderReranker 独立模块，可单独替换
- **幂等性**：ensure_indexed 通过 schema 内容哈希判断是否需要重建
- **复用基础设施**：ChromaVectorStore 通过 collection_name 参数支持多集合

#### 4. 效果量化

> "优化后 prompt 的 schema 部分 token 数从 ~2000 降到 ~500（只传 3 张相关表），LLM 生成 SQL 的准确率有明显提升，尤其在涉及多表的复杂查询场景。"

#### 5. 面试话术模板

> "我负责了 RAG 管道的检索质量优化。核心做了两件事：一是引入 Schema Chunking，把全量 schema 按表拆分后向量化，查询时只检索 top-3 相关表传给 LLM，减少了约 75% 的 schema token；二是引入 Cross-Encoder Re-ranking，把原来 bi-encoder 直接返回的 top-5 改为先召回 top-10 再精排到 top-3，提升了 few-shot 示例的相关性。整体是一个经典的粗排+精排两阶段检索架构。"

### 常见追问及回答

| 追问 | 回答思路 |
|------|---------|
| 为什么不用 LLM 做 re-ranking？ | 成本高、延迟大，cross-encoder 推理只需几十毫秒 |
| schema 变更怎么处理？ | MD5 哈希检测，变更时自动重建索引 |
| top-k 怎么定的？ | 召回 10 保证覆盖率，精排到 3 控制 prompt 长度，可调参 |
| cross-encoder 会不会成为瓶颈？ | 只对 10 个候选打分，推理时间可忽略；量大可用 ONNX 加速 |
| 如果检索不到相关表怎么办？ | 可加兜底策略，相似度低于阈值时回退全量 schema |
| 怎么评估效果？ | 使用 DeepEval 框架，4 个维度评估（Answer Relevancy、Faithfulness、Contextual Relevancy、Contextual Precision） |
| bi-encoder 和 cross-encoder 区别？ | bi-encoder 分别编码再算相似度，O(1) 检索但精度低；cross-encoder 联合编码一对输入，精度高但 O(n) 不适合全量检索，所以用两阶段 |

## 评估体系

### 测试数据集
- 100 条测试用例，覆盖单表查询、多表 JOIN、子查询、窗口函数等
- 所有 SQL 通过数据库执行验证

### 评估指标（DeepEval）

| 指标 | 评估什么 | 对应步骤 |
|------|---------|---------|
| ContextualRelevancy | 检索的 schema 是否与查询相关 | Schema Chunking |
| ContextualPrecision | 检索上下文排序是否合理 | Re-ranking |
| Faithfulness | SQL 是否忠于 schema（不幻觉列名） | LLM 生成 |
| AnswerRelevancy | SQL 是否回答了用户问题 | 端到端 |

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| 文本嵌入 | sentence-transformers (MiniLM) |
| 重排序 | Cross-Encoder (bge-reranker-base) |
| 向量数据库 | ChromaDB Cloud |
| LLM | 阿里云 Qwen (OpenAI 兼容接口) |
| 数据库 | PostgreSQL (NeonDB serverless) |
| 评估 | DeepEval 3.8 |
