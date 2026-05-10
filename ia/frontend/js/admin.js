/**
 * StudyFlow AI - Admin Dashboard
 */
document.addEventListener('DOMContentLoaded', () => {
  const token = getToken();
  if (!token) { window.location.href = '/login'; return; }
  loadAdminData();
});

async function loadAdminData() {
  try {
    // Load stats
    const statsRes = await apiFetch('/api/admin/stats');
    if (statsRes.status === 403) {
      document.querySelector('.admin-content').innerHTML = '<div style="text-align:center;padding:80px 20px;"><h2>🔒 Admin Access Required</h2><p style="color:var(--text-secondary);margin-top:8px;">Your account does not have admin privileges.</p><button class="btn-primary" style="margin-top:20px;" onclick="window.location.href=\'/\'">Back to Chat</button></div>';
      return;
    }
    if (statsRes.ok) {
      const stats = await statsRes.json();
      document.getElementById('stat-users').textContent = formatNumber(stats.users);
      document.getElementById('stat-conversations').textContent = formatNumber(stats.conversations);
      document.getElementById('stat-messages').textContent = formatNumber(stats.messages);
      document.getElementById('stat-files').textContent = formatNumber(stats.files);
      document.getElementById('stat-tokens').textContent = formatNumber(stats.total_tokens);
      document.getElementById('stat-storage').textContent = formatBytes(stats.storage_bytes);
    }

    // Load users
    const usersRes = await apiFetch('/api/admin/users');
    if (usersRes.ok) {
      const data = await usersRes.json();
      const tbody = document.getElementById('users-tbody');
      tbody.innerHTML = (data.users || []).map(u => `<tr>
        <td><strong>${escapeHtml(u.username)}</strong></td>
        <td>${escapeHtml(u.email)}</td>
        <td><span class="role-badge role-${u.role}">${u.role}</span></td>
        <td>${u.auth_provider}</td>
        <td>${u.message_count}</td>
        <td>${timeAgo(u.created_at)}</td>
        <td>${u.role !== 'admin' ? `<button class="btn-ghost" onclick="deactivateUser('${u.id}')" style="font-size:0.75rem;padding:4px 8px;">Deactivate</button>` : ''}</td>
      </tr>`).join('');
    }

    // Load files
    const filesRes = await apiFetch('/api/admin/files');
    if (filesRes.ok) {
      const data = await filesRes.json();
      const tbody = document.getElementById('files-tbody');
      tbody.innerHTML = (data.files || []).map(f => `<tr>
        <td>${escapeHtml(f.name)}</td>
        <td>${f.type}</td>
        <td>${formatBytes(f.size)}</td>
        <td>${f.indexed ? '✅' : '❌'}</td>
        <td>${timeAgo(f.created_at)}</td>
      </tr>`).join('');
    }
  } catch (err) {
    console.error('Admin data error:', err);
  }
}

async function deactivateUser(userId) {
  if (!confirm('Deactivate this user?')) return;
  try {
    await apiFetch(`/api/admin/users/${userId}`, { method: 'DELETE' });
    loadAdminData();
  } catch (err) {
    console.error('Deactivate failed:', err);
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}
