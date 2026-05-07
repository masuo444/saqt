/**
 * KANADE WEB チャットボット ウィジェット
 * OpenAI API プロキシ版（APIキーはサーバー側で管理）
 *
 * 使い方:
 * <script src="chatbot/widget/chatbot.js"
 *   data-knowledge="knowledge.json"
 *   data-primary-color="#f97316"
 * ></script>
 */
(function() {
    'use strict';

    const scriptTag = document.currentScript;
    const knowledgePath = scriptTag?.getAttribute('data-knowledge') || './knowledge.json';
    const primaryColor = scriptTag?.getAttribute('data-primary-color') || '#f97316';
    const greetingOverride = scriptTag?.getAttribute('data-greeting') || '';

    let knowledge = null;
    let settings = {};
    let conversationHistory = [];

    function loadCSS() {
        const cssPath = scriptTag?.src?.replace('chatbot.js', 'chatbot.css') || './chatbot.css';
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = cssPath;
        document.head.appendChild(link);

        if (!document.querySelector('link[href*="Noto+Sans+JP"]')) {
            const font = document.createElement('link');
            font.rel = 'stylesheet';
            font.href = 'https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600&display=swap';
            document.head.appendChild(font);
        }
    }

    async function loadKnowledge() {
        try {
            const res = await fetch(knowledgePath);
            if (!res.ok) throw new Error('not found');
            const data = await res.json();
            knowledge = data.entries || [];
            settings = data.settings || {};
        } catch (e) {
            knowledge = [];
            settings = {
                bot_name: 'サポート',
                greeting: 'こんにちは！ご質問をどうぞ。',
                fallback: 'お問い合わせはこちら: info@web.kanade-ai.com',
                quick_replies: []
            };
        }
    }

    // OpenAI プロキシ経由（APIキーはサーバー側 - フロントエンドに露出しない）
    async function askOpenAI(userMessage) {
        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: userMessage,
                    history: conversationHistory.slice(-10),
                }),
            });
            if (!res.ok) return null;
            const data = await res.json();
            return data.reply || null;
        } catch (_) {
            return null;
        }
    }

    // キーワードマッチング（APIが使えない場合のフォールバック）
    function findAnswerByKeyword(userMessage) {
        if (!knowledge || knowledge.length === 0) return null;

        const msg = userMessage.toLowerCase().replace(/[？?！!。、\s]/g, '');
        let bestMatch = null;
        let bestScore = 0;

        for (const entry of knowledge) {
            let score = 0;
            for (const kw of (entry.keywords || [])) {
                if (msg.includes(kw.toLowerCase().replace(/\s/g, ''))) score += 10;
            }
            for (const q of (entry.questions || [])) {
                const qNorm = q.toLowerCase().replace(/[？?！!。、\s]/g, '');
                if (msg.includes(qNorm) || qNorm.includes(msg)) score += 15;
                const common = [...msg].filter(c => qNorm.includes(c)).length;
                if (common / Math.max(msg.length, qNorm.length) > 0.5) score += 5;
            }
            if (score > bestScore) { bestScore = score; bestMatch = entry; }
        }

        return bestScore >= 5 ? bestMatch?.answer : null;
    }

    async function getAnswer(userMessage) {
        const reply = await askOpenAI(userMessage);
        if (reply) {
            conversationHistory.push({ role: 'user', content: userMessage });
            conversationHistory.push({ role: 'assistant', content: reply });
            return reply;
        }
        const keywordAnswer = findAnswerByKeyword(userMessage);
        if (keywordAnswer) return keywordAnswer;
        return settings.fallback || 'お問い合わせはこちら: info@web.kanade-ai.com';
    }

    function buildWidget() {
        document.documentElement.style.setProperty('--saqt-primary', primaryColor);

        const btn = document.createElement('button');
        btn.className = 'saqt-chat-btn';
        btn.setAttribute('aria-label', 'チャットを開く');
        btn.innerHTML = `
            <svg class="saqt-icon-chat" viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            <svg class="saqt-icon-close" viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12" stroke="#fff" stroke-width="2.5" stroke-linecap="round" fill="none"/></svg>
            <span class="saqt-chat-badge">1</span>
        `;

        const win = document.createElement('div');
        win.className = 'saqt-chat-window';
        const botName = settings.bot_name || 'サポート';
        const greeting = greetingOverride || settings.greeting || 'こんにちは！';

        win.innerHTML = `
            <div class="saqt-chat-header">
                <div class="saqt-chat-avatar">
                    <svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                </div>
                <div class="saqt-chat-header-info">
                    <h3>${escapeHtml(botName)}</h3>
                    <p>通常すぐに返信</p>
                </div>
            </div>
            <div class="saqt-chat-messages" id="saqt-messages"></div>
            <div class="saqt-quick-replies" id="saqt-quick"></div>
            <div class="saqt-chat-input-area">
                <input type="text" class="saqt-chat-input" id="saqt-input" placeholder="メッセージを入力..." autocomplete="off" maxlength="500">
                <button class="saqt-chat-send" id="saqt-send" aria-label="送信">
                    <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
                </button>
            </div>
            <div class="saqt-chat-powered">Powered by <a href="https://web.kanade-ai.com" target="_blank" rel="noopener">KANADE WEB</a></div>
        `;

        document.body.appendChild(btn);
        document.body.appendChild(win);

        const messagesEl = win.querySelector('#saqt-messages');
        const inputEl = win.querySelector('#saqt-input');
        const sendBtn = win.querySelector('#saqt-send');
        const quickEl = win.querySelector('#saqt-quick');
        const badge = btn.querySelector('.saqt-chat-badge');
        let isOpen = false;
        let isProcessing = false;

        btn.addEventListener('click', () => {
            isOpen = !isOpen;
            win.classList.toggle('open', isOpen);
            btn.classList.toggle('active', isOpen);
            badge.classList.add('hidden');
            if (isOpen) inputEl.focus();
        });

        addBotMessage(greeting);
        showQuickReplies();

        async function handleSend() {
            const text = inputEl.value.trim();
            if (!text || isProcessing) return;
            inputEl.value = '';
            isProcessing = true;
            addUserMessage(text);
            hideQuickReplies();
            showTyping();

            const answer = await getAnswer(text);

            removeTyping();
            addBotMessage(answer);
            showQuickReplies();
            isProcessing = false;
        }

        sendBtn.addEventListener('click', handleSend);
        inputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.isComposing) {
                e.preventDefault();
                handleSend();
            }
        });

        function addBotMessage(text) {
            const div = document.createElement('div');
            div.className = 'saqt-msg saqt-msg-bot';
            div.innerHTML = `<div class="saqt-msg-bubble">${escapeHtml(text)}</div>`;
            messagesEl.appendChild(div);
            scrollToBottom();
        }

        function addUserMessage(text) {
            const div = document.createElement('div');
            div.className = 'saqt-msg saqt-msg-user';
            div.innerHTML = `<div class="saqt-msg-bubble">${escapeHtml(text)}</div>`;
            messagesEl.appendChild(div);
            scrollToBottom();
        }

        function showTyping() {
            const div = document.createElement('div');
            div.className = 'saqt-typing';
            div.id = 'saqt-typing';
            div.innerHTML = '<div class="saqt-typing-dot"></div><div class="saqt-typing-dot"></div><div class="saqt-typing-dot"></div>';
            messagesEl.appendChild(div);
            scrollToBottom();
        }

        function removeTyping() {
            const el = document.getElementById('saqt-typing');
            if (el) el.remove();
        }

        function showQuickReplies() {
            const replies = settings.quick_replies || [];
            if (replies.length === 0) return;
            quickEl.innerHTML = '';
            for (const text of replies) {
                const qbtn = document.createElement('button');
                qbtn.className = 'saqt-quick-btn';
                qbtn.textContent = text;
                qbtn.addEventListener('click', () => {
                    inputEl.value = text;
                    handleSend();
                });
                quickEl.appendChild(qbtn);
            }
        }

        function hideQuickReplies() { quickEl.innerHTML = ''; }
        function scrollToBottom() { messagesEl.scrollTop = messagesEl.scrollHeight; }
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML.replace(/\n/g, '<br>');
    }

    async function init() {
        loadCSS();
        await loadKnowledge();
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', buildWidget);
        } else {
            buildWidget();
        }
    }

    init();
})();
