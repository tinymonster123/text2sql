from typing import Dict, Any, List
import logging
from .base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI兼容的LLM提供商

    支持OpenAI、DeepSeek、Qwen等OpenAI兼容的API
    """

    def __init__(self):
        super().__init__("openai")
        self.client = None
        self.model = None
        self.api_key = None
        self.base_url = None

    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化OpenAI提供商"""
        try:
            from openai import OpenAI

            self.api_key = config.get("api_key")
            self.base_url = config.get("base_url", "https://api.openai.com/v1")
            self.model = config.get("model", "gpt-3.5-turbo")

            if not self.api_key:
                raise ValueError("API key is required")

            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )

            # 测试连接
            self.client.models.list()

            self.is_initialized = True
            logger.info(f"OpenAI提供商初始化成功: {self.base_url}")
            return True

        except Exception as e:
            logger.error(f"OpenAI提供商初始化失败: {e}")
            return False

    def generate_sql(self, input_data: Dict[str, Any]) -> str:
        """生成SQL查询"""
        if not self.is_initialized:
            raise RuntimeError("Provider not initialized")

        query = input_data.get("query", "")
        schema = input_data.get("schema", "")
        examples = input_data.get("examples", [])

        # 构建提示词
        prompt = self._build_sql_prompt(query, schema, examples)

        messages = [
            {"role": "system", "content": "你是一个专业的SQL查询生成器。请根据用户的自然语言查询和数据库结构，生成准确的SQL语句。"},
            {"role": "user", "content": prompt}
        ]

        return self.generate_response(messages)

    def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """生成通用响应"""
        if not self.is_initialized:
            raise RuntimeError("Provider not initialized")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                max_tokens=1000
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"生成响应失败: {e}")
            raise

    def _build_sql_prompt(self, query: str, schema: str, examples: List[Dict]) -> str:
        """构建SQL生成提示词"""
        prompt = f"""请根据以下信息生成SQL查询：

数据库结构：
{schema}

用户查询：{query}

"""

        if examples:
            prompt += "参考示例：\n"
            for i, example in enumerate(examples[:3], 1):
                prompt += f"{i}. 查询：{example.get('question', '')}\n"
                prompt += f"   SQL：{example.get('sql', '')}\n"

        prompt += "\n请只返回SQL语句，不要包含其他解释。"

        return prompt

    def get_info(self) -> Dict[str, Any]:
        """获取提供商信息"""
        info = super().get_info()
        info.update({
            "model": self.model,
            "base_url": self.base_url,
            "api_type": "openai_compatible"
        })
        return info