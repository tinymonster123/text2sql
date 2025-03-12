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
    DEEPSEEK = os.getenv("DEEPSEEK")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    API_KEY = os.getenv("API_KEY")
    BASE_URL = os.getenv("BASE_URL")
    BERT_MODEL_NAME = os.getenv(
        "BERT_MODEL_NAME", "paraphrase-multilingual-MiniLM-L12-v2"
    )
