/**
 * AgentGaia - Multi-LLM Chat Platform
 * Clean design with dynamic model selection and file upload
 */

const connections = {};
const providers = ['claude', 'openai', 'gemini'];
let currentProvider = 'claude';
let messageId = 0;

// File attachments state
const attachments = new Map(); // filename -> { status, category, error }

const modelSelect = document.getElementById('model-select');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const chatOutput = document.getElementById('chat-output');
const chatStatus = document.getElementById('chat-status');
const chatCard = document.querySelector('.chat-card');
const attachBtn = document.getElementById('attach-btn');
const fileInput = document.getElementById('file-input');
const attachmentsPreview = document.getElementById('attachments-preview');

document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    connectAllProviders();
});

function initEventListeners() {
    modelSelect.addEventListener('change', (e) => {
        currentProvider = e.target.value;
        updateCardStyle();
        updateStatus();
        updateSendButton();
    });

    sendBtn.addEventListener('click', sendMessage);

    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    chatInput.addEventListener('input', () => {
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(chatInput.scrollHeight, 128) + 'px';
        updateSendButton();
    });

    // File upload handlers
    attachBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);

    // Drag and drop
    chatCard.addEventListener('dragover', (e) => {
        e.preventDefault();
        chatCard.classList.add('drag-over');
    });
    chatCard.addEventListener('dragleave', () => {
        chatCard.classList.remove('drag-over');
    });
    chatCard.addEventListener('drop', (e) => {
        e.preventDefault();
        chatCard.classList.remove('drag-over');
        if (e.dataTransfer.files.length > 0) {
            handleFiles(e.dataTransfer.files);
        }
    });
}

function updateCardStyle() {
    chatCard.setAttribute('data-provider', currentProvider);
}

function updateSendButton() {
    const ws = connections[currentProvider];
    const isConnected = ws && ws.readyState === WebSocket.OPEN;
    const hasText = chatInput.value.trim().length > 0;
    const hasAttachments = attachments.size > 0;
    sendBtn.disabled = (!hasText && !hasAttachments) || !isConnected;
}

function updateStatus(text, className) {
    if (text) {
        chatStatus.textContent = text;
        chatStatus.className = `status ${className || ''}`;
    } else {
        const ws = connections[currentProvider];
        if (ws && ws.readyState === WebSocket.OPEN) {
            chatStatus.textContent = '연결됨';
            chatStatus.className = 'status connected';
        } else {
            chatStatus.textContent = '연결 중...';
            chatStatus.className = 'status';
        }
    }
}

function connectAllProviders() {
    providers.forEach(provider => connectWebSocket(provider));
}

function connectWebSocket(provider) {
    if (connections[provider]) connections[provider].close();

    const ws = new WebSocket(`ws://${window.location.host}/api/v1/ws/chat?provider=${provider}`);

    ws.onopen = () => {
        console.log(`Connected: ${provider}`);
        if (provider === currentProvider) {
            updateStatus('연결됨', 'connected');
            updateSendButton();
        }
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (provider === currentProvider) {
            handleMessage(data);
        }
    };

    ws.onclose = () => {
        console.log(`Disconnected: ${provider}`);
        if (provider === currentProvider) {
            updateStatus('연결 끊김', '');
            updateSendButton();
        }
        setTimeout(() => {
            if (!connections[provider] || connections[provider].readyState === WebSocket.CLOSED) {
                connectWebSocket(provider);
            }
        }, 3000);
    };

    ws.onerror = () => {
        if (provider === currentProvider) {
            updateStatus('오류', 'error');
        }
    };

    connections[provider] = ws;
}

function handleMessage(data) {
    switch (data.status || data.type) {
        case 'connected':
            updateStatus('준비됨', 'connected');
            break;

        case 'streaming':
            updateStatus('응답 중...', 'streaming');
            hideEmptyState();
            let bubble = chatOutput.querySelector('.message.assistant.streaming');
            if (!bubble) {
                bubble = document.createElement('div');
                bubble.className = 'message assistant streaming';
                chatOutput.appendChild(bubble);
            }
            bubble.textContent += data.chunk;
            chatOutput.scrollTop = chatOutput.scrollHeight;
            break;

        case 'complete':
            updateStatus('완료', 'connected');
            const streamingBubble = chatOutput.querySelector('.message.assistant.streaming');
            if (streamingBubble) streamingBubble.classList.remove('streaming');
            break;

        case 'error':
            updateStatus('오류', 'error');
            break;

        case 'backup_switch':
            updateStatus(`${data.backup_provider} 전환`, 'connected');
            break;
    }
}

function hideEmptyState() {
    const emptyState = chatOutput.querySelector('.empty-state');
    if (emptyState) emptyState.remove();
}

// File upload functions
async function handleFileSelect(e) {
    if (e.target.files.length > 0) {
        await handleFiles(e.target.files);
        fileInput.value = ''; // Reset for same file selection
    }
}

async function handleFiles(files) {
    for (const file of files) {
        await uploadFile(file);
    }
}

async function uploadFile(file) {
    const filename = file.name;

    // Add to attachments with uploading status
    attachments.set(filename, { status: 'uploading', category: 'unknown' });
    renderAttachments();

    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/api/v1/upload', {
            method: 'POST',
            body: formData,
        });

        const result = await response.json();

        if (result.success) {
            attachments.set(filename, {
                status: 'ready',
                category: result.category,
                hasImage: result.has_image,
            });
        } else {
            attachments.set(filename, {
                status: 'error',
                category: 'unsupported',
                error: result.error || 'Upload failed',
            });
        }
    } catch (error) {
        attachments.set(filename, {
            status: 'error',
            category: 'unsupported',
            error: error.message,
        });
    }

    renderAttachments();
    updateSendButton();
}

function removeAttachment(filename) {
    attachments.delete(filename);
    renderAttachments();
    updateSendButton();

    // Also delete from server
    fetch(`/api/v1/upload/${encodeURIComponent(filename)}`, {
        method: 'DELETE',
    }).catch(console.error);
}

function renderAttachments() {
    if (attachments.size === 0) {
        attachmentsPreview.style.display = 'none';
        return;
    }

    attachmentsPreview.style.display = 'flex';
    attachmentsPreview.innerHTML = '';

    for (const [filename, info] of attachments) {
        const item = document.createElement('div');
        item.className = `attachment-item ${info.category} ${info.status}`;

        const icon = getFileIcon(info.category);
        const statusIcon = info.status === 'uploading' ? '⏳' : '';

        item.innerHTML = `
            <span class="icon">${icon}</span>
            <span class="filename" title="${filename}">${statusIcon}${filename}</span>
            <button class="remove-btn" title="제거">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 6L6 18M6 6l12 12"/>
                </svg>
            </button>
        `;

        item.querySelector('.remove-btn').addEventListener('click', () => {
            removeAttachment(filename);
        });

        if (info.error) {
            item.title = info.error;
        }

        attachmentsPreview.appendChild(item);
    }
}

function getFileIcon(category) {
    const icons = {
        image: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>',
        document: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/></svg>',
        code: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 18l6-6-6-6M8 6l-6 6 6 6"/></svg>',
        data: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3h18v18H3zM3 9h18M3 15h18M9 3v18M15 3v18"/></svg>',
        text: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6"/></svg>',
    };
    return icons[category] || icons.text;
}

function sendMessage() {
    const message = chatInput.value.trim();
    const readyAttachments = Array.from(attachments.entries())
        .filter(([_, info]) => info.status === 'ready')
        .map(([filename]) => filename);

    if (!message && readyAttachments.length === 0) return;

    messageId++;

    chatInput.value = '';
    chatInput.style.height = 'auto';

    // Build display message with attachment info
    let displayMessage = message;
    if (readyAttachments.length > 0) {
        const fileList = readyAttachments.map(f => `📎 ${f}`).join('\n');
        displayMessage = readyAttachments.length > 0
            ? (message ? `${fileList}\n\n${message}` : fileList)
            : message;
    }

    hideEmptyState();
    appendMessage(displayMessage, 'user');
    updateStatus('요청 중...', '');

    // Clear attachments
    attachments.clear();
    renderAttachments();
    updateSendButton();

    const ws = connections[currentProvider];
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'chat',
            message: message,
            message_id: messageId,
            attachments: readyAttachments,
        }));
    } else {
        updateStatus('연결 안됨', 'error');
    }
}

function appendMessage(text, type) {
    const div = document.createElement('div');
    div.className = `message ${type}`;
    div.textContent = text;
    chatOutput.appendChild(div);
    chatOutput.scrollTop = chatOutput.scrollHeight;
}
