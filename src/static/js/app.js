/**
 * AgentGaia - Multi-LLM Chat Platform
 * Each panel has independent chat functionality
 */

const connections = {};
const providers = ['claude'];
let messageId = 0;

document.addEventListener('DOMContentLoaded', () => {
    initPanelInputs();
    connectWebSockets();
});

function initPanelInputs() {
    providers.forEach(provider => {
        const panel = document.querySelector(`.chat-panel[data-provider="${provider}"]`);
        const textarea = panel.querySelector('.panel-input textarea');
        const sendBtn = panel.querySelector('.panel-send-btn');

        // Send button click
        sendBtn.addEventListener('click', () => sendMessage(provider));

        // Enter key to send
        textarea.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage(provider);
            }
        });

        // Auto-resize textarea
        textarea.addEventListener('input', () => {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 100) + 'px';
            updatePanelSendButton(provider);
        });
    });
}

function updatePanelSendButton(provider) {
    const panel = document.querySelector(`.chat-panel[data-provider="${provider}"]`);
    const textarea = panel.querySelector('.panel-input textarea');
    const sendBtn = panel.querySelector('.panel-send-btn');
    const ws = connections[provider];
    const isConnected = ws && ws.readyState === WebSocket.OPEN;
    const hasText = textarea.value.trim().length > 0;
    sendBtn.disabled = !hasText || !isConnected;
}

function connectWebSockets() {
    providers.forEach(provider => connectWebSocket(provider));
}

function connectWebSocket(provider) {
    if (connections[provider]) connections[provider].close();

    const ws = new WebSocket(`ws://${window.location.host}/api/v1/ws/chat?provider=${provider}`);

    ws.onopen = () => {
        updateStatus(provider, '연결됨', 'connected');
        updatePanelSendButton(provider);
        showPlaceholder(provider, '');
    };

    ws.onmessage = (event) => handleMessage(provider, JSON.parse(event.data));

    ws.onclose = () => {
        updateStatus(provider, '연결 끊김', 'disconnected');
        updatePanelSendButton(provider);
        setTimeout(() => {
            if (!connections[provider] || connections[provider].readyState === WebSocket.CLOSED) {
                connectWebSocket(provider);
            }
        }, 3000);
    };

    ws.onerror = () => updateStatus(provider, '연결 실패', 'error');
    connections[provider] = ws;
}

function handleMessage(provider, data) {
    const outputEl = document.getElementById(`${provider}-output`);

    switch (data.status || data.type) {
        case 'connected':
            updateStatus(provider, '준비됨', 'connected');
            break;

        case 'streaming':
            updateStatus(provider, '응답 중...', 'streaming');
            let bubble = outputEl.querySelector('.message.assistant.streaming');
            if (!bubble) {
                bubble = document.createElement('div');
                bubble.className = 'message assistant streaming';
                outputEl.appendChild(bubble);
            }
            bubble.textContent += data.chunk;
            outputEl.scrollTop = outputEl.scrollHeight;
            break;

        case 'complete':
            updateStatus(provider, '완료', 'complete');
            const streamingBubble = outputEl.querySelector('.message.assistant.streaming');
            if (streamingBubble) streamingBubble.classList.remove('streaming');
            break;

        case 'error':
            updateStatus(provider, '응답 불가', 'error');
            showPlaceholder(provider, '서비스 연결을 확인해주세요');
            break;

        case 'backup_switch':
            updateStatus(provider, `${data.backup_provider} 전환`, 'connected');
            break;
    }
}

function showPlaceholder(provider, text) {
    const outputEl = document.getElementById(`${provider}-output`);
    let placeholder = outputEl.querySelector('.placeholder');
    if (!placeholder && text) {
        placeholder = document.createElement('div');
        placeholder.className = 'placeholder';
        outputEl.appendChild(placeholder);
    }
    if (placeholder) {
        placeholder.textContent = text;
        if (!text) placeholder.remove();
    }
}

function sendMessage(provider) {
    const panel = document.querySelector(`.chat-panel[data-provider="${provider}"]`);
    const textarea = panel.querySelector('.panel-input textarea');
    const message = textarea.value.trim();

    if (!message) return;

    messageId++;
    const outputEl = document.getElementById(`${provider}-output`);

    // 플레이스홀더 제거
    const placeholder = outputEl.querySelector('.placeholder');
    if (placeholder) placeholder.remove();

    // Clear input
    textarea.value = '';
    textarea.style.height = 'auto';
    updatePanelSendButton(provider);

    // Show user message
    appendMessage(provider, message, 'user');
    updateStatus(provider, '요청 중...', '');

    // Send to WebSocket
    const ws = connections[provider];
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'chat',
            message: message,
            message_id: messageId
        }));
    } else {
        updateStatus(provider, '연결 안됨', 'error');
    }
}

function appendMessage(provider, text, type) {
    const outputEl = document.getElementById(`${provider}-output`);
    const div = document.createElement('div');
    div.className = `message ${type}`;
    div.textContent = text;
    outputEl.appendChild(div);
    outputEl.scrollTop = outputEl.scrollHeight;
}

function updateStatus(provider, text, className) {
    const el = document.getElementById(`${provider}-status`);
    el.textContent = text;
    el.className = `status ${className}`;
}
