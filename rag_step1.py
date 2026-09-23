#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rag_step1.py - 艺术学概论 RAG 检索脚本
"""

import os
import sys
import json
from docx import Document
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions

# ============================================================
# 1. 核心逻辑封装（避免重复造轮子）
# ============================================================
def load_docx(file_path):
    """读取 Word 文档"""
    doc = Document(file_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return paragraphs

def init_rag_system():
    """初始化模型和数据库（只执行一次）"""
    print("🚀 正在加载模型和数据库...")
    model = SentenceTransformer('./model_cache')
    client = chromadb.PersistentClient(path="./chroma_db_real")
    bge_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="./model_cache")
    collection = client.get_or_create_collection(
        name="art_history_real",
        embedding_function=bge_ef
    )
    return model, collection

def index_documents(collection, doc_path="艺术学概论.docx"):
    """将文档入库（仅当需要更新知识库时调用）"""
    if not os.path.exists(doc_path):
        print(f"❌ 找不到文件 {doc_path}")
        return
    paragraphs = load_docx(doc_path)
    print(f"📥 正在将 {len(paragraphs)} 个段落存入向量数据库...")
    ids = [str(i) for i in range(len(paragraphs))]
    metadatas = [{"source": "《艺术学概论》"} for _ in paragraphs]
    collection.add(ids=ids, documents=paragraphs, metadatas=metadatas)
    print(f"✅ 真实文档入库完成！")

# ============================================================
# 2. 供 server.py 调用的检索接口
# ============================================================
# 在模块级别初始化一次，后续所有请求共享，速度极快！
model, collection = init_rag_system()

def search_rag(query_text):
    """执行检索，直接返回 Python 字典"""
    try:
        query_embedding = model.encode([query_text]).tolist()
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=3,
            include=["documents", "metadatas"]
        )
        return {"results": results}
    except Exception as e:
        return {"error": str(e), "results": []}

# ============================================================
# 3. 命令行独立运行入口
# ============================================================
if __name__ == "__main__":
    # 如果是命令行运行，先执行一次入库（或者你可以注释掉这行，只保留检索）
    index_documents(collection) 
    
    if len(sys.argv) > 1:
        user_question = sys.argv[1]
        results = search_rag(user_question)
        print(json.dumps(results, ensure_ascii=False))  # 注意这里修正了变量名
