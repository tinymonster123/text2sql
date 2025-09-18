import logging
from openai import OpenAI
from ..config import Config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个专业的SQL助手，你的唯一任务是将自然语言转换为准确的PostgreSQL查询。

**至关重要的规则：**
数据库中的所有表名和列名都区分大小写。因此，任何包含大写字母的标识符（如 "Colleges", "Staff", "student_count"）都 **必须** 使用双引号（""）括起来。这是一个绝对的要求，否则查询将失败。

例如，查询 "Staff" 表必须写成 `SELECT * FROM "Staff";`，而不是 `SELECT * FROM Staff;`。

请根据提供的数据库架构信息，严格遵守以上规则，生成SQL查询。仅返回SQL代码，不要有任何额外的解释。"""

FEW_SHOT_EXAMPLES = [
    {
        "question": "查询所有学院的名称",
        "sql": 'SELECT "college_name" FROM "Colleges";',
    },
    {
        "question": "查询所有员工的姓名和他们所属的学院ID",
        "sql": 'SELECT "staff_name", "college_id" FROM "Staff";',
    },
]


class LLM:
    """LLM API 封装类

    提供与 LLM API 交互的功能，用于生成 SQL 查询语句。
    """

    def __init__(self):
        """初始化 LLM API 客户端"""
        self.client = OpenAI(api_key=Config.API_KEY, base_url=Config.BASE_URL)
        self.system_prompt = SYSTEM_PROMPT
        self.few_shot_example = FEW_SHOT_EXAMPLES
        self.model = Config.LLM_MODEL

    def generate_full_prompt(
        self,
        prompt: str,
        schema_info: str,
        few_shot_example=None,
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

        full_prompt = f"数据库结构:\n{schema_info}\n\n"

        if few_shot_example:
            full_prompt += "示例:\n"
            for example in few_shot_example:
                full_prompt += f"问题:{example['question']}\nSQL:{example['sql']}\n\n"

        full_prompt += f"请为以下问题生成 SQL:\n{prompt}"

        logger.debug(f"生成的完整提示: {full_prompt[:200]}...")
        return full_prompt

    def get_response(self, prompt: str, schema_info: str, few_shot_example: list = None) -> str:
        """获取 API 响应

        Args:
            prompt: 用户的查询提示
            schema_info: 数据库架构信息
            few_shot_example: 动态 few-shot 示例

        Returns:
            str: 生成的SQL语句

        Raises:
            Exception: API调用失败时抛出异常
        """
        try:
            full_prompt = self.generate_full_prompt(
                prompt, schema_info, few_shot_example
            )

            logger.info(f"发送到LLM的prompt前100个字符: {full_prompt[:100]}...")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": full_prompt},
                ],
                max_tokens=1024,
                temperature=0.7,
                stream=False,
            )

            sql = response.choices[0].message.content
            logger.info(f"LLM返回的SQL: {sql}")
            return sql

        except Exception as e:
            logger.error(f"LLM API调用失败: {str(e)}")
            raise