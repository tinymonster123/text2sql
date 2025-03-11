from openai import OpenAI
from ..config import Config

few_shot_example = [
    {
        "question": "查询数据中专辑的创建时间并且按照专辑的 id 排序返回结果",
        "sql": "SELECT album_date_created, album_id FROM raw_albums  ORDER BY album_id;",
    },
    {
        "question": "查询数据库中的专辑标题并按照专辑的听众人数排序返回结果",
        "sql": "SELECT album_listens, album_title FROM raw_albums ORDER BY album_listens;",
    },
]


class Deepseek:
    def __init__(self):
        self.client = OpenAI(api_key=Config.API_KEY, base_url=Config.BASE_URL)
        self.system_prompt = """你是一个专业的SQL助手，擅长将自然语言转换为准确的SQL查询。
请根据提供的数据库架构信息，生成符合MySQL语法的SQL查询语句。
仅返回SQL代码，不要有任何额外的解释。"""
        self.few_shot_example = few_shot_example

    def generate_full_prompt(self, prompt, schema_info, few_shot_example=None):
        if not prompt:
            raise ValueError("查询不能为空")

        few_shot_example = few_shot_example or self.few_shot_example

        full_prompt = f"数据库结构:\n{schema_info}\n\n"

        if few_shot_example:
            full_prompt += f"示例:\n"
            for example in few_shot_example:
                full_prompt += f"问题:{example['question']}\nSQL:{example['sql']}\n\n"

        full_prompt += f"请为以下问题生成 SQL:\n{prompt}"

        return full_prompt

    def get_response(self, prompt, schema_info):
        try:
            full_prompt = self.generate_full_prompt(
                prompt, schema_info, self.few_shot_example
            )
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": full_prompt},
                ],
                max_tokens=1024,
                temperature=0.7,
                stream=False,
            )

            return response.choices[0].message.content
        except Exception as e:
            raise e
