# -*- coding: utf-8 -*-
"""
DeepEval RAG 管道评估测试

评估 Text2SQL 系统的检索质量和生成质量：
- AnswerRelevancyMetric: 生成的 SQL 是否与用户查询相关
- FaithfulnessMetric: 生成的 SQL 是否忠于检索到的 schema 上下文
- ContextualRelevancyMetric: 检索到的 schema 是否与查询相关
- ContextualPrecisionMetric: 检索到的上下文排序是否合理
"""

import json
import logging
import os
import re
import time
from typing import Optional

# 设置 DeepEval 超时（秒）
os.environ["DEEPEVAL_PER_TASK_TIMEOUT_SECONDS_OVERRIDE"] = "600"

from deepeval import evaluate
from deepeval.dataset import EvaluationDataset, Golden
from deepeval.models import DeepEvalBaseLLM
from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    ContextualRelevancyMetric,
    ContextualPrecisionMetric,
)
from tests.custom_metrics import (
    ExecutionAccuracyMetric,
    ValidSqlMetric,
    TableSelectionMetric,
)
from deepeval.test_case import LLMTestCase
from openai import AsyncOpenAI, OpenAI

from src.core.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _clean_json_response(content: str) -> str:
    """清理 Qwen 模型返回的 JSON，修复常见问题"""
    content = content.strip()
    # 去除 markdown 代码块包裹
    content = re.sub(r'^```(?:json)?\s*', '', content)
    content = re.sub(r'\s*```$', '', content)
    # 去除 BOM 和零宽字符
    content = content.lstrip('\ufeff\u200b')
    # 修复非法反斜杠转义（如 \_ \* 等非标准转义）
    content = re.sub(r'\\([^"\\/bfnrtu])', r'\1', content)
    return content.strip()


class QwenEvalModel(DeepEvalBaseLLM):
    """使用阿里云 Qwen 作为 DeepEval 的评估 Judge 模型"""

    def __init__(self, model_name: str = "qwen-max"):
        self.client = OpenAI(api_key=Config.API_KEY, base_url=Config.BASE_URL)
        self.async_client = AsyncOpenAI(api_key=Config.API_KEY, base_url=Config.BASE_URL)
        self.model_name = model_name

    def load_model(self):
        return self.client

    def _call_api(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You must respond with valid JSON only. No markdown, no extra text, no code blocks."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=4096,
        )
        return response.choices[0].message.content

    async def _async_call_api(self, prompt: str) -> str:
        response = await self.async_client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You must respond with valid JSON only. No markdown, no extra text, no code blocks."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=4096,
        )
        return response.choices[0].message.content

    def generate(self, prompt: str, schema=None) -> str:
        raw = ""
        content = ""
        for attempt in range(MAX_RETRIES):
            try:
                raw = self._call_api(prompt)
                content = _clean_json_response(raw)
                json.loads(content)
                return content
            except Exception as e:
                logger.warning(f"generate() 第 {attempt+1} 次尝试失败: {e}")
        logger.error(f"generate() {MAX_RETRIES} 次重试后仍失败，返回原始内容")
        return content or raw

    async def a_generate(self, prompt: str, schema=None) -> str:
        raw = ""
        content = ""
        for attempt in range(MAX_RETRIES):
            try:
                raw = await self._async_call_api(prompt)
                content = _clean_json_response(raw)
                json.loads(content)
                return content
            except Exception as e:
                logger.warning(f"a_generate() 第 {attempt+1} 次尝试失败: {e}")
        logger.error(f"a_generate() {MAX_RETRIES} 次重试后仍失败，返回原始内容")
        return content or raw

    def get_model_name(self) -> str:
        return self.model_name


def load_test_dataset(path: str = "data/test_dataset.json", limit: Optional[int] = None):
    """加载测试数据集"""
    with open(path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    if limit:
        dataset = dataset[:limit]
    return dataset


def push_dataset_to_confident(path: str = "data/test_dataset.json", alias: str = "melomane-text2sql"):
    """将本地测试数据集上传到 Confident AI 平台"""
    with open(path, "r", encoding="utf-8") as f:
        raw_dataset = json.load(f)

    goldens = []
    for item in raw_dataset:
        golden = Golden(
            input=item["question"],
            expected_output=item["sql"],
            additional_metadata={"id": item["id"], "category": item.get("category", "")},
        )
        goldens.append(golden)

    dataset = EvaluationDataset(goldens=goldens)
    dataset.push(alias=alias)
    logger.info(f"数据集已上传到 Confident AI，alias={alias}，共 {len(goldens)} 条")


def run_text2sql_pipeline(query: str) -> dict:
    """调用 Text2SQL 管道，返回中间结果用于评估"""
    import requests

    resp = requests.post(
        "http://localhost:8000/api/v1/app/text2sql/generate_sql",
        json={"query": query},
        timeout=120,
    )

    if resp.status_code == 200:
        data = resp.json()["data"]
        return {
            "sql": data["sql"],
            "schema_info": data.get("schema_info", ""),
            "similar_examples": data.get("similar_examples", []),
            "success": True,
        }
    else:
        detail = resp.json().get("detail", resp.text)
        return {
            "sql": "",
            "schema_info": "",
            "similar_examples": [],
            "success": False,
            "error": detail,
        }


def build_test_cases(dataset: list) -> list:
    """构建 DeepEval 测试用例"""
    test_cases = []
    results_log = []

    for i, item in enumerate(dataset):
        query = item["question"]
        expected_sql = item["sql"]
        logger.info(f"[{i+1}/{len(dataset)}] 测试: {query}")

        start = time.time()
        result = run_text2sql_pipeline(query)
        elapsed = time.time() - start

        actual_sql = result["sql"] if result["success"] else f"FAILED: {result.get('error', '')}"
        schema_context = result["schema_info"]
        examples = result["similar_examples"]

        # 构建检索上下文：schema + few-shot 示例
        retrieval_context = []
        if schema_context:
            retrieval_context.append(schema_context)
        for ex in examples:
            retrieval_context.append(
                f"问题: {ex.get('question', '')}\nSQL: {ex.get('sql', '')}"
            )

        test_case = LLMTestCase(
            input=query,
            actual_output=actual_sql,
            expected_output=expected_sql,
            retrieval_context=retrieval_context if retrieval_context else ["无检索上下文"],
        )
        test_cases.append(test_case)

        results_log.append({
            "id": item["id"],
            "question": query,
            "expected_sql": expected_sql,
            "actual_sql": actual_sql,
            "success": result["success"],
            "time": f"{elapsed:.2f}s",
            "category": item.get("category", ""),
        })

        logger.info(f"  耗时: {elapsed:.2f}s | 成功: {result['success']}")

    # 保存中间结果
    with open("data/eval_results_raw.json", "w", encoding="utf-8") as f:
        json.dump(results_log, f, ensure_ascii=False, indent=2)
    logger.info(f"原始结果已保存到 data/eval_results_raw.json")

    return test_cases


def run_evaluation(test_cases: list, judge_model, metric_count: int = 4, use_custom: bool = False):
    """运行 DeepEval 评估

    Args:
        metric_count: 2=核心指标(AR+F), 4=全部指标
        use_custom: 是否使用 Text2SQL 自定义指标替代通用 RAG 指标
    """
    if use_custom:
        metrics = [
            ExecutionAccuracyMetric(threshold=0.5),
            ValidSqlMetric(threshold=0.5),
            TableSelectionMetric(threshold=0.5),
        ]
    else:
        all_metrics = [
            AnswerRelevancyMetric(threshold=0.5, model=judge_model),
            FaithfulnessMetric(threshold=0.5, model=judge_model),
            ContextualRelevancyMetric(threshold=0.5, model=judge_model),
            ContextualPrecisionMetric(threshold=0.5, model=judge_model),
        ]
        metrics = all_metrics[:metric_count]

    logger.info(f"开始评估 {len(test_cases)} 个测试用例，使用 {len(metrics)} 个指标: {[m.__class__.__name__ for m in metrics]}")

    hyperparams = {
        "model": "qwen-max (Text2SQL LLM)",
        "embedding": "paraphrase-multilingual-MiniLM-L12-v2",
        "reranker": "BAAI/bge-reranker-base",
        "schema_chunking_top_k": 3,
        "example_retrieval_top_k": 10,
        "reranking_top_n": 3,
        "vector_db": "ChromaDB Cloud",
        "metric_type": "custom-text2sql" if use_custom else "deepeval-rag",
    }
    if not use_custom:
        hyperparams["judge_model"] = judge_model.get_model_name()

    results = evaluate(
        test_cases=test_cases,
        metrics=metrics,
        hyperparameters=hyperparams,
    )

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Text2SQL RAG 管道评估")
    parser.add_argument("--limit", type=int, default=5, help="测试用例数量限制（默认5）")
    parser.add_argument("--dataset", type=str, default="data/test_dataset.json", help="测试数据集路径")
    parser.add_argument("--metrics", type=int, default=4, choices=[2, 4], help="指标数量：2=核心(AR+F), 4=全部")
    parser.add_argument("--model", type=str, default="qwen-max", help="Judge 模型名称")
    parser.add_argument("--push-dataset", action="store_true", help="将数据集上传到 Confident AI 平台（不执行评估）")
    parser.add_argument("--custom", action="store_true", help="使用 Text2SQL 自定义指标（EX + ValidSQL + TableSelection）")
    args = parser.parse_args()

    if args.push_dataset:
        push_dataset_to_confident(args.dataset)
        exit(0)

    logger.info(f"加载测试数据集: {args.dataset}, limit={args.limit}")
    dataset = load_test_dataset(args.dataset, limit=args.limit)

    logger.info("构建测试用例（调用 Text2SQL 管道）...")
    test_cases = build_test_cases(dataset)

    logger.info(f"初始化评估 Judge 模型: {args.model}")
    judge = QwenEvalModel(model_name=args.model)

    logger.info("开始 DeepEval 评估...")
    results = run_evaluation(test_cases, judge, metric_count=args.metrics, use_custom=args.custom)

    logger.info("评估完成！")
