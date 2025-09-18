import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # 环境配置
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")  # development 或 production

    # 数据库配置
    USER_DATABASE_URL = os.getenv("USER_DATABASE_URL")  # 用户认证数据库
    MUSIC_DATABASE_URL = os.getenv("MUSIC_DATABASE_URL")  # 音乐数据库

    # LLM配置
    API_KEY = os.getenv("API_KEY")
    BASE_URL = os.getenv("BASE_URL")
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen3-max-preview")

    # BERT嵌入模型配置
    BERT_MODEL_NAME = os.getenv(
        "BERT_MODEL_NAME", "paraphrase-multilingual-MiniLM-L12-v2"
    )

    # ChromaDB配置
    CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
    CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
    CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "text2sql_collection")
