/**
 * StudyFlow AI - File Upload with Drag & Drop
 */
let pendingFiles = [];

function initFileUpload() {
  const fileInput = document.getElementById('file-input');
  const chatMain = document.querySelector('.chat-main');
  const dropOverlay = document.getElementById('drop-overlay');

  if (fileInput) {
    fileInput.addEventListener('change', (e) => {
      addFiles(Array.from(e.target.files));
      fileInput.value = '';
    });
  }

  // Drag and drop
  if (chatMain && dropOverlay) {
    let dragCounter = 0;
    chatMain.addEventListener('dragenter', (e) => {
      e.preventDefault();
      dragCounter++;
      dropOverlay.classList.add('active');
    });
    chatMain.addEventListener('dragleave', (e) => {
      e.preventDefault();
      dragCounter--;
      if (dragCounter <= 0) { dropOverlay.classList.remove('active'); dragCounter = 0; }
    });
    chatMain.addEventListener('dragover', (e) => e.preventDefault());
    chatMain.addEventListener('drop', (e) => {
      e.preventDefault();
      dragCounter = 0;
      dropOverlay.classList.remove('active');
      if (e.dataTransfer.files.length > 0) {
        addFiles(Array.from(e.dataTransfer.files));
      }
    });
    // Also handle on overlay itself
    dropOverlay.addEventListener('dragover', (e) => e.preventDefault());
    dropOverlay.addEventListener('drop', (e) => {
      e.preventDefault();
      dragCounter = 0;
      dropOverlay.classList.remove('active');
      if (e.dataTransfer.files.length > 0) {
        addFiles(Array.from(e.dataTransfer.files));
      }
    });
  }
}

function addFiles(files) {
  files.forEach(file => {
    // Check for duplicates
    if (!pendingFiles.some(f => f.name === file.name && f.size === file.size)) {
      pendingFiles.push(file);
    }
  });
  updateFilePreview();
}

function removeFile(index) {
  pendingFiles.splice(index, 1);
  updateFilePreview();
}

function clearFiles() {
  pendingFiles = [];
  updateFilePreview();
}

function updateFilePreview() {
  const bar = document.getElementById('file-preview-bar');
  if (!bar) return;

  if (pendingFiles.length === 0) {
    bar.classList.remove('has-files');
    bar.innerHTML = '';
    return;
  }

  bar.classList.add('has-files');
  bar.innerHTML = pendingFiles.map((file, i) => {
    const icon = getFileIcon(file.name);
    const size = formatBytes(file.size);
    return `<div class="file-preview-item">
      <span>${icon}</span>
      <span>${file.name.length > 25 ? file.name.substring(0, 22) + '...' : file.name}</span>
      <span style="color:var(--text-tertiary);font-size:0.7rem">${size}</span>
      <button class="remove-file" onclick="removeFile(${i})" title="Remove">✕</button>
    </div>`;
  }).join('');
}

function getFileIcon(name) {
  const ext = name.split('.').pop().toLowerCase();
  const icons = {
    pdf: '📄', docx: '📝', doc: '📝', txt: '📃', md: '📋',
    pptx: '📊', ppt: '📊', csv: '📈', xlsx: '📈',
    png: '🖼️', jpg: '🖼️', jpeg: '🖼️', gif: '🎬', webp: '🖼️',
    zip: '📦', rar: '📦',
    py: '🐍', js: '⚡', ts: '⚡', jsx: '⚛️', tsx: '⚛️',
    java: '☕', cpp: '🔧', c: '🔧', cs: '🔷', go: '🚀',
    rb: '💎', php: '🐘', swift: '🍎', rs: '🦀', kt: '📱',
    sql: '💾', html: '🌐', css: '🎨', json: '📊', xml: '📋',
    yaml: '📋', yml: '📋', sh: '🖥️',
  };
  return icons[ext] || '📎';
}

async function uploadPendingFiles(conversationId) {
  if (pendingFiles.length === 0) return [];
  const formData = new FormData();
  formData.append('conversation_id', conversationId);
  pendingFiles.forEach(file => formData.append('files', file));

  try {
    const res = await apiFetch('/api/files/upload', { method: 'POST', body: formData });
    const data = await res.json();
    clearFiles();
    return data.files || [];
  } catch (err) {
    console.error('File upload error:', err);
    return [];
  }
}

document.addEventListener('DOMContentLoaded', initFileUpload);
