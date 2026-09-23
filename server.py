#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ArtMind - 艺术学习AI助手 (纯开源版)
完全适配前端 app.js 的所有 API 调用
RAG 知识库检索已集成
"""

import os
import sys
import json
import uuid
import base64
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import subprocess
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
# 确保能导入同目录下的 rag_step1
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rag_step1 import search_rag
load_dotenv()

# ============================================================
# 配置
# ============================================================

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_FOLDER, exist_ok=True)

CONVERSATIONS_FILE = os.path.join(DATA_FOLDER, 'conversations.json')
RELATION_GRAPH_FILE = os.path.join(DATA_FOLDER, 'relation_graph.json')

# AI 配置
API_KEY = os.environ.get('API_KEY', '')
API_BASE_URL = os.environ.get('API_BASE_URL', '')
MODEL_NAME = os.environ.get('MODEL_NAME', 'qwen-vl-plus')

USE_MOCK = not API_KEY

if not USE_MOCK:
    client = OpenAI(
        api_key=API_KEY,
        base_url=API_BASE_URL,
        timeout=60,
        max_retries=2,
    )
else:
    client = None

# ============================================================
# 系统提示词
# ============================================================
SYSTEM_PROMPTS = {
    'read': """你是ArtMind"艺境"智能艺术史学习助手，水平不亚于艺术史学教授，专注于作品赏析。当前处于「阅画」模式。
请对用户提供的画作进行详细分析，包括：
1. 基本介绍（作者、年代、尺寸、材质、现藏地）
2. 构图分析（布局、视觉引导、比例）
3. 笔触与技法（用笔、色彩、明暗、质感）
4. 母题解读（象征元素、隐喻）
5. 历史语境（时代背景、艺术流派）
6. 艺术价值（地位、影响）
回答要通俗易懂，同时适当使用专业术语并解释。末尾可提出2-3个思考问题。""",
    'think': """你是ArtMind"艺境"智能艺术史学习助手，水平不亚于一位善于启发的艺术导师。当前处于「思画」模式。
请针对之前讲解的内容向学生提问，检验理解程度。问题应涉及：
1. 构图与空间处理
2. 色彩与笔触技巧
3. 母题与象征意义
4. 历史与风格比较
提问要循序渐进，由浅入深。先提一个具体问题，等学生回答后再继续。""",
    'research': """你是ArtMind"艺境"智能艺术史学习助手，水平不亚于一位艺术史研究学者。当前处于「研画」模式。
请进行深度学术探讨，包括：
1. 历史纵深（更广阔的时代脉络）
2. 思想解读（哲学、美学观念）
3. 学术争议（不同学派的解读）
4. 跨学科视角（社会学、心理学等）
5. 研究前沿（最新成果）
鼓励思辨，引导学生形成独立学术观点。"""
}

# ============================================================
# 数据持久化
# ============================================================
def load_json(filepath, default=None):
    if default is None:
        default = {}
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_conversations():
    return load_json(CONVERSATIONS_FILE, {})

def save_conversations(data):
    save_json(CONVERSATIONS_FILE, data)

def load_relation_graph():
    return load_json(RELATION_GRAPH_FILE, {"nodes": [], "edges": []})

def save_relation_graph(data):
    save_json(RELATION_GRAPH_FILE, data)

# ============================================================
# 模拟响应
# ============================================================
def generate_mock_response(user_text, mode):
    if mode == 'read':
        return """## 🎨 阅画模式 — 模拟作品赏析

感谢您的提问！由于未配置 API Key，我为您提供模拟的艺术解析。

**构图分析**  
经典作品常采用三角形或黄金分割构图，画面稳定而富有张力。主体物位于视觉中心，引导视线自然聚焦。

**笔触与色彩**  
画家运用细腻的笔触和温暖的色调，营造出深邃的空间感和情感氛围。

**母题与象征**  
画面中的元素往往承载丰富的象征意义，如光线代表灵感，花朵隐喻短暂的生命。

**历史语境**  
这件作品诞生于特定时代，反映了当时的社会审美和文化思潮。

**思考问题**  
1. 您认为画家最想表达的是什么？
2. 如果您来创作，会如何改变构图？  
（配置 API Key 即可获得真实 AI 解析）"""
    elif mode == 'think':
        return """## 💭 思画模式 — 模拟提问

很好！让我们检验一下您的理解。

**问题 1**：请描述画面中最吸引您注意力的部分，并说明画家用了什么技法让它突出？

请先思考一下再回答，我期待您的见解！"""
    elif mode == 'research':
        return """## 🔬 研画模式 — 模拟深度探讨

让我们深入历史语境和思想内涵。

**历史纵深**  
这件作品创作于社会转型期，艺术风格反映了当时政治、宗教和哲学思潮的碰撞。

**学术观点**  
不同学者对此作有不同解读：形式主义者看重视觉构成，文化研究者关注其社会隐喻。

**讨论**  
您认为在当代视角下，这件作品的意义是否发生了变化？为什么？

欢迎分享您的见解！"""
    else:
        return "您好！我是 ArtMind 艺术助手。请选择阅画、思画或研画模式开始学习。"

# ============================================================
# 生成选项（供前端使用）
# ============================================================
def get_options(mode):
    options_map = {
        'read': ['深入了解构图技巧', '探索色彩运用', '了解创作背景'],
        'think': ['我想思考更多', '请给我提示', '我想分享我的看法'],
        'research': ['讨论历史影响', '分析艺术价值', '对比其他作品']
    }
    return options_map.get(mode, [])

# ============================================================
# API 路由
# ============================================================

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'mode': 'mock' if USE_MOCK else 'real',
        'model': MODEL_NAME
    })

# ---------- 核心聊天接口 ----------
@app.route('/api/chat', methods=['POST'])
def chat():
    # 1. 获取前端传来的消息和模式
    user_message = request.json.get('message')
    mode = request.json.get('mode', 'read')

    # 2. 检查消息是否为空
    if not user_message:
        return jsonify({'success': False, 'error': '消息不能为空'}), 400

    # ==========================================
    # 【RAG 检索】调用 rag_step1.py 检索知识库
    # ==========================================
        # ==========================================
    # 【RAG 检索】直接调用函数，无需 subprocess
    # ==========================================
    rag_context = ""
    try:
        print(f"🔍 正在检索: {user_message}")
        rag_data = search_rag(user_message)
                # 强制转换：如果 rag_data 是字符串，就把它变成字典！
        if isinstance(rag_data, str):
            rag_data = json.loads(rag_data)
        if "error" in rag_data:
            print(f"❌ RAG 内部错误: {rag_data['error']}")
            raise Exception(rag_data['error'])
        if rag_data.get("results"):
            # 提取 ChromaDB 返回的二维列表中的第一段（documents[0]）
            docs = rag_data["results"].get("documents", [[]])[0]
            # 将段落拼接成字符串
            rag_context = "\n\n".join(docs)
            print(f"✅ RAG 检索成功，找到 {len(docs)} 段相关内容")
        else:
            print("⚠️ RAG 未找到相关内容")
    except Exception as e:
        print(f"❌ RAG 调用失败: {e}")
        rag_context = "未检索到相关背景知识。"
    # ==========================================
    # 【RAG 检索结束】
    # ==========================================
    # ==========================================
    # 【RAG 检索结束】
    # ==========================================

    # ==========================================
    # 【构建 System Prompt】结合模式 + RAG 上下文
    # ==========================================
    base_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS['read'])
    if rag_context:
        system_prompt = f"""{base_prompt}

【参考背景】（来自知识库《艺术学概论》，请优先基于以下内容回答）：
{rag_context}"""
    else:
        system_prompt = base_prompt
    # ==========================================
    # 【System Prompt 构建结束】
    # ==========================================

    # 3. 调用大模型
    if not USE_MOCK and client:
            # 如果RAG检索到了内容，就把它拼到用户消息里
        if rag_context:
            user_message_with_context = (
                f"以下是从《艺术学概论》中检索到的相关参考资料：\n\n"
                f"{rag_context}\n\n"
                f"---\n"
                f"请严格基于以上参考资料回答用户的问题，并在回答中明确标注内容出自哪个章节。"
                f"如果参考资料中没有相关信息，请如实告知。\n\n"
                f"用户的问题：{user_message}"
            )
        else:
            user_message_with_context = user_message

        print("\n" + "="*60)
        print(f"📋 发送给大模型的 user_message 前200字:")
        print(user_message_with_context[:200])
        print(f"\n📋 完整长度: {len(user_message_with_context)} 字符")
        print("="*60 + "\n")
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message_with_context}
            ]
        )
        reply = response.choices[0].message.content
    else:
        reply = generate_mock_response(user_message, mode)

    # 4. 返回结果给前端
    return jsonify({'success': True, 'reply': reply})

# ---------- 对话管理 ----------
@app.route('/api/conversations', methods=['GET'])
def list_conversations():
    convs = load_conversations()
    conv_list = []
    for cid, chat in convs.items():
        conv_list.append({
            'id': cid,
            'title': chat.get('title', '未命名对话'),
            'preview': chat.get('preview', ''),
            'time': chat.get('time', ''),
            'messages': chat.get('messages', [])
        })
    conv_list.sort(key=lambda x: x.get('time', ''), reverse=True)
    return jsonify({'conversations': conv_list})

@app.route('/api/conversations', methods=['POST'])
def create_conversation():
    data = request.get_json() or {}
    chat_id = 'chat_' + str(uuid.uuid4().hex)[:8]
    now = datetime.now().strftime('%Y-%m-%d')
    new_chat = {
        'id': chat_id,
        'title': data.get('title', '新对话'),
        'preview': data.get('preview', '开始新的艺术探索...'),
        'time': now,
        'messages': [],
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }
    convs = load_conversations()
    convs[chat_id] = new_chat
    save_conversations(convs)
    return jsonify({'conversation': new_chat})

@app.route('/api/conversations/<chat_id>', methods=['GET'])
def get_conversation(chat_id):
    convs = load_conversations()
    if chat_id not in convs:
        return jsonify({'error': '对话不存在'}), 404
    return jsonify({'conversation': convs[chat_id]})

@app.route('/api/conversations/<chat_id>', methods=['PUT'])
def update_conversation(chat_id):
    convs = load_conversations()
    if chat_id not in convs:
        return jsonify({'error': '对话不存在'}), 404
    data = request.get_json() or {}
    chat = convs[chat_id]
    if 'title' in data:
        chat['title'] = data['title']
    if 'preview' in data:
        chat['preview'] = data['preview']
    if 'messages' in data:
        chat['messages'] = data['messages']
    if 'time' in data:
        chat['time'] = data['time']
    chat['updated_at'] = datetime.now().isoformat()
    save_conversations(convs)
    return jsonify({'conversation': chat})

@app.route('/api/conversations/<chat_id>', methods=['DELETE'])
def delete_conversation(chat_id):
    convs = load_conversations()
    if chat_id in convs:
        del convs[chat_id]
        save_conversations(convs)
    return jsonify({'status': 'deleted'})

# ---------- 搜索 ----------
@app.route('/api/conversations/search', methods=['GET'])
def search_conversations():
    query = request.args.get('q', '').lower()
    convs = load_conversations()
    results = []
    for cid, chat in convs.items():
        title_match = query in chat.get('title', '').lower()
        preview_match = query in chat.get('preview', '').lower()
        if title_match or preview_match:
            results.append({
                'conversation_id': cid,
                'title': chat.get('title', ''),
                'matches': [],
                'match_type': 'title' if title_match else 'content'
            })
    return jsonify({'results': results, 'query': query})

# ---------- 关系网 ----------
@app.route('/api/relation-graph', methods=['GET'])
def get_relation_graph():
    graph = load_relation_graph()
    return jsonify(graph)

@app.route('/api/relation-graph/nodes', methods=['POST'])
def add_relation_node():
    data = request.get_json() or {}
    graph = load_relation_graph()
    node = {
        'id': str(uuid.uuid4()),
        'name': data.get('name', ''),
        'type': data.get('type', 'artist'),
        'description': data.get('description', ''),
        'created_at': datetime.now().isoformat()
    }
    graph['nodes'].append(node)
    save_relation_graph(graph)
    return jsonify({'node': node})

@app.route('/api/relation-graph/edges', methods=['POST'])
def add_relation_edge():
    data = request.get_json() or {}
    graph = load_relation_graph()
    edge = {
        'id': str(uuid.uuid4()),
        'source': data.get('source', ''),
        'target': data.get('target', ''),
        'relation': data.get('relation', 'related_to'),
        'description': data.get('description', ''),
        'created_at': datetime.now().isoformat()
    }
    graph['edges'].append(edge)
    save_relation_graph(graph)
    return jsonify({'edge': edge})

@app.route('/api/relation-graph/node/<node_id>', methods=['DELETE'])
def delete_relation_node(node_id):
    graph = load_relation_graph()
    graph['nodes'] = [n for n in graph['nodes'] if n['id'] != node_id]
    graph['edges'] = [e for e in graph['edges'] if e['source'] != node_id and e['target'] != node_id]
    save_relation_graph(graph)
    return jsonify({'status': 'deleted'})

@app.route('/api/relation-graph/edge/<edge_id>', methods=['DELETE'])
def delete_relation_edge(edge_id):
    graph = load_relation_graph()
    graph['edges'] = [e for e in graph['edges'] if e['id'] != edge_id]
    save_relation_graph(graph)
    return jsonify({'status': 'deleted'})

# ============================================================
# 启动
# ============================================================
if __name__ == '__main__':
    port = int(os.environ.get('DEPLOY_RUN_PORT', 5000))
    print(f"""
╔══════════════════════════════════════════╗
║       ArtMind - 艺术学习AI助手            ║
║       Flask 服务器 (纯开源版)             ║
║       端口: {port}                          ║
║       模式: {'模拟 (无 API Key)' if USE_MOCK else '真实 (已配置 API)'}
║       访问: http://localhost:{port}         ║
╚══════════════════════════════════════════╝
    """)

    print("KEY=", repr(API_KEY))
    print("BASE=", repr(API_BASE_URL))
    print("MODEL=", repr(MODEL_NAME))
    app.run(host='0.0.0.0', port=port, debug=True)
