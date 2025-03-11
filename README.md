# Text2SQL

基于 deepseek 和 word2vec

```shell
text2sql/
├── .env                    # 环境变量配置
├── .gitignore              # Git忽略文件
├── README.md               # 项目说明文档
├── requirements.txt        # 项目依赖
├── src/
│   ├── api.py              # API服务
│   ├── config.py           # 配置模块
│   ├── main.py             # 入口文件
│   ├── text2sql_service.py # 核心服务
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py   # 数据库连接
│   │   ├── schema_manager.py  # 数据库元信息管理
│   │   └── sql_validator.py   # SQL验证
│   ├── llm/
│   │   ├── __init__.py
│   │   └── deepseek.py     # DeepSeek LLM接口
│   └── rag/
│       ├── __init__.py
│       ├── embedding/
│       │   ├── __init__.py
│       │   └── word2vec.py     # Word2Vec实现
│       └── vectordb/
│           ├── __init__.py
│           └── vector_store.py   # 向量存储实现
├── data/                   # 数据目录(自动创建)
│   ├── schema_cache.json   # 数据库结构缓存
│   └── vector_store.pkl    # 向量存储缓存
└── models/                 # 模型目录(自动创建)
    └── word2vec.model      # 训练好的Word2Vec模型
```
