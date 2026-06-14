/**
 * Upload page JavaScript
 * Handles drag-and-drop, file list management, and form submission.
 */
(function () {
    'use strict';

    const dropZone   = document.getElementById('drop-zone');
    const fileInput   = document.getElementById('file-input');
    const fileList    = document.getElementById('file-list');
    const fileItems   = document.getElementById('file-items');
    const clearBtn    = document.getElementById('clear-files');
    const form        = document.getElementById('upload-form');
    const submitBtn   = document.getElementById('submit-btn');
    const togglePass  = document.getElementById('toggle-pass');
    const groqInput   = document.getElementById('groq-key');

    /* ---------- DataTransfer to hold selected files ---------- */
    let selectedFiles = new DataTransfer();

    /* ---------- Drag & Drop ---------- */
    ['dragenter', 'dragover'].forEach(evt =>
        dropZone.addEventListener(evt, e => { e.preventDefault(); dropZone.classList.add('drag-over'); })
    );
    ['dragleave', 'drop'].forEach(evt =>
        dropZone.addEventListener(evt, e => { e.preventDefault(); dropZone.classList.remove('drag-over'); })
    );

    dropZone.addEventListener('drop', e => {
        const files = e.dataTransfer.files;
        addFiles(files);
    });

    /* ---------- Browse button ---------- */
    fileInput.addEventListener('change', () => {
        addFiles(fileInput.files);
    });

    /* ---------- Add files to list ---------- */
    function addFiles(files) {
        for (const f of files) {
            if (!f.name.toLowerCase().endsWith('.pdf')) {
                showTempError(`"${f.name}" is not a PDF file.`);
                continue;
            }
            // Avoid duplicates by name
            let dup = false;
            for (let i = 0; i < selectedFiles.files.length; i++) {
                if (selectedFiles.files[i].name === f.name) { dup = true; break; }
            }
            if (!dup) selectedFiles.items.add(f);
        }
        syncInput();
        renderList();
    }

    /* ---------- Sync DataTransfer → input ---------- */
    function syncInput() {
        fileInput.files = selectedFiles.files;
    }

    /* ---------- Render file list ---------- */
    function renderList() {
        fileItems.innerHTML = '';
        if (selectedFiles.files.length === 0) {
            fileList.style.display = 'none';
            return;
        }
        fileList.style.display = 'block';
        for (let i = 0; i < selectedFiles.files.length; i++) {
            const f = selectedFiles.files[i];
            const li = document.createElement('li');
            li.style.animationDelay = `${i * 0.05}s`;
            li.innerHTML = `
                <svg class="file-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                <span class="file-name">${f.name}</span>
                <span class="file-size">${formatSize(f.size)}</span>
                <button type="button" class="file-remove" data-idx="${i}" title="Remove">&times;</button>
            `;
            fileItems.appendChild(li);
        }
    }

    /* ---------- Remove file ---------- */
    fileItems.addEventListener('click', e => {
        const btn = e.target.closest('.file-remove');
        if (!btn) return;
        const idx = parseInt(btn.dataset.idx, 10);
        const newDT = new DataTransfer();
        for (let i = 0; i < selectedFiles.files.length; i++) {
            if (i !== idx) newDT.items.add(selectedFiles.files[i]);
        }
        selectedFiles = newDT;
        syncInput();
        renderList();
    });

    /* ---------- Clear all ---------- */
    clearBtn.addEventListener('click', () => {
        selectedFiles = new DataTransfer();
        syncInput();
        renderList();
    });

    /* ---------- Form submit → loading state ---------- */
    form.addEventListener('submit', () => {
        if (selectedFiles.files.length === 0) return;
        submitBtn.disabled = true;
        submitBtn.querySelector('.btn-text').style.display = 'none';
        submitBtn.querySelector('.btn-loading').style.display = 'inline-flex';
    });

    /* ---------- Show / hide password ---------- */
    togglePass.addEventListener('click', () => {
        const isPass = groqInput.type === 'password';
        groqInput.type = isPass ? 'text' : 'password';
    });

    /* ---------- Helpers ---------- */
    function formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / 1048576).toFixed(1) + ' MB';
    }

    function showTempError(msg) {
        const div = document.createElement('div');
        div.className = 'alert alert-error';
        div.innerHTML = `<span>${msg}</span><button class="alert-close" onclick="this.parentElement.remove()">&times;</button>`;
        form.prepend(div);
        setTimeout(() => div.remove(), 4000);
    }
})();
