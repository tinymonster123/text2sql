import os
import asyncio
import logging
import json
from typing import Any, Dict, List, Optional

import pandas as pd
import numpy as np
from datasets import Dataset
from dotenv import load_dotenv

os.environ["TOKENIZERS_PARALLELISM"] = "false"

from ragas import evaluate
from ragas.metrics import context_precision, DataCompyScore, LLMSQLEquivalence
from ragas.dataset_schema import SingleTurnSample
from ragas.llms.base import BaseRagasLLM
from ragas.embeddings.base import BaseRagasEmbeddings
from ragas.run_config import RunConfig
from ragas.metrics.base import MetricWithLLM, MetricWithEmbeddings

from langchain_openai import ChatOpenAI
from langchain_core.outputs import LLMResult, Generation
from langchain_core.prompt_values import PromptValue

from src.text_to_sql import Text2SQL
from src.config import Config
from src.database.connection import PostgreSQLConnection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()

if not os.getenv("API_KEY") or not os.getenv("BASE_URL"):
    logger.error("错误：请在 .env 文件中设置 API_KEY 和 BASE_URL 环境变量。")
    exit()
else:
    logger.info("API_KEY 和 BASE_URL 已设置。")


class CustomRagasLLM(BaseRagasLLM):
    """自定义的 Ragas LLM 适配器"""

    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=Config.API_KEY, base_url=Config.BASE_URL)
        self.model = Config.LLM_MODEL

    def generate_text(
        self,
        prompt: PromptValue,
        n: int = 1,
        temperature: float = 0.2,
        stop: Optional[List[str]] = None,
        callbacks=None,
    ) -> LLMResult:
        """生成文本的核心方法"""
        try:
            prompt_str = prompt.to_string()
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt_str}],
                max_tokens=1024,
                temperature=temperature,
                n=n,
                stop=stop,
            )

            generations = []
            for choice in response.choices:
                generations.append(Generation(text=choice.message.content))

            return LLMResult(generations=[generations])

        except Exception as e:
            logger.error(f"LLM 生成失败: {e}")
            raise

    async def agenerate_text(
        self,
        prompt: PromptValue,
        n: int = 1,
        temperature: float = 0.2,
        stop: Optional[List[str]] = None,
        callbacks=None,
    ) -> LLMResult:
        """异步生成文本"""
        return self.generate_text(prompt, n, temperature, stop, callbacks)


EVALUATION_DATASET = [
    {
        "question": "查询所有学院的名称",
        "expected_sql": 'SELECT "college_name" FROM "Colleges";',
        "table_names": ["Colleges"]
    },
    {
        "question": "查询所有教职工的信息",
        "expected_sql": 'SELECT * FROM "Staff";',
        "table_names": ["Staff"]
    },
]


async def run_evaluation():
    """运行评估测试"""
    logger.info("开始 Ragas 评估...")

    text2sql = Text2SQL()
    custom_llm = CustomRagasLLM()

    responses = []
    samples = []

    for item in EVALUATION_DATASET:
        question = item["question"]
        expected_sql = item["expected_sql"]

        logger.info(f"处理问题: {question}")

        result = text2sql.generate_sql(question)
        generated_sql = result.get("sql", "")
        schema_info = result.get("schema_info", "")

        responses.append({
            "question": question,
            "generated_sql": generated_sql,
            "expected_sql": expected_sql,
            "success": result.get("success", False)
        })

        sample = SingleTurnSample(
            user_input=question,
            response=generated_sql,
            reference=expected_sql,
            retrieved_contexts=[schema_info] if schema_info else []
        )
        samples.append(sample)

    dataset = Dataset.from_list([sample.to_dict() for sample in samples])

    metrics = [
        context_precision.with_llms([custom_llm]),
        DataCompyScore(),
        LLMSQLEquivalence().with_llms([custom_llm])
    ]

    results = evaluate(dataset, metrics)

    logger.info("评估完成！")
    logger.info(f"评估结果: {results}")

    return results, responses


if __name__ == "__main__":
    results, responses = asyncio.run(run_evaluation())

    with open("evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump(responses, f, ensure_ascii=False, indent=2)

    logger.info("评估结果已保存到 evaluation_results.json")