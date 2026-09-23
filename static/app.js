/**
 * ArtMind - 艺术学习AI助手 (前端)
 * 完全基于后端 REST API，所有数据存储在后端
 */

// ========== 全局状态 ==========
const state = {
    currentChatId: null,
    currentMode: 'read',
    currentVersion: 'standard',
    messages: [],
    uploadedImage: null,      // base64 图片数据
    isGenerating: false,
    chats: []                 // 从后端加载的对话列表
};

// ========== DOM 引用 ==========
const el = {
    sidebar: document.getElementById('sidebar'),
    toggleSidebar: document.getElementById('toggleSidebar'),
    expandSidebar: document.getElementById('expandSidebar'),
    searchInput: document.getElementById('searchInput'),
    chatList: document.getElementById('chatList'),
    newChatBtn: document.getElementById('newChatBtn'),
    messagesContainer: document.getElementById('messagesContainer'),
    welcomeScreen: document.getElementById('welcomeScreen'),
    messageInput: document.getElementById('messageInput'),
    sendBtn: document.getElementById('sendBtn'),
    versionBtn: document.getElementById('versionBtn'),
    versionDropdown: document.getElementById('versionDropdown'),
    currentVersion: document.getElementById('currentVersion'),
    uploadBtn: document.getElementById('uploadBtn'),
    fileInput: document.getElementById('fileInput'),
    uploadedImages: document.getElementById('uploadedImages'),
    openNetworkBtn: document.getElementById('openNetworkBtn'),
    viewNetworkBtn: document.getElementById('viewNetworkBtn'),
    networkModal: document.getElementById('networkModal'),
    closeNetworkModal: document.getElementById('closeNetworkModal'),
    networkList: document.getElementById('networkList'),
    chatTitle: document.getElementById('chatTitle'),
    modeButtons: document.querySelectorAll('.mode-btn')
};

// ========== API 基础路径 ==========
const API_BASE = '';

// ========== 初始化 ==========
async function init() {
    await loadChats();
    setupEventListeners();
    autoResizeTextarea();
    // 如果没有对话，创建一个默认的
    if (state.chats.length === 0) {
        await createNewChat();
    } else {
        loadChat(state.chats[0].id);
    }
}

// ========== 事件监听 ==========
function setupEventListeners() {
    el.toggleSidebar.addEventListener('click', () => el.sidebar.classList.add('collapsed'));
    el.expandSidebar.addEventListener('click', () => el.sidebar.classList.remove('collapsed'));

    el.newChatBtn.addEventListener('click', createNewChat);
    el.sendBtn.addEventListener('click', sendMessage);
    el.messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    el.versionBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        el.versionDropdown.classList.toggle('show');
    });
    document.querySelectorAll('.version-option').forEach(opt => {
        opt.addEventListener('click', () => {
            const ver = opt.dataset.version;
            state.currentVersion = ver;
            el.currentVersion.textContent = opt.textContent;
            document.querySelectorAll('.version-option').forEach(o => o.classList.remove('selected'));
            opt.classList.add('selected');
            el.versionDropdown.classList.remove('show');
        });
    });
    document.addEventListener('click', () => el.versionDropdown.classList.remove('show'));

    el.modeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            el.modeButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.currentMode = btn.dataset.mode;
        });
    });

    el.uploadBtn.addEventListener('click', () => el.fileInput.click());
    el.fileInput.addEventListener('change', handleFileUpload);

    el.openNetworkBtn.addEventListener('click', openNetworkModal);
    el.viewNetworkBtn.addEventListener('click', openNetworkModal);
    el.closeNetworkModal.addEventListener('click', closeNetworkModal);
    el.networkModal.addEventListener('click', (e) => {
        if (e.target === el.networkModal) closeNetworkModal();
    });

    l.searechInput.addEventListener('input', filterChatList);
}

// ========== 自动调整文本框高度 ==========
function autoResizeTextarea() {
    el.messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 200) + 'px';
    });
}

// ========== 对话管理（后端 API） ==========
async function loadChats() {
    try {
        const res = await fetch(`${API_BASE}/api/conversations`);
        const data = await res.json();
        state.chats = data.conversations || [];
        renderChatList();
    } catch (e) {
        console.error('加载对话列表失败:', e);
        state.chats = [];
        renderChatList();
    }
}

async function createNewChat() {
    try {
        const res = await fetch(`${API_BASE}/api/conversations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: '新对话', preview: '开始新的艺术探索...' })
        });
        const data = await res.json();
        const chat = data.conversation;
        state.chats.unshift(chat);
        renderChatList();
        loadChat(chat.id);
    } catch (e) {
        console.error('创建对话失败:', e);
        alert('创建对话失败，请检查后端是否运行');
    }
}

async function loadChat(chatId) {
    try {
        const res = await fetch(`${API_BASE}/api/conversations/${chatId}`);
        const data = await res.json();
        const chat = data.conversation;
        state.currentChatId = chat.id;
        state.messages = chat.messages || [];
        el.chatTitle.textContent = chat.title;
        renderMessages();
        renderChatList();
    } catch (e) {
        console.error('加载对话失败:', e);
    }
}

async function deleteChat(chatId) {
    if (!confirm('确定要删除此对话吗？')) return;
    try {
        await fetch(`${API_BASE}/api/conversations/${chatId}`, { method: 'DELETE' });
        state.chats = state.chats.filter(c => c.id !== chatId);
        if (state.currentChatId === chatId) {
            state.currentChatId = null;
            state.messages = [];
            renderMessages();
            el.chatTitle.textContent = 'ArtMind - 艺术学习AI助手';
        }
        renderChatList();
    } catch (e) {
        console.error('删除对话失败:', e);
    }
}

// ========== 渲染对话列表 ==========
function renderChatList(filter = '') {
    const list = el.chatList;
    const filtered = filter
        ? state.chats.filter(c => c.title.includes(filter) || c.preview.includes(filter))
        : state.chats;

    if (filtered.length === 0) {
        list.innerHTML = `<div style="color:var(--text-muted);text-align:center;padding:20px;">暂无对话</div>`;
        return;
    }

    list.innerHTML = filtered.map(chat => `
        <div class="chat-item ${chat.id === state.currentChatId ? 'active' : ''}" data-id="${chat.id}">
            <div class="chat-item-title">${escapeHtml(chat.title)}</div>
            <div class="chat-item-preview">${escapeHtml(chat.preview || '')}</div>
            <div class="chat-item-time">${chat.time || ''}</div>
            <button class="chat-delete" style="background:transparent;border:none;color:#ffffff;cursor:pointer;float:right;font-size:14px;" data-id="${chat.id}">✕</button>
        </div>
    `).join('');

    list.querySelectorAll('.chat-item').forEach(item => {
        item.addEventListener('click', (e) => {
            if (e.target.classList.contains('chat-delete')) return;
            loadChat(item.dataset.id);
        });
        const delBtn = item.querySelector('.chat-delete');
        if (delBtn) {
            delBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                deleteChat(delBtn.dataset.id);
            });
        }
    });
}

function filterChatList() {
    const query = el.searchInput.value.trim();
    renderChatList(query);
}

// ========== 渲染消息 ==========
function renderMessages() {
    if (state.messages.length === 0) {
        el.welcomeScreen.style.display = 'flex';
        el.messagesContainer.innerHTML = '';
        el.messagesContainer.appendChild(el.welcomeScreen);
        return;
    }
    el.welcomeScreen.style.display = 'none';

    let html = '';
    state.messages.forEach(msg => {
        const avatar = msg.role === 'user' ? '👤' : '🎨';
        const sender = msg.role === 'user' ? '你' : 'ArtMind';
        const time = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : '';

        let content = msg.content;
        // 简单的 Markdown 渲染（支持标题、列表、粗体等）
        content = renderMarkdown(content);

        // 如果有图片
        let imageHtml = '';
        if (msg.image) {
            imageHtml = `<div class="uploaded-image"><img src="${msg.image}" alt="画作"></div>`;
        }

        let optionsHtml = '';
        if (msg.role === 'ai' && msg.options && msg.options.length) {
            optionsHtml = `<div class="ai-options">${msg.options.map(opt => `<button class="ai-option-btn" data-option="${opt}">${opt}</button>`).join('')}</div>`;
        }

        html += `
            <div class="message ${msg.role}">
                <div class="message-header">
                    <div class="message-avatar">${avatar}</div>
                    <span class="message-sender">${sender}</span>
                    <span class="message-time">${time}</span>
                </div>
                <div class="message-content">${imageHtml}${content}</div>
                ${optionsHtml}
            </div>
        `;
    });

    el.messagesContainer.innerHTML = html;
    el.messagesContainer.scrollTop = el.messagesContainer.scrollHeight;

    // 绑定选项按钮
    el.messagesContainer.querySelectorAll('.ai-option-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            el.messageInput.value = btn.dataset.option;
            sendMessage();
        });
    });
}

// ========== 简易 Markdown 渲染 ==========
function renderMarkdown(text) {
    if (!text) return '';
    let html = escapeHtml(text);
    // 标题
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    // 粗体
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // 斜体
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // 代码
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // 引用
    html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
    // 列表（简单处理）
    const lines = html.split('\n');
    let result = [];
    let inList = false;
    let listType = 'ul';
    for (let line of lines) {
        if (/^[-*] /.test(line)) {
            if (!inList) { result.push('<ul>'); inList = true; listType = 'ul'; }
            result.push(`<li>${line.replace(/^[-*] /, '')}</li>`);
        } else if (/^\d+\. /.test(line)) {
            if (!inList) { result.push('<ol>'); inList = true; listType = 'ol'; }
            result.push(`<li>${line.replace(/^\d+\. /, '')}</li>`);
        } else {
            if (inList) { result.push(listType === 'ul' ? '</ul>' : '</ol>'); inList = false; }
            result.push(line);
        }
    }
    if (inList) result.push(listType === 'ul' ? '</ul>' : '</ol>');
    html = result.join('\n');
    // 段落
    html = html.split('\n\n').map(p => {
        if (p.trim().startsWith('<h') || p.trim().startsWith('<ul') || p.trim().startsWith('<ol') ||
            p.trim().startsWith('<blockquote') || p.trim().startsWith('<div')) {
            return p;
        }
        return `<p>${p}</p>`;
    }).join('');
    return html;
}

// ========== 发送消息 ==========
async function sendMessage() {
    const content = el.messageInput.value.trim();
    if (!content && !state.uploadedImage) return;
    if (state.isGenerating) return;

    state.isGenerating = true;
    el.sendBtn.disabled = true;

    // 如果没有当前对话，先创建
    if (!state.currentChatId) {
        await createNewChat();
        if (!state.currentChatId) {
            state.isGenerating = false;
            el.sendBtn.disabled = false;
            return;
        }
    }

    // 构建用户消息
    const userMsg = {
        role: 'user',
        content: content,
        timestamp: Date.now(),
        image: state.uploadedImage
    };
    state.messages.push(userMsg);

    // 更新对话标题和预览（仅本地，后端会在保存时更新）
    const chat = state.chats.find(c => c.id === state.currentChatId);
    if (chat) {
        if (chat.title === '新对话' && content) {
            chat.title = content.substring(0, 15) + (content.length > 15 ? '...' : '');
        }
        chat.preview = content.substring(0, 30) + (content.length > 30 ? '...' : '');
        chat.time = new Date().toLocaleDateString('zh-CN');
        // 更新后端
        try {
            await fetch(`${API_BASE}/api/conversations/${state.currentChatId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: chat.title, preview: chat.preview })
            });
        } catch (e) {}
    }

    // 清空输入
    el.messageInput.value = '';
    const imageCopy = state.uploadedImage;
    state.uploadedImage = null;
    el.uploadedImages.innerHTML = '';

    renderMessages();
    renderChatList();

    // 显示加载动画
    showTypingIndicator();

    try {
        // 调用后端 AI 接口
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: content,
                mode: state.currentMode,
                version: state.currentVersion,
                image: imageCopy || null,
                history: state.messages.slice(0, -1).map(m => ({ role: m.role, content: m.content }))
            })
        });

        const data = await response.json();
        removeTypingIndicator();

        if (data.success) {
            const aiMsg = {
                role: 'ai',
                content: data.reply,
                timestamp: Date.now(),
                options: data.options || null
            };
            state.messages.push(aiMsg);

            // 保存消息到后端
            try {
                await fetch(`${API_BASE}/api/conversations/${state.currentChatId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ messages: state.messages })
                });
            } catch (e) {}
        } else {
            const errorMsg = {
                role: 'ai',
                content: `抱歉，出现错误：${data.error || '请稍后重试'}`,
                timestamp: Date.now()
            };
            state.messages.push(errorMsg);
        }
    } catch (error) {
        removeTypingIndicator();
        console.error('请求失败:', error);
        const errorMsg = {
            role: 'ai',
            content: '抱歉，网络连接出现问题，请检查服务器是否正常运行。',
            timestamp: Date.now()
        };
        state.messages.push(errorMsg);
    }

    renderMessages();
    state.isGenerating = false;
    el.sendBtn.disabled = false;
}

function showTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.id = 'typingIndicator';
    indicator.className = 'message ai';
    indicator.innerHTML = `
        <div class="message-header">
            <div class="message-avatar">🎨</div>
            <span class="message-sender">ArtMind</span>
        </div>
        <div class="message-content">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    el.messagesContainer.appendChild(indicator);
    el.messagesContainer.scrollTop = el.messagesContainer.scrollHeight;
}

function removeTypingIndicator() {
    const ind = document.getElementById('typingIndicator');
    if (ind) ind.remove();
}

// ========== 文件上传 ==========
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
        alert('请上传图片文件');
        return;
    }
    if (file.size > 10 * 1024 * 1024) {
        alert('图片大小不能超过10MB');
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        state.uploadedImage = e.target.result;
        el.uploadedImages.innerHTML = `
            <div class="uploaded-image">
                <img src="${e.target.result}" alt="预览">
                <div class="uploaded-image-info">
                    <div class="uploaded-image-name">${file.name}</div>
                    <div class="uploaded-image-size">${(file.size / 1024).toFixed(1)} KB</div>
                </div>
                <button class="remove-image" id="removeImage">移除</button>
            </div>
        `;
        document.getElementById('removeImage').addEventListener('click', () => {
            state.uploadedImage = null;
            el.uploadedImages.innerHTML = '';
            el.fileInput.value = '';
        });
    };
    reader.readAsDataURL(file);
}

// ========== 关系网模态框 ==========
async function openNetworkModal() {
    el.networkModal.classList.add('show');
    try {
        const res = await fetch(`${API_BASE}/api/relation-graph`);
        const data = await res.json();
        renderNetworkList(data.nodes || [], data.edges || []);
    } catch (e) {
        console.error('加载关系网失败:', e);
        el.networkList.innerHTML = '<div style="color:var(--text-muted)">暂无关系网数据</div>';
    }
}

function closeNetworkModal() {
    el.networkModal.classList.remove('show');
}

function renderNetworkList(nodes, edges) {
    if (!nodes || nodes.length === 0) {
        el.networkList.innerHTML = '<div style="color:var(--text-muted)">暂无关系网节点</div>';
        return;
    }
    el.networkList.innerHTML = nodes.map(node => `
        <div class="network-item">
            <div class="network-info">
                <div class="network-name">${escapeHtml(node.name)}</div>
                <div class="network-meta">类型: ${node.type || '未知'} · 创建于 ${node.created_at || ''}</div>
            </div>
            <div class="network-actions">
                <button class="network-btn">查看关联</button>
            </div>
        </div>
    `).join('');
}

// ========== 工具函数 ==========
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========== 启动 ==========
document.addEventListener('DOMContentLoaded', init);