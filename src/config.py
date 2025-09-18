import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SSH_HOST = os.getenv("SSH_HOST")
    SSH_USER = os.getenv("SSH_USER")
    SSH_KEY_PATH = os.getenv("SSH_KEY_PATH")
    DB_HOST = os.getenv("DB_HOST")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")

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

    # 兼容旧版本
    DEEPSEEK = os.getenv("DEEPSEEK")  # 保留兼容性
