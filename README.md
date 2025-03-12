# Text2SQL

基于 deepseek 和 BERT 实现的 text to sql 

```shell
.
├── README.md
├── data
├── requirements.txt
└── src
    ├── app.py
    ├── config.py
    ├── database
    │   ├── __init__.py
    │   ├── connection.py
    │   ├── connection_local.py
    │   ├── schema_manager.py
    │   └── sql_validator.py
    ├── llm
    │   ├── __init__.py
    │   └── deepseek.py
    ├── main.py
    ├── rag
    │   ├── __init__.py
    │   ├── embedding
    │   │   ├── __init__.py
    │   │   └── bert_embedding_model.py
    │   └── vectordb
    │       ├── __init__.py
    │       └── vector_store.py
    └── text_to_sql.py
```

连接数据库有两种方式一种是 ssh 隧道连接，一种是本地连接。分别位于**connection.py**和**connection_local.py**中，项目默认使用 ssh 连接如有需求请自行修改。