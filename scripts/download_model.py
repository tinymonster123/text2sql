#!/usr/bin/env python3
"""
模型下载脚本

预下载必要的AI模型以提高启动速度
"""

import os
import sys
from pathlib import Path
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_sentence_transformer():
    """下载句子转换器模型"""
    try:
        logger.info("🔽 开始下载sentence-transformers模型...")
        from sentence_transformers import SentenceTransformer

        # 下载常用的中英文模型
        models = [
            "all-MiniLM-L6-v2",  # 英文通用模型
            "paraphrase-multilingual-MiniLM-L12-v2"  # 多语言模型
        ]

        for model_name in models:
            try:
                logger.info(f"📦 正在下载模型: {model_name}")
                model = SentenceTransformer(model_name)
                logger.info(f"✅ 模型 {model_name} 下载完成")
            except Exception as e:
                logger.warning(f"⚠️ 模型 {model_name} 下载失败: {e}")

    except ImportError:
        logger.warning("sentence-transformers未安装，跳过模型下载")
    except Exception as e:
        logger.error(f"❌ 下载sentence-transformers模型失败: {e}")


def download_nltk_data():
    """下载NLTK数据"""
    try:
        logger.info("🔽 开始下载NLTK数据...")
        import nltk

        # 下载必要的NLTK数据
        data_packages = [
            'punkt',
            'stopwords',
            'wordnet'
        ]

        for package in data_packages:
            try:
                logger.info(f"📦 正在下载NLTK数据: {package}")
                nltk.download(package, quiet=True)
                logger.info(f"✅ NLTK数据 {package} 下载完成")
            except Exception as e:
                logger.warning(f"⚠️ NLTK数据 {package} 下载失败: {e}")

    except ImportError:
        logger.warning("NLTK未安装，跳过数据下载")
    except Exception as e:
        logger.error(f"❌ 下载NLTK数据失败: {e}")


def main():
    """主函数"""
    logger.info("🚀 开始预下载模型和数据...")

    try:
        # 设置缓存目录
        cache_dir = os.getenv("HF_HOME", "/app/huggingface_cache")
        os.makedirs(cache_dir, exist_ok=True)

        # 下载模型
        download_sentence_transformer()
        download_nltk_data()

        logger.info("✅ 模型和数据预下载完成")

    except Exception as e:
        logger.error(f"❌ 模型下载过程中出现错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()