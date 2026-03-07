# DeepEval 性能分析

## 为什么 DeepEval 评估耗时很长

### 核心原因：每个指标需要多次串行 LLM 调用

从 DeepEval 3.8.8 源码分析，每个指标对每个 test case 的 LLM 调用链如下：

### FaithfulnessMetric（4 次 LLM 调用）

```
源码位置: deepeval/metrics/faithfulness/faithfulness.py:153-159

Step 1: _a_generate_truths()    → 1 次调用（从 retrieval_context 提取事实）
Step 2: _a_generate_claims()    → 1 次调用（从 actual_output 提取声明）
        ↑ Step 1 和 2 通过 asyncio.gather 并行
Step 3: _a_generate_verdicts()  → 1 次调用（逐条判断声明是否忠于事实）
Step 4: _a_generate_reason()    → 1 次调用（生成最终解释）
        ↑ Step 3 和 4 必须串行（依赖前一步结果）
```

### AnswerRelevancyMetric（3 次 LLM 调用）

```
源码位置: deepeval/metrics/answer_relevancy/answer_relevancy.py:143-150

Step 1: _a_generate_statements()  → 1 次调用（从 output 提取陈述）
Step 2: _a_generate_verdicts()    → 1 次调用（判断每条陈述是否与 input 相关）
Step 3: _a_generate_reason()      → 1 次调用（生成解释）
        ↑ 全部串行
```

### ContextualRelevancyMetric（N+1 次 LLM 调用）

```
源码位置: deepeval/metrics/contextual_relevancy/contextual_relevancy.py:149-158

Step 1: _a_generate_verdicts() × N  → N 次调用（N = retrieval_context 条数）
        ↑ 通过 asyncio.gather 并行
Step 2: _a_generate_reason()        → 1 次调用
```

### ContextualPrecisionMetric（2 次 LLM 调用）

```
Step 1: _a_generate_verdicts()  → 1 次调用
Step 2: _a_generate_reason()    → 1 次调用
```

### 总调用量

| 场景 | 每 case LLM 调用 | 5 个 case | 100 个 case |
|------|-----------------|-----------|-------------|
| Faithfulness | 4 | 20 | 400 |
| AnswerRelevancy | 3 | 15 | 300 |
| ContextualRelevancy | ~3 | ~15 | ~300 |
| ContextualPrecision | 2 | 10 | 200 |
| **合计** | **~12** | **~60** | **~1200** |

### 并发调度模型

```python
# deepeval/evaluate/execute.py:577
semaphore = asyncio.Semaphore(async_config.max_concurrent)  # 默认 20
```

- test case 之间：并行（最多 20 个并发）
- 同一 case 的 4 个指标：并行（asyncio.gather）
- 每个指标内部的多步骤：串行（有依赖关系）

### 阿里云 API 叠加的延迟

以 `qwen-max` 为例，每次 API 调用约 2-5 秒：
- 5 个 test case：~60 次调用 × 3s ≈ 3 分钟（理论并行最优）
- 实际因串行依赖约 5-8 分钟
- 100 个 test case：理论 ~1200 次调用，约 40-60 分钟

### JSON 解析失败的额外代价

```python
# deepeval/metrics/utils.py:403-408
def trimAndLoadJson(jsonStr, metric):
    try:
        return json.loads(jsonStr)
    except json.JSONDecodeError:
        raise ValueError("Evaluation LLM outputted an invalid JSON.")
```

Qwen 模型有时返回非标准 JSON（markdown 包裹、非法转义），导致解析失败后整个 task 报错。

### 优化建议

1. **减少指标数量**：只用 AnswerRelevancy + Faithfulness（2 个最核心的）
2. **关闭 reason 生成**：`include_reason=False`，每个指标省 1 次调用
3. **用更快的 judge**：qwen-turbo 快但 JSON 不稳，qwen-plus 是折中选择
4. **利用缓存**：`.deepeval/.deepeval-cache.json` 会缓存已跑过的 case，重跑时跳过
5. **分批跑**：每次跑 10-20 条，避免单次运行时间过长
