/**
 * StudyFlow AI - Main Chat Application
 */
let ws = null;
let isStreaming = false;
let streamingMessageEl = null;
let streamBuffer = '';
let currentConversationFiles = [];
let isChallengeMode = false;

function toggleChallengeMode() {
  const toggle = document.getElementById('challenge-mode-toggle');
  isChallengeMode = toggle.checked;
  const label = document.getElementById('mode-label');
  label.textContent = isChallengeMode ? 'Strict Teacher' : 'Study';
  label.style.color = isChallengeMode ? 'var(--accent-primary)' : 'var(--text-tertiary)';
  
  // Show a toast or message
  appendMessage('assistant', isChallengeMode ? 
    "🎓 **Challenge Mode Activated.** I am now your strict teacher. I will ask the questions. Let's see how much you've learned!" : 
    "📚 **Study Mode Activated.** How can I help you learn today?", false);
}

function quickAction(type) {
  const input = document.getElementById('message-input');
  if (!input) return;

  const prompts = {
    summarize: "Summarize the key points of the uploaded document(s).",
    quiz: "Generate a 5-question quiz based on the uploaded materials. Include multiple choice and open questions.",
    explain: "Explain the main concepts of this lesson as if I am 10 years old.",
    flashcards: "Create a set of 10 Q&A flashcards from this content."
  };

  input.value = prompts[type] || "";
  autoResizeInput();
  sendMessage();
}

function updateFilesBadge() {
  const container = document.getElementById('sidebar-files');
  const badge = document.getElementById('chat-files-count');
  const list = document.getElementById('chat-files-list');
  
  if (!container || !list) return;

  if (currentConversationFiles.length > 0) {
    container.style.display = 'block';
    if (badge) {
      badge.textContent = currentConversationFiles.length;
      badge.style.display = 'inline-block';
    }
    
    list.innerHTML = currentConversationFiles.map(f => `
      <div class="chat-file-item" style="padding: 6px 8px; margin-bottom: 4px; cursor:pointer;" onclick="openViewer('${f.id}')">
        <div class="file-icon" style="font-size: 1.1rem;">${getFileIcon(f.type)}</div>
        <div class="chat-file-info">
          <h4 style="font-size: 0.8rem; margin-bottom: 0;">${escapeHtml(f.name)}</h4>
          <p style="font-size: 0.65rem;">${formatBytes(f.size || 0)} ${f.subject ? `• ${f.subject}` : ''}</p>
        </div>
      </div>
    `).join('');
  } else {
    container.style.display = 'none';
    if (badge) badge.style.display = 'none';
    list.innerHTML = '';
  }
}
document.addEventListener('DOMContentLoaded', () => {
  if (!requireAuth()) return;

  const user = getUser();
  if (user) {
    const userEl = document.getElementById('user-display');
    if (userEl) userEl.textContent = user.username || user.email;
  }

  // Load conversations
  loadConversations();

  // Input handling
  const input = document.getElementById('message-input');
  if (input) {
    input.addEventListener('input', autoResizeInput);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }

  // Create initial conversation if none exists
  ensureConversation();
});

async function ensureConversation() {
  if (!currentConversationId) {
    try {
      const res = await apiFetch('/api/conversations', {
        method: 'POST',
        body: JSON.stringify({ title: 'New Conversation' }),
      });
      if (res.ok) {
        const data = await res.json();
        currentConversationId = data.id;
        await loadConversations();
      }
    } catch (err) { console.error(err); }
  }
}

function autoResizeInput() {
  const input = document.getElementById('message-input');
  if (!input) return;
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 200) + 'px';
}

async function sendMessage() {
  const input = document.getElementById('message-input');
  const text = input?.value?.trim();
  if ((!text && pendingFiles.length === 0) || isStreaming) return;

  if (!currentConversationId) await ensureConversation();

  // Upload files first if any
  let uploadedFiles = [];
  if (pendingFiles.length > 0) {
    uploadedFiles = await uploadPendingFiles(currentConversationId);
    if (uploadedFiles.length > 0) {
      currentConversationFiles = [...currentConversationFiles, ...uploadedFiles];
      updateFilesBadge();
    }
  }

  if (!text && uploadedFiles.length === 0) return;

  // Show user message
  hideWelcomeScreen();
  if (text) {
    appendMessage('user', text, false);
    // Build file pills if files were uploaded
    if (uploadedFiles.length > 0) {
      const lastMsg = document.querySelector('.message-row.user:last-child .message-bubble');
      if (lastMsg) {
        const filesHtml = uploadedFiles.map(f =>
          `<span class="file-pill"><span class="file-icon">${getFileIcon(f.name)}</span>${f.name}</span>`
        ).join('');
        lastMsg.innerHTML += `<div class="message-files">${filesHtml}</div>`;
      }
    }
  }

  // Clear input
  input.value = '';
  input.style.height = 'auto';

  // Show typing indicator and stream via WebSocket
  const typingEl = showTyping();
  isStreaming = true;
  updateSendBtn();

  try {
    await streamChat(text, typingEl);
  } catch (err) {
    removeTyping(typingEl);
    appendMessage('assistant', '⚠️ Failed to get response: ' + err.message, false);
  }

  isStreaming = false;
  updateSendBtn();
  scrollToBottom();
}

async function streamChat(message, typingEl) {
  const token = getToken();
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${wsProtocol}//${window.location.host}/api/chat/ws/${currentConversationId}?token=${token}`;

  return new Promise((resolve, reject) => {
    const socket = new WebSocket(wsUrl);
    let fullResponse = '';
    let messageEl = null;

    socket.onopen = () => {
      socket.send(JSON.stringify({ 
        message,
        mode: isChallengeMode ? 'challenge' : 'study'
      }));
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'stream_start') {
        removeTyping(typingEl);
        messageEl = appendMessage('assistant', '', true);
        streamingMessageEl = messageEl;
      } else if (data.type === 'stream_token') {
        fullResponse += data.content;
        updateStreamingMessage(messageEl, fullResponse);
      } else if (data.type === 'stream_end') {
        // Final render with full markdown
        if (messageEl) {
          const bubble = messageEl.querySelector('.message-bubble');
          if (bubble) {
            bubble.classList.remove('stream-cursor');
            bubble.innerHTML = renderMarkdown(fullResponse);
          }
          // Add action buttons
          addMessageActions(messageEl, fullResponse);
        }
        streamingMessageEl = null;
        socket.close();
        resolve();
      } else if (data.type === 'title_update') {
        updateChatTitle(data.title);
        loadConversations();
      } else if (data.type === 'error') {
        removeTyping(typingEl);
        appendMessage('assistant', '⚠️ ' + data.content, false);
        socket.close();
        resolve();
      }
    };

    socket.onerror = (err) => {
      removeTyping(typingEl);
      // Fallback to REST API
      fallbackRestChat(message, typingEl).then(resolve).catch(reject);
    };

    socket.onclose = (event) => {
      if (!event.wasClean && !fullResponse) {
        fallbackRestChat(message, typingEl).then(resolve).catch(reject);
      }
    };

    // Timeout after 60s
    setTimeout(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.close();
        resolve();
      }
    }, 60000);
  });
}

async function fallbackRestChat(message) {
  try {
    const res = await apiFetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        conversation_id: currentConversationId,
      }),
    });
    const data = await res.json();
    if (res.ok) {
      const el = appendMessage('assistant', data.message, false);
      addMessageActions(el, data.message);
      if (data.conversation_id) currentConversationId = data.conversation_id;
    } else {
      appendMessage('assistant', '⚠️ ' + (data.detail || 'Error'), false);
    }
  } catch (err) {
    appendMessage('assistant', '⚠️ Network error: ' + err.message, false);
  }
}

function appendMessage(role, content, isStreaming) {
  const inner = document.getElementById('messages-inner');
  if (!inner) return null;

  const row = document.createElement('div');
  row.className = `message-row ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'message-avatar';
  avatar.textContent = role === 'assistant' ? '🎓' : '👤';

  const contentDiv = document.createElement('div');
  contentDiv.className = 'message-content';

  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';

  if (isStreaming) {
    bubble.classList.add('stream-cursor');
    bubble.innerHTML = '';
  } else {
    bubble.innerHTML = role === 'assistant' ? renderMarkdown(content) : escapeHtml(content).replace(/\n/g, '<br>');
  }

  contentDiv.appendChild(bubble);

  if (role === 'assistant' && !isStreaming && content) {
    addMessageActions(row, content);
  }

  row.appendChild(avatar);
  row.appendChild(contentDiv);
  inner.appendChild(row);
  scrollToBottom();
  return row;
}

function updateStreamingMessage(messageEl, text) {
  if (!messageEl) return;
  const bubble = messageEl.querySelector('.message-bubble');
  if (!bubble) return;
  // Render incrementally - simple render for streaming, full render on end
  bubble.innerHTML = renderMarkdown(text);
  scrollToBottom();
}

function addMessageActions(messageEl, content) {
  if (!messageEl) return;
  const contentDiv = messageEl.querySelector('.message-content');
  if (!contentDiv) return;

  // Check if actions already exist
  if (contentDiv.querySelector('.message-actions')) return;

  const actions = document.createElement('div');
  actions.className = 'message-actions';
  actions.innerHTML = `
    <button class="message-action-btn" onclick="copyMessageText(this)" data-text="${escapeHtml(content).replace(/"/g, '&quot;')}">📋 Copy</button>
    <button class="message-action-btn" onclick="speakText(\`${content.replace(/`/g, '\\`').replace(/\\/g, '\\\\')}\`)">🔊 Read</button>
  `;
  contentDiv.appendChild(actions);
}

function copyMessageText(btn) {
  const text = btn.getAttribute('data-text')?.replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
  navigator.clipboard.writeText(text || '').then(() => {
    btn.innerHTML = '✅ Copied';
    setTimeout(() => { btn.innerHTML = '📋 Copy'; }, 2000);
  });
}

function showTyping() {
  const inner = document.getElementById('messages-inner');
  const row = document.createElement('div');
  row.className = 'message-row assistant';
  row.id = 'typing-row';
  row.innerHTML = `
    <div class="message-avatar">🎓</div>
    <div class="message-content">
      <div class="message-bubble">
        <div class="typing-dots"><span></span><span></span><span></span></div>
      </div>
    </div>
  `;
  inner.appendChild(row);
  scrollToBottom();
  return row;
}

function removeTyping(el) {
  if (el && el.parentNode) el.remove();
  const existing = document.getElementById('typing-row');
  if (existing) existing.remove();
}

function showWelcomeScreen() {
  const welcome = document.getElementById('welcome-screen');
  if (welcome) welcome.style.display = 'flex';
}

function hideWelcomeScreen() {
  const welcome = document.getElementById('welcome-screen');
  if (welcome) welcome.style.display = 'none';
}

function clearChatUI() {
  const inner = document.getElementById('messages-inner');
  if (!inner) return;
  // Remove all messages but keep welcome screen
  const welcome = document.getElementById('welcome-screen');
  inner.innerHTML = '';
  if (welcome) inner.appendChild(welcome);
}

function scrollToBottom() {
  const container = document.getElementById('chat-messages');
  if (container) {
    requestAnimationFrame(() => {
      container.scrollTop = container.scrollHeight;
    });
  }
}

function updateSendBtn() {
  const btn = document.getElementById('send-btn');
  if (btn) {
    btn.disabled = isStreaming;
    btn.textContent = isStreaming ? '⏳' : '➤';
  }
}

function quickPrompt(text) {
  const input = document.getElementById('message-input');
  if (input) {
    input.value = text;
    autoResizeInput();
    input.focus();
  }
}

async function exportChat() {
  if (!currentConversationId) return;
  try {
    const res = await apiFetch(`/api/conversations/${currentConversationId}`);
    if (!res.ok) return;
    const data = await res.json();
    let text = `# ${data.title}\n\nExported from KHABACH AI\n\n`;
    (data.messages || []).forEach(msg => {
      const role = msg.role === 'user' ? 'You' : 'KHABACH AI';
      text += `## ${role}\n\n${msg.content}\n\n---\n\n`;
    });
    const blob = new Blob([text], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${data.title || 'chat'}.md`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error('Export failed:', err);
  }
}

function openSettings() {
  alert('Settings panel coming soon!');
}

function logout() {
  localStorage.removeItem('sf_token');
  localStorage.removeItem('sf_user');
  window.location.href = '/login';
}
