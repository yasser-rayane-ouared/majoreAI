/**
 * StudyFlow AI - Sidebar & Conversation Management
 */
let conversations = [];
let currentConversationId = null;

async function loadConversations() {
  try {
    const res = await apiFetch('/api/conversations');
    if (!res.ok) return;
    const data = await res.json();
    conversations = data.conversations || [];
    renderConversations();
  } catch (err) {
    console.error('Failed to load conversations:', err);
  }
}

function renderConversations() {
  const list = document.getElementById('conversations-list');
  if (!list) return;

  if (conversations.length === 0) {
    list.innerHTML = `<div style="padding:20px;text-align:center;color:var(--text-tertiary);font-size:0.85rem;">
      <p>No conversations yet</p>
      <p style="margin-top:4px;font-size:0.78rem">Start a new chat to begin</p>
    </div>`;
    return;
  }

  // Group by date
  const today = new Date();
  const groups = { today: [], yesterday: [], week: [], older: [] };

  conversations.forEach(conv => {
    const date = new Date(conv.updated_at || conv.created_at);
    const diff = Math.floor((today - date) / 86400000);
    if (diff === 0) groups.today.push(conv);
    else if (diff === 1) groups.yesterday.push(conv);
    else if (diff < 7) groups.week.push(conv);
    else groups.older.push(conv);
  });

  let html = '';
  const renderGroup = (label, items) => {
    if (items.length === 0) return '';
    let g = `<div class="conv-group-label">${label}</div>`;
    items.forEach(conv => {
      const isActive = conv.id === currentConversationId;
      g += `<div class="conv-item ${isActive ? 'active' : ''}" onclick="switchConversation('${conv.id}')" data-conv-id="${conv.id}">
        <span class="conv-icon">💬</span>
        <span class="conv-title">${escapeHtml(conv.title || 'New Conversation')}</span>
        <div class="conv-actions">
          <button onclick="event.stopPropagation();renameConversation('${conv.id}')" title="Rename">✏️</button>
          <button onclick="event.stopPropagation();deleteConversation('${conv.id}')" title="Delete">🗑️</button>
        </div>
      </div>`;
    });
    return g;
  };

  html += renderGroup('Today', groups.today);
  html += renderGroup('Yesterday', groups.yesterday);
  html += renderGroup('This Week', groups.week);
  html += renderGroup('Older', groups.older);
  list.innerHTML = html;
}

async function createNewChat() {
  try {
    const res = await apiFetch('/api/conversations', {
      method: 'POST',
      body: JSON.stringify({ title: 'New Conversation' }),
    });
    if (!res.ok) return;
    const data = await res.json();
    currentConversationId = data.id;
    await loadConversations();
    clearChatUI();
    showWelcomeScreen();
    updateChatTitle('New Conversation');
    closeSidebar();
  } catch (err) {
    console.error('Failed to create conversation:', err);
  }
}

async function switchConversation(convId) {
  if (convId === currentConversationId) { closeSidebar(); return; }
  currentConversationId = convId;
  renderConversations();
  closeSidebar();
  await loadConversationMessages(convId);
}

async function loadConversationMessages(convId) {
  try {
    const res = await apiFetch(`/api/conversations/${convId}`);
    if (!res.ok) return;
    const data = await res.json();
    updateChatTitle(data.title || 'Conversation');
    
    // Update files badge
    currentConversationFiles = data.files || [];
    if (typeof updateFilesBadge === 'function') updateFilesBadge();

    clearChatUI();

    if (data.messages && data.messages.length > 0) {
      hideWelcomeScreen();
      data.messages.forEach(msg => {
        appendMessage(msg.role, msg.content, false);
      });
      scrollToBottom();
    } else {
      showWelcomeScreen();
    }
  } catch (err) {
    console.error('Failed to load messages:', err);
  }
}

async function renameConversation(convId) {
  const conv = conversations.find(c => c.id === convId);
  const newTitle = prompt('Rename conversation:', conv?.title || '');
  if (!newTitle || !newTitle.trim()) return;
  try {
    await apiFetch(`/api/conversations/${convId}`, {
      method: 'PUT',
      body: JSON.stringify({ title: newTitle.trim() }),
    });
    await loadConversations();
    if (convId === currentConversationId) updateChatTitle(newTitle.trim());
  } catch (err) {
    console.error('Rename failed:', err);
  }
}

async function deleteConversation(convId) {
  if (!confirm('Delete this conversation?')) return;
  try {
    await apiFetch(`/api/conversations/${convId}`, { method: 'DELETE' });
    if (convId === currentConversationId) {
      currentConversationId = null;
      clearChatUI();
      showWelcomeScreen();
      updateChatTitle('New Conversation');
    }
    await loadConversations();
  } catch (err) {
    console.error('Delete failed:', err);
  }
}

function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  sidebar.classList.toggle('open');
  overlay.classList.toggle('active');
}

function closeSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  if (sidebar) sidebar.classList.remove('open');
  if (overlay) overlay.classList.remove('active');
}

function updateChatTitle(title) {
  const el = document.getElementById('chat-title');
  if (el) el.textContent = title;
}

// Close sidebar on overlay click
document.addEventListener('DOMContentLoaded', () => {
  const overlay = document.getElementById('sidebar-overlay');
  if (overlay) overlay.addEventListener('click', closeSidebar);
});
