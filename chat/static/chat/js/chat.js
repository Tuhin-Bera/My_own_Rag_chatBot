/**
 * Chat page JavaScript
 * Handles AJAX messaging, auto-scroll, textarea auto-resize,
 * basic markdown rendering, and sidebar toggle.
 */
(function () {
    'use strict';

    const form       = document.getElementById('chat-form');
    const input      = document.getElementById('chat-input');
    const sendBtn    = document.getElementById('send-btn');
    const msgList    = document.getElementById('messages');
    const container  = document.getElementById('messages-container');
    const sidebar    = document.getElementById('sidebar');
    const sidebarBtn = document.getElementById('sidebar-toggle');

    const API_URL    = window.CHAT_API_URL;
    const CSRF       = window.CSRF_TOKEN;

    let isProcessing = false;

    /* ---------- Send message ---------- */
    form.addEventListener('submit', e => {
        e.preventDefault();
        sendMessage();
    });

    function sendMessage() {
        const text = input.value.trim();
        if (!text || isProcessing) return;

        isProcessing = true;
        sendBtn.disabled = true;

        // Append user message
        appendMessage('user', text);
        input.value = '';
        autoResize();

        // Show typing indicator
        const typingEl = appendTyping();

        // Call API
        fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF,
            },
            body: JSON.stringify({ question: text }),
        })
        .then(res => res.json())
        .then(data => {
            typingEl.remove();
            if (data.error) {
                appendMessage('assistant', '⚠️ ' + data.error, true);
            } else {
                appendMessage('assistant', data.answer);
            }
        })
        .catch(err => {
            typingEl.remove();
            appendMessage('assistant', '⚠️ Network error. Please try again.', true);
            console.error(err);
        })
        .finally(() => {
            isProcessing = false;
            sendBtn.disabled = false;
            input.focus();
        });
    }

    /* ---------- Append a message bubble ---------- */
    function appendMessage(role, text, isError) {
        const div = document.createElement('div');
        div.className = `message ${role}-message fade-in`;

        const avatarSVG = role === 'user'
            ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>'
            : '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>';

        const senderName = role === 'user' ? 'You' : 'DocuMind AI';
        const renderedText = role === 'assistant' ? renderMarkdown(text) : escapeHtml(text);

        div.innerHTML = `
            <div class="message-avatar ${role}-avatar">${avatarSVG}</div>
            <div class="message-content">
                <div class="message-sender">${senderName}</div>
                <div class="message-text${isError ? ' error-text' : ''}">${renderedText}</div>
            </div>
        `;

        msgList.appendChild(div);
        scrollToBottom();
    }

    /* ---------- Typing indicator ---------- */
    function appendTyping() {
        const div = document.createElement('div');
        div.className = 'message assistant-message fade-in';
        div.innerHTML = `
            <div class="message-avatar assistant-avatar">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
            </div>
            <div class="message-content">
                <div class="message-sender">DocuMind AI</div>
                <div class="typing-indicator">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                </div>
            </div>
        `;
        msgList.appendChild(div);
        scrollToBottom();
        return div;
    }

    /* ---------- Auto-scroll ---------- */
    function scrollToBottom() {
        requestAnimationFrame(() => {
            container.scrollTop = container.scrollHeight;
        });
    }

    /* ---------- Textarea auto-resize ---------- */
    input.addEventListener('input', autoResize);
    function autoResize() {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    }

    /* ---------- Enter to send, Shift+Enter for newline ---------- */
    input.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    /* ---------- Sidebar toggle (mobile) ---------- */
    sidebarBtn.addEventListener('click', () => {
        sidebar.classList.toggle('open');
    });
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', e => {
        if (sidebar.classList.contains('open') &&
            !sidebar.contains(e.target) &&
            !sidebarBtn.contains(e.target)) {
            sidebar.classList.remove('open');
        }
    });

    /* ---------- Basic Markdown rendering ---------- */
    function renderMarkdown(text) {
        let html = escapeHtml(text);

        // Bold **text**
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

        // Italic *text*
        html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

        // Inline code `code`
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

        // Unordered lists (lines starting with - or *)
        html = html.replace(/^[\-\*]\s+(.+)$/gm, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');

        // Numbered lists
        html = html.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');

        // Paragraphs (double newline)
        html = html.replace(/\n\n/g, '</p><p>');
        html = '<p>' + html + '</p>';

        // Single newlines → <br>
        html = html.replace(/\n/g, '<br>');

        // Clean up empty tags
        html = html.replace(/<p><\/p>/g, '');
        html = html.replace(/<p><br>/g, '<p>');

        return html;
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    /* ---------- Initial scroll ---------- */
    scrollToBottom();

})();
