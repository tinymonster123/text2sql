import os
from dotenv import load_dotenv

load_dotenv()


class Config:
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
    CHROMA_API_KEY = os.getenv("CHROMA_API_KEY")
    CHROMA_TENANT = os.getenv("CHROMA_TENANT")
    CHROMA_DATABASE = os.getenv("CHROMA_DATABASE")
    CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "melomane_collection")

    # Re-ranker配置
    RERANKER_MODEL_NAME = os.getenv("RERANKER_MODEL_NAME", "BAAI/bge-reranker-base")

    # Schema向量集合配置
    SCHEMA_COLLECTION_NAME = os.getenv(
        "SCHEMA_COLLECTION_NAME", "melomane_schema_collection"
    )

    HF_ENDPOINT = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")
