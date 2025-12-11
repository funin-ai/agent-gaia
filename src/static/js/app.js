/**
 * AgentGaia - Claude-style Multi-LLM Chat Platform
 */

const connections = {};
const providers = ['claude', 'openai', 'gemini'];
let currentProvider = 'claude';
let messageId = 0;

// File attachments state
const attachments = new Map();

// Auth state
let currentUser = null;

// DOM Elements
const modelSelect = document.getElementById('model-select');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const chatOutput = document.getElementById('chat-output');
const chatStatus = document.getElementById('chat-status');
const attachBtn = document.getElementById('attach-btn');
const fileInput = document.getElementById('file-input');
const attachmentsPreview = document.getElementById('attachments-preview');
const welcomeScreen = document.getElementById('welcome-screen');
const newChatBtn = document.getElementById('new-chat-btn');
const chatMain = document.querySelector('.chat-main');
const usageInfo = document.getElementById('usage-info');

document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    initAuth();
    connectAllProviders();
});

function initEventListeners() {
    modelSelect.addEventListener('change', (e) => {
        currentProvider = e.target.value;
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
        chatInput.style.height = Math.min(chatInput.scrollHeight, 200) + 'px';
        updateSendButton();
    });

    // Paste image from clipboard
    chatInput.addEventListener('paste', async (e) => {
        const items = e.clipboardData?.items;
        if (!items) return;

        for (const item of items) {
            if (item.type.startsWith('image/')) {
                e.preventDefault();
                const file = item.getAsFile();
                if (file) {
                    // Generate filename with timestamp
                    const ext = item.type.split('/')[1] || 'png';
                    const filename = `pasted-image-${Date.now()}.${ext}`;
                    const renamedFile = new File([file], filename, { type: file.type });
                    await handleFiles([renamedFile]);
                }
                break;
            }
        }
    });

    // File upload handlers
    attachBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);

    // New chat button
    newChatBtn.addEventListener('click', clearChat);

    // Drag and drop on main area
    const chatMain = document.querySelector('.chat-main');
    chatMain.addEventListener('dragover', (e) => {
        e.preventDefault();
        chatMain.classList.add('drag-over');
    });
    chatMain.addEventListener('dragleave', () => {
        chatMain.classList.remove('drag-over');
    });
    chatMain.addEventListener('drop', (e) => {
        e.preventDefault();
        chatMain.classList.remove('drag-over');
        if (e.dataTransfer.files.length > 0) {
            handleFiles(e.dataTransfer.files);
        }
    });
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
        chatStatus.className = `status-indicator ${className || ''}`;
    } else {
        const ws = connections[currentProvider];
        if (ws && ws.readyState === WebSocket.OPEN) {
            chatStatus.textContent = '';
            chatStatus.className = 'status-indicator connected';
        } else {
            chatStatus.textContent = 'Connecting...';
            chatStatus.className = 'status-indicator';
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
            updateStatus();
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
            updateStatus('Disconnected', '');
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
            updateStatus('Error', 'error');
        }
    };

    connections[provider] = ws;
}

function handleMessage(data) {
    switch (data.status || data.type) {
        case 'connected':
            updateStatus();
            break;

        case 'streaming':
            updateStatus('Thinking...', 'streaming');
            hideWelcomeScreen();
            let bubble = chatOutput.querySelector('.message.assistant.streaming');
            if (!bubble) {
                bubble = createMessageElement('', 'assistant', true);
                chatOutput.appendChild(bubble);
            }
            const content = bubble.querySelector('.message-content');
            content.textContent += data.chunk;
            chatOutput.scrollTop = chatOutput.scrollHeight;
            break;

        case 'complete':
            updateStatus();
            const streamingBubble = chatOutput.querySelector('.message.assistant.streaming');
            if (streamingBubble) streamingBubble.classList.remove('streaming');
            break;

        case 'error':
            updateStatus('Error', 'error');
            break;

        case 'backup_switch':
            updateStatus(`Switched to ${data.backup_provider}`, 'connected');
            break;

        case 'usage':
            updateUsageDisplay(data.session);
            break;

        case 'history_cleared':
            updateUsageDisplay(data.session);
            break;
    }
}

function updateUsageDisplay(session) {
    if (!usageInfo || !session) return;
    const cost = session.total_cost < 0.01
        ? `${(session.total_cost * 100).toFixed(2)}¢`
        : `$${session.total_cost.toFixed(4)}`;
    usageInfo.textContent = `${session.total_tokens.toLocaleString()} tokens · ${cost}`;
}

function hideWelcomeScreen() {
    if (welcomeScreen) {
        welcomeScreen.style.display = 'none';
    }
    if (chatMain) {
        chatMain.classList.remove('centered');
    }
}

function clearChat() {
    // Clear messages except welcome screen
    const messages = chatOutput.querySelectorAll('.message');
    messages.forEach(msg => msg.remove());

    // Show welcome screen and restore centered layout
    if (welcomeScreen) {
        welcomeScreen.style.display = 'flex';
    }
    if (chatMain) {
        chatMain.classList.add('centered');
    }

    // Clear attachments
    attachments.clear();
    renderAttachments();

    // Clear input
    chatInput.value = '';
    chatInput.style.height = 'auto';
    updateSendButton();

    // Send clear history to server
    const ws = connections[currentProvider];
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'clear_history' }));
    }
}

function createMessageElement(text, type, isStreaming = false) {
    const div = document.createElement('div');
    div.className = `message ${type}${isStreaming ? ' streaming' : ''}`;

    const avatar = type === 'user' ? 'U' : 'A';

    div.innerHTML = `
        <div class="message-inner">
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">${escapeHtml(text)}</div>
        </div>
    `;

    return div;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// File upload functions
async function handleFileSelect(e) {
    if (e.target.files.length > 0) {
        await handleFiles(e.target.files);
        fileInput.value = '';
    }
}

async function handleFiles(files) {
    for (const file of files) {
        await uploadFile(file);
    }
}

async function uploadFile(file) {
    const filename = file.name;

    // Generate thumbnail for images before upload
    let thumbnail = null;
    if (file.type.startsWith('image/')) {
        thumbnail = await generateThumbnail(file);
    }

    attachments.set(filename, { status: 'uploading', category: file.type.startsWith('image/') ? 'image' : 'unknown', thumbnail });
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
            // Keep the thumbnail we generated earlier
            const existingInfo = attachments.get(filename);
            attachments.set(filename, {
                status: 'ready',
                category: result.category,
                hasImage: result.has_image,
                thumbnail: existingInfo?.thumbnail || thumbnail,
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

function generateThumbnail(file) {
    return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            resolve(e.target.result);
        };
        reader.onerror = () => resolve(null);
        reader.readAsDataURL(file);
    });
}

function removeAttachment(filename) {
    attachments.delete(filename);
    renderAttachments();
    updateSendButton();

    fetch(`/api/v1/upload/${encodeURIComponent(filename)}`, {
        method: 'DELETE',
    }).catch(console.error);
}

function renderAttachments() {
    attachmentsPreview.innerHTML = '';

    if (attachments.size === 0) {
        attachmentsPreview.classList.remove('has-files');
        return;
    }

    attachmentsPreview.classList.add('has-files');

    for (const [filename, info] of attachments) {
        const item = document.createElement('div');
        const isImage = info.category === 'image';
        const hasThumbnail = info.thumbnail && info.thumbnail.length > 0;
        item.className = `attachment-item ${info.category} ${info.status}${(isImage && hasThumbnail) ? ' image-preview' : ''}`;

        const statusIcon = info.status === 'uploading' ? '⏳ ' : '';

        if (isImage && hasThumbnail) {
            // Image with thumbnail preview
            item.innerHTML = `
                <div class="thumbnail-wrapper">
                    <img src="${info.thumbnail}" alt="${filename}" class="thumbnail">
                    <button class="remove-btn" title="Remove">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M18 6L6 18M6 6l12 12"/>
                        </svg>
                    </button>
                </div>
                <span class="filename" title="${filename}">${statusIcon}${filename}</span>
            `;
        } else {
            // Non-image file with icon
            const icon = getFileIcon(info.category);
            item.innerHTML = `
                <span class="icon">${icon}</span>
                <span class="filename" title="${filename}">${statusIcon}${filename}</span>
                <button class="remove-btn" title="Remove">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 6L6 18M6 6l12 12"/>
                    </svg>
                </button>
            `;
        }

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

    // Build display message
    let displayMessage = message;
    if (readyAttachments.length > 0) {
        const fileList = readyAttachments.map(f => `📎 ${f}`).join('\n');
        displayMessage = message ? `${fileList}\n\n${message}` : fileList;
    }

    hideWelcomeScreen();
    const userMessage = createMessageElement(displayMessage, 'user');
    chatOutput.appendChild(userMessage);
    chatOutput.scrollTop = chatOutput.scrollHeight;

    updateStatus('Sending...', '');

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
        updateStatus('Not connected', 'error');
    }
}

// ==================== Authentication ====================

/**
 * Initialize authentication - check status and setup event listeners
 */
async function initAuth() {
    // Check URL params for auth callback
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('auth_success')) {
        // Clear URL params
        window.history.replaceState({}, document.title, window.location.pathname);
    } else if (urlParams.get('auth_error')) {
        console.error('Auth error:', urlParams.get('auth_error'));
        window.history.replaceState({}, document.title, window.location.pathname);
    }

    // Check auth status
    await checkAuthStatus();

    // Setup login button handlers
    const googleBtn = document.getElementById('google-login-btn');
    const githubBtn = document.getElementById('github-login-btn');
    const logoutBtn = document.getElementById('logout-btn');

    if (googleBtn) {
        googleBtn.addEventListener('click', () => {
            if (googleBtn.classList.contains('disabled')) {
                alert('Google OAuth is not configured.\nPlease set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.');
                return;
            }
            window.location.href = '/api/v1/auth/google/login';
        });
    }

    if (githubBtn) {
        githubBtn.addEventListener('click', () => {
            if (githubBtn.classList.contains('disabled')) {
                alert('GitHub OAuth is not configured.\nPlease set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET.');
                return;
            }
            window.location.href = '/api/v1/auth/github/login';
        });
    }

    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }

    // Check which providers are available and hide unavailable ones
    await checkAvailableProviders();
}

/**
 * Check authentication status
 */
async function checkAuthStatus() {
    try {
        const response = await fetch('/api/v1/auth/status', {
            credentials: 'include'
        });
        const data = await response.json();

        if (data.authenticated && data.user) {
            currentUser = data.user;
            showUserInfo(data.user);
        } else {
            currentUser = null;
            showLoginButtons();
        }
    } catch (error) {
        console.error('Failed to check auth status:', error);
        showLoginButtons();
    }
}

/**
 * Check which OAuth providers are available
 */
async function checkAvailableProviders() {
    try {
        const response = await fetch('/api/v1/auth/providers');
        const data = await response.json();

        const googleBtn = document.getElementById('google-login-btn');
        const githubBtn = document.getElementById('github-login-btn');

        // Get available providers
        const availableProviders = data.providers.map(p => p.name);

        // Mark unconfigured providers as disabled (but keep visible)
        if (googleBtn && !availableProviders.includes('google')) {
            googleBtn.classList.add('disabled');
            googleBtn.title = 'Google OAuth not configured';
        }

        if (githubBtn && !availableProviders.includes('github')) {
            githubBtn.classList.add('disabled');
            githubBtn.title = 'GitHub OAuth not configured';
        }

        // If auth is disabled entirely, hide the section
        if (!data.enabled) {
            const userSection = document.getElementById('user-section');
            if (userSection) {
                userSection.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Failed to check available providers:', error);
    }
}

/**
 * Show login buttons (not authenticated state)
 */
function showLoginButtons() {
    const loginButtons = document.getElementById('login-buttons');
    const userInfo = document.getElementById('user-info');

    if (loginButtons) loginButtons.style.display = 'flex';
    if (userInfo) userInfo.style.display = 'none';
}

/**
 * Show user info (authenticated state)
 */
function showUserInfo(user) {
    const loginButtons = document.getElementById('login-buttons');
    const userInfo = document.getElementById('user-info');
    const userAvatar = document.getElementById('user-avatar');
    const userName = document.getElementById('user-name');

    if (loginButtons) loginButtons.style.display = 'none';
    if (userInfo) userInfo.style.display = 'flex';

    if (userAvatar) {
        userAvatar.src = user.picture || '/static/img/default-avatar.png';
        userAvatar.onerror = () => {
            userAvatar.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%236b6b6b"><circle cx="12" cy="8" r="4"/><path d="M12 14c-6 0-8 3-8 6v2h16v-2c0-3-2-6-8-6z"/></svg>';
        };
    }

    if (userName) {
        userName.textContent = user.name || user.email;
    }
}

/**
 * Logout user
 */
async function logout() {
    try {
        await fetch('/api/v1/auth/logout', {
            method: 'POST',
            credentials: 'include'
        });

        currentUser = null;
        showLoginButtons();

        // Optionally reload to clear any user-specific state
        // window.location.reload();
    } catch (error) {
        console.error('Logout failed:', error);
    }
}
