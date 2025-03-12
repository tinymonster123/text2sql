# -*- coding: utf-8 -*-
import logging
from openai import OpenAI
from ..config import Config

logger = logging.getLogger(__name__)

# 示例查询
few_shot_example = [
    {
        "question": "查询数据中专辑的创建时间并且按照专辑的 id 排序返回结果",
        "sql": "SELECT album_date_created, album_id FROM raw_albums ORDER BY album_id;",
    },
    {
        "question": "查询数据库中的专辑标题并按照专辑的听众人数排序返回结果",
        "sql": "SELECT album_listens, album_title FROM raw_albums ORDER BY album_listens;",
    },
]


class Deepseek:
    """Deepseek API 封装类

    提供与 Deepseek API 交互的功能，用于生成 SQL 查询语句。
    """

    def __init__(self):
        """初始化 Deepseek API 客户端"""
        self.client = OpenAI(api_key=Config.API_KEY, base_url=Config.BASE_URL)
        self.system_prompt = """你是一个专业的SQL助手，擅长将自然语言转换为准确的SQL查询。
请根据提供的数据库架构信息，生成符合MySQL语法的SQL查询语句。
仅返回SQL代码，不要有任何额外的解释。
请确保生成的SQL语句遵循以下规则：
1. 使用正确的表名和字段名
2. 返回有意义的列（不要只返回id）
3. 正确处理排序和分组
4. 使用合适的WHERE条件"""
        self.few_shot_example = few_shot_example
        self.deepseek = Config.DEEPSEEK

    def generate_full_prompt(
        self, prompt: str, schema_info: str, few_shot_example=None
    ) -> str:
        """生成完整的提示信息

        Args:
            prompt: 用户的查询提示
            schema_info: 数据库架构信息
            few_shot_example: 示例查询列表（可选）

        Returns:
            str: 格式化后的完整提示文本

        Raises:
            ValueError: 当提示为空时抛出异常
        """
        if not prompt:
            raise ValueError("查询不能为空")

        few_shot_example = few_shot_example or self.few_shot_example

        # 构建提示文本
        full_prompt = f"数据库结构:\n{schema_info}\n\n"

        if few_shot_example:
            full_prompt += "示例:\n"
            for example in few_shot_example:
                full_prompt += f"问题:{example['question']}\nSQL:{example['sql']}\n\n"

        full_prompt += f"请为以下问题生成 SQL:\n{prompt}"

        logger.debug(f"生成的完整提示: {full_prompt[:200]}...")  # 记录前200个字符
        return full_prompt

    def get_response(self, prompt: str, schema_info: str) -> str:
        """获取 API 响应

        Args:
            prompt: 用户的查询提示
            schema_info: 数据库架构信息

        Returns:
            str: 生成的SQL语句

        Raises:
            Exception: API调用失败时抛出异常
        """
        try:
            full_prompt = self.generate_full_prompt(
                prompt, schema_info, self.few_shot_example
            )

            logger.info(f"发送到Deepseek的prompt前100个字符: {full_prompt[:100]}...")

            response = self.client.chat.completions.create(
                model=self.deepseek,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": full_prompt},
                ],
                max_tokens=1024,
                temperature=0.7,
                stream=False,
            )

            sql = response.choices[0].message.content
            logger.info(f"Deepseek返回的SQL: {sql}")
            return sql

        except Exception as e:
            logger.error(f"Deepseek API调用失败: {str(e)}")
            raise
