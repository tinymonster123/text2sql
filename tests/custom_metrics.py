# -*- coding: utf-8 -*-
"""
Text2SQL 专用自定义评估指标

针对 Text2SQL 场景设计的细粒度指标，弥补通用 RAG 指标的盲区：
- ExecutionAccuracyMetric (EX): 执行两条 SQL，比较结果集是否一致
- ValidSqlMetric: 生成的 SQL 能否成功执行
- TableSelectionMetric: Schema Chunking 选的表是否覆盖了 SQL 所需的表
"""

import logging
import re
from typing import List, Optional, Set

import psycopg2
from psycopg2.extras import RealDictCursor
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

from src.core.config import Config

logger = logging.getLogger(__name__)


def _execute_sql(sql: str, limit: int = 50) -> Optional[List[dict]]:
    """执行 SQL 并返回结果集（字典列表），失败返回 None"""
    try:
        sql = sql.strip().rstrip(";")
        # 如果没有 LIMIT，加一个防止结果集过大
        if not re.search(r"\bLIMIT\s+\d+", sql, re.IGNORECASE):
            sql = f"{sql} LIMIT {limit}"
        sql += ";"

        with psycopg2.connect(Config.MUSIC_DATABASE_URL) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql)
                rows = cur.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        logger.debug(f"SQL 执行失败: {e}")
        return None


def _extract_table_names(sql: str) -> Set[str]:
    """从 SQL 中提取引用的表名"""
    # 匹配 FROM/JOIN 后面的表名（带引号或不带引号）
    pattern = r'(?:FROM|JOIN)\s+(?:"([^"]+)"|(\w+))'
    matches = re.findall(pattern, sql, re.IGNORECASE)
    tables = set()
    for quoted, unquoted in matches:
        name = quoted or unquoted
        # 排除子查询别名等
        if name.upper() not in ("SELECT", "WHERE", "ON", "AND", "OR"):
            tables.add(name.lower())
    return tables


class ExecutionAccuracyMetric(BaseMetric):
    """执行准确率 (EX)

    Text2SQL 的核心指标（参考 Spider/BIRD 基准）：
    分别执行 actual_output 和 expected_output，比较结果集。

    比较策略（BIRD 风格）：
    - 忽略列名/别名差异
    - 忽略行顺序
    - SELECT * 场景做列子集匹配

    评分规则：
    - 1.0: 结果集语义一致（值匹配）
    - 0.5: actual SQL 可执行但结果不一致
    - 0.0: actual SQL 执行失败
    """

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        self.score = None
        self.reason = None
        self.success = None
        self.error = None

    def measure(self, test_case: LLMTestCase) -> float:
        actual_sql = test_case.actual_output
        expected_sql = test_case.expected_output

        # 执行 actual SQL
        actual_results = _execute_sql(actual_sql)
        if actual_results is None:
            self.score = 0.0
            self.reason = f"生成的 SQL 执行失败: {actual_sql}"
            self.success = False
            return self.score

        # 执行 expected SQL
        expected_results = _execute_sql(expected_sql)
        if expected_results is None:
            # expected SQL 也执行失败，只能判断 actual 是否可执行
            self.score = 0.5
            self.reason = "期望 SQL 也执行失败，无法对比结果集；生成的 SQL 可执行"
            self.success = self.score >= self.threshold
            return self.score

        # 比较结果集
        if _results_match(actual_results, expected_results):
            self.score = 1.0
            self.reason = f"结果集完全一致 ({len(actual_results)} 行)"
        else:
            self.score = 0.5
            self.reason = (
                f"SQL 可执行但结果不一致: "
                f"actual={len(actual_results)} 行, expected={len(expected_results)} 行"
            )

        self.success = self.score >= self.threshold
        return self.score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        if self.error is not None:
            self.success = False
        else:
            try:
                self.success = self.score >= self.threshold
            except TypeError:
                self.success = False
        return self.success

    @property
    def __name__(self):
        return "Execution Accuracy (EX)"


class ValidSqlMetric(BaseMetric):
    """SQL 有效性指标

    检查生成的 SQL 能否成功执行。比通用 Faithfulness 更直接：
    不关心 SQL 是否"忠于上下文"，只关心它是否是有效的 SQL。

    评分：1.0 = 可执行, 0.0 = 执行失败
    """

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        self.score = None
        self.reason = None
        self.success = None
        self.error = None

    def measure(self, test_case: LLMTestCase) -> float:
        actual_sql = test_case.actual_output

        if not actual_sql or actual_sql.startswith("FAILED:"):
            self.score = 0.0
            self.reason = f"未生成有效 SQL: {actual_sql[:100]}"
            self.success = False
            return self.score

        results = _execute_sql(actual_sql)
        if results is not None:
            self.score = 1.0
            self.reason = f"SQL 执行成功，返回 {len(results)} 行"
        else:
            self.score = 0.0
            self.reason = f"SQL 执行失败: {actual_sql[:200]}"

        self.success = self.score >= self.threshold
        return self.score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        if self.error is not None:
            self.success = False
        else:
            try:
                self.success = self.score >= self.threshold
            except TypeError:
                self.success = False
        return self.success

    @property
    def __name__(self):
        return "Valid SQL Rate"


class TableSelectionMetric(BaseMetric):
    """表选择准确率

    评估 Schema Chunking 检索到的表是否覆盖了 SQL 实际需要的表。
    从 retrieval_context (schema 文本) 中提取表名，
    与 expected_output (SQL) 中引用的表名对比。

    评分 = 覆盖的表数 / SQL 需要的表数
    """

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        self.score = None
        self.reason = None
        self.success = None
        self.error = None

    def measure(self, test_case: LLMTestCase) -> float:
        expected_sql = test_case.expected_output
        retrieval_context = test_case.retrieval_context or []

        # 从 expected SQL 提取需要的表名
        needed_tables = _extract_table_names(expected_sql)
        if not needed_tables:
            self.score = 1.0
            self.reason = "无法从期望 SQL 中提取表名，跳过"
            self.success = True
            return self.score

        # 从 retrieval_context 中提取 schema 包含的表名
        retrieved_tables = set()
        for ctx in retrieval_context:
            # 匹配 "表：table_name" 格式
            for match in re.findall(r"表[：:]\s*(\w+)", ctx):
                retrieved_tables.add(match.lower())

        if not retrieved_tables:
            self.score = 0.0
            self.reason = f"未从检索上下文中提取到表名，需要: {needed_tables}"
            self.success = False
            return self.score

        # 计算覆盖率
        covered = needed_tables & retrieved_tables
        self.score = len(covered) / len(needed_tables)
        missing = needed_tables - retrieved_tables
        self.reason = (
            f"需要: {needed_tables}, 检索到: {retrieved_tables}, "
            f"覆盖: {covered}"
            + (f", 缺失: {missing}" if missing else "")
        )

        self.success = self.score >= self.threshold
        return self.score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        if self.error is not None:
            self.success = False
        else:
            try:
                self.success = self.score >= self.threshold
            except TypeError:
                self.success = False
        return self.success

    @property
    def __name__(self):
        return "Table Selection Accuracy"


def _results_match(actual: List[dict], expected: List[dict]) -> bool:
    """比较两个结果集是否语义一致（BIRD 风格）

    参考 BIRD 基准的评估策略：对值做集合比较，
    忽略列名/别名、列顺序、行顺序。

    策略优先级：
    1. 行数必须一致
    2. 列数相同 → 按行比较值元组（忽略列名，按值排序）
    3. actual 列 > expected 列（SELECT * 场景）→ 列名子集匹配
    4. 以上均失败 → BIRD 风格全值集合比较（完全忽略列归属）
    """
    if len(actual) != len(expected):
        return False

    if not actual:
        return True

    def normalize_value(v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        return str(v).strip().lower()

    # --- 策略 1：列数相同时，按值排序比较（忽略列名/别名） ---
    actual_cols = len(actual[0])
    expected_cols = len(expected[0])

    def _sort_key(x):
        return (x is None, str(x))

    def _tuple_sort_key(t):
        return tuple(_sort_key(x) for x in t)

    if actual_cols == expected_cols:
        def row_values_sorted(row: dict) -> tuple:
            return tuple(sorted((normalize_value(v) for v in row.values()), key=_sort_key))

        actual_rows = sorted((row_values_sorted(r) for r in actual), key=_tuple_sort_key)
        expected_rows = sorted((row_values_sorted(r) for r in expected), key=_tuple_sort_key)
        if actual_rows == expected_rows:
            return True

    # --- 策略 2：SELECT * 场景，expected 列名在 actual 中做子集匹配 ---
    if actual_cols > expected_cols:
        exp_keys = list(expected[0].keys())
        # 精确列名匹配
        if all(k in actual[0] for k in exp_keys):
            subset_actual = sorted(
                (tuple(normalize_value(r[k]) for k in exp_keys) for r in actual),
                key=_tuple_sort_key,
            )
            subset_expected = sorted(
                (tuple(normalize_value(r[k]) for k in exp_keys) for r in expected),
                key=_tuple_sort_key,
            )
            if subset_actual == subset_expected:
                return True

    # --- 策略 3：BIRD 风格全值集合比较（忽略列归属） ---
    # 将每行的所有值收集为 sorted tuple，再跨行排序比较
    def row_to_value_bag(row: dict) -> tuple:
        return tuple(sorted(
            (normalize_value(v) for v in row.values()),
            key=lambda x: (x is None, str(x))
        ))

    actual_bags = sorted((row_to_value_bag(r) for r in actual), key=_tuple_sort_key)
    expected_bags = sorted((row_to_value_bag(r) for r in expected), key=_tuple_sort_key)
    if actual_bags == expected_bags:
        return True

    return False
