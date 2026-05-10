/**
 * KHABACH AI - Document Viewer Logic
 */

let currentViewerFile = null;

async function openViewer(fileId) {
    const viewer = document.getElementById('doc-viewer');
    if (!viewer) return;

    try {
        // Find file in our global state (loaded in app.js or sidebar.js)
        const file = currentConversationFiles.find(f => f.id === fileId);
        if (!file) return;

        currentViewerFile = file;

        // Update UI
        document.getElementById('viewer-filename').textContent = file.name;
        document.getElementById('viewer-icon').textContent = getFileIcon(file.type);
        document.getElementById('viewer-subject').textContent = file.subject || 'General';
        document.getElementById('viewer-summary').textContent = file.summary || 'Analyzing document...';
        
        const contentArea = document.getElementById('viewer-content');
        contentArea.innerHTML = '<div class="loading-spinner">Loading content...</div>';

        // Fetch full text from backend if not already present
        // Note: For now we'll assume the list endpoint might not return the full 50k chars
        // We might need a specific endpoint: GET /api/files/content/{fileId}
        const res = await apiFetch(`/api/files/content/${fileId}`);
        if (res.ok) {
            const data = await res.json();
            contentArea.innerHTML = `<div class="content-body">${escapeHtml(data.text).replace(/\n/g, '<br>')}</div>`;
        } else {
            contentArea.innerHTML = `<div class="error-text">Failed to load content.</div>`;
        }

        viewer.classList.add('active');
        document.body.classList.add('viewer-open'); // For responsive adjustments

    } catch (err) {
        console.error('Viewer error:', err);
    }
}

function closeViewer() {
    const viewer = document.getElementById('doc-viewer');
    if (viewer) viewer.classList.remove('active');
    document.body.classList.remove('viewer-open');
    currentViewerFile = null;
}

function highlightViewerText(snippet) {
    const contentArea = document.getElementById('viewer-content');
    if (!contentArea || !snippet) return;

    const body = contentArea.querySelector('.content-body');
    if (!body) return;

    // Simple highlight (v1)
    const text = body.innerHTML;
    if (text.includes(snippet)) {
        body.innerHTML = text.replace(snippet, `<mark class="highlight-ref">${snippet}</mark>`);
        // Scroll to highlight
        const mark = body.querySelector('.highlight-ref');
        if (mark) mark.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}
