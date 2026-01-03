// Chatbot Web UI JavaScript

let currentConversationId = null;
let conversations = [];
let currentModel = 'openai'; // Default model

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const newChatBtn = document.getElementById('newChatBtn');
const conversationsList = document.getElementById('conversationsList');
const clearAllBtn = document.getElementById('clearAllBtn');
const searchInput = document.getElementById('searchInput');
const modelSelect = document.getElementById('modelSelect');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadConversations();
    loadCurrentModel();
    setupEventListeners();
});

// Load current model from backend
async function loadCurrentModel() {
    try {
        const response = await auth.authenticatedFetch('/api/current-model');
        
        // Check if response is JSON before parsing
        const contentType = response.headers.get('content-type');
        let data;
        
        if (contentType && contentType.includes('application/json')) {
            data = await response.json();
        } else {
            throw new Error('Server returned non-JSON response');
        }
        
        if (response.ok && data.model) {
            // Check if model is supported
            if (data.available_models.includes(data.model)) {
                currentModel = data.model;
                if (modelSelect) {
                    modelSelect.value = data.model;
                }
                // Also update localStorage
                localStorage.setItem('selectedModel', data.model);
            }
        }
    } catch (error) {
        console.error('Error loading current model:', error);
        // Fallback to localStorage or default
        const savedModel = localStorage.getItem('selectedModel');
        if (savedModel && (savedModel === 'openai' || savedModel === 'deepseek')) {
            currentModel = savedModel;
            if (modelSelect) {
                modelSelect.value = savedModel;
            }
        }
    }
}

// Event Listeners
function setupEventListeners() {
    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    newChatBtn.addEventListener('click', createNewChat);
    clearAllBtn.addEventListener('click', clearAllConversations);
    searchInput.addEventListener('input', filterConversations);
    
    // Model selector change handler
    if (modelSelect) {
        modelSelect.addEventListener('change', handleModelChange);
    }
}

// Handle model selection change
async function handleModelChange(event) {
    const selectedModel = event.target.value;
    currentModel = selectedModel;
    
    // Save to localStorage for persistence
    localStorage.setItem('selectedModel', selectedModel);
    
    // Show notification
    const notification = document.createElement('div');
    notification.className = 'model-change-notification';
    notification.textContent = `Model switched to ${selectedModel.charAt(0).toUpperCase() + selectedModel.slice(1)}`;
    document.body.appendChild(notification);
    
    // Remove notification after 2 seconds
    setTimeout(() => {
        notification.remove();
    }, 2000);
}

// Send message
async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;
    
    // Clear input
    chatInput.value = '';
    sendBtn.disabled = true;
    
    // Remove welcome message if present
    const welcomeMsg = chatMessages.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }
    
    // Add user message to UI
    addMessageToUI('user', message);
    
    // Show loading indicator
    const loadingId = addMessageToUI('assistant', '', true);
    
    try {
        const response = await auth.authenticatedFetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: {
                message: message,
                conversation_id: currentConversationId,
                model: currentModel
            }
        });
        
        // Check if response is JSON before parsing
        const contentType = response.headers.get('content-type');
        let data;
        
        if (contentType && contentType.includes('application/json')) {
            data = await response.json();
        } else {
            // If not JSON, try to get text and create error
            const text = await response.text();
            throw new Error(`Server returned non-JSON response: ${response.status} ${response.statusText}`);
        }
        
        if (response.ok) {
            // Update current conversation ID
            currentConversationId = data.conversation_id;
            
            // Remove loading indicator
            const loadingElement = document.getElementById(loadingId);
            if (loadingElement) {
                loadingElement.remove();
            }
            
            // Add assistant response
            addMessageToUI('assistant', data.response);
            
            // Reload conversations list to update titles
            loadConversations();
        } else {
            throw new Error(data.error || `Failed to get response: ${response.status} ${response.statusText}`);
        }
    } catch (error) {
        console.error('Error:', error);
        
        // Remove loading indicator
        const loadingElement = document.getElementById(loadingId);
        if (loadingElement) {
            loadingElement.remove();
        }
        
        // Show error message
        let errorMessage = error.message;
        if (error.message.includes('Failed to decode JSON')) {
            errorMessage = 'Server returned an invalid response. Please check your authentication and try again.';
        }
        addMessageToUI('assistant', `Sorry, I encountered an error: ${errorMessage}`);
    } finally {
        sendBtn.disabled = false;
        chatInput.focus();
    }
}

// Add message to UI
function addMessageToUI(role, content, isLoading = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const messageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    messageDiv.id = messageId;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    
    if (role === 'user') {
        avatar.textContent = 'RG';
    } else {
        avatar.innerHTML = '<i class="fas fa-robot"></i>';
    }
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    if (isLoading) {
        contentDiv.innerHTML = '<div class="loading"><span></span><span></span><span></span></div>';
    } else {
        // Format content with proper line breaks and preserve formatting
        const formattedContent = formatMessageContent(content);
        contentDiv.innerHTML = formattedContent;
        
        // Add actions for assistant messages
        if (role === 'assistant') {
            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'message-actions';
            actionsDiv.innerHTML = `
                <button onclick="copyMessage('${messageId}')" title="Copy">
                    <i class="fas fa-copy"></i>
                </button>
                <button onclick="regenerateMessage('${messageId}')" title="Regenerate">
                    <i class="fas fa-redo"></i>
                </button>
            `;
            messageDiv.appendChild(actionsDiv);
        }
    }
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
    
    return messageId;
}

// Load conversations list
async function loadConversations() {
    try {
        const response = await auth.authenticatedFetch('/api/conversations');
        
        // Check if response is JSON before parsing
        const contentType = response.headers.get('content-type');
        let data;
        
        if (contentType && contentType.includes('application/json')) {
            data = await response.json();
        } else {
            console.error('Server returned non-JSON response for conversations');
            return;
        }
        
        if (response.ok) {
            conversations = data.conversations;
            renderConversationsList();
        }
    } catch (error) {
        console.error('Error loading conversations:', error);
    }
}

// Render conversations list
function renderConversationsList(filtered = null) {
    const list = filtered || conversations;
    conversationsList.innerHTML = '';
    
    if (list.length === 0) {
        conversationsList.innerHTML = '<div style="padding: 20px; text-align: center; color: #9ca3af;">No conversations yet</div>';
        return;
    }
    
    list.forEach(conv => {
        const item = document.createElement('div');
        item.className = `conversation-item ${conv.id === currentConversationId ? 'active' : ''}`;
        item.innerHTML = `
            <i class="fas fa-comment"></i>
            <span class="title">${escapeHtml(conv.title)}</span>
            <div class="actions">
                <button onclick="deleteConversation('${conv.id}')" title="Delete">
                    <i class="fas fa-trash"></i>
                </button>
                <button onclick="editConversationTitle('${conv.id}')" title="Edit">
                    <i class="fas fa-edit"></i>
                </button>
            </div>
        `;
        
        item.addEventListener('click', (e) => {
            if (!e.target.closest('.actions')) {
                loadConversation(conv.id);
            }
        });
        
        conversationsList.appendChild(item);
    });
}

// Load a specific conversation
async function loadConversation(conversationId) {
    try {
        const response = await auth.authenticatedFetch(`/api/conversations/${conversationId}`);
        
        // Check if response is JSON before parsing
        const contentType = response.headers.get('content-type');
        let data;
        
        if (contentType && contentType.includes('application/json')) {
            data = await response.json();
        } else {
            console.error('Server returned non-JSON response for conversation');
            return;
        }
        
        if (response.ok) {
            currentConversationId = conversationId;
            
            // Clear current messages
            chatMessages.innerHTML = '';
            
            // Load messages
            const conversation = data.conversation;
            conversation.messages.forEach(msg => {
                addMessageToUI(msg.role, msg.content);
            });
            
            // Update active conversation in list
            loadConversations();
            
            scrollToBottom();
        }
    } catch (error) {
        console.error('Error loading conversation:', error);
    }
}

// Create new chat
async function createNewChat() {
    try {
        const response = await auth.authenticatedFetch('/api/new-chat', {
            method: 'POST'
        });
        
        // Check if response is JSON before parsing
        const contentType = response.headers.get('content-type');
        let data;
        
        if (contentType && contentType.includes('application/json')) {
            data = await response.json();
        } else {
            console.error('Server returned non-JSON response for new chat');
            return;
        }
        
        if (response.ok) {
            currentConversationId = data.conversation_id;
            chatMessages.innerHTML = '<div class="welcome-message"><h2>Welcome to CHAT A.I+</h2><p>Start a conversation by typing a message below</p></div>';
            loadConversations();
            chatInput.focus();
        }
    } catch (error) {
        console.error('Error creating new chat:', error);
    }
}

// Delete conversation
async function deleteConversation(conversationId) {
    if (!confirm('Are you sure you want to delete this conversation?')) {
        return;
    }
    
    try {
        const response = await auth.authenticatedFetch(`/api/conversations/${conversationId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            if (conversationId === currentConversationId) {
                createNewChat();
            } else {
                loadConversations();
            }
        }
    } catch (error) {
        console.error('Error deleting conversation:', error);
    }
}

// Clear all conversations
async function clearAllConversations() {
    if (!confirm('Are you sure you want to clear all conversations?')) {
        return;
    }
    
    try {
        const response = await auth.authenticatedFetch('/api/conversations', {
            method: 'DELETE'
        });
        
        if (response.ok) {
            conversations = [];
            currentConversationId = null;
            chatMessages.innerHTML = '<div class="welcome-message"><h2>Welcome to CHAT A.I+</h2><p>Start a conversation by typing a message below</p></div>';
            loadConversations();
        }
    } catch (error) {
        console.error('Error clearing conversations:', error);
    }
}

// Edit conversation title
async function editConversationTitle(conversationId) {
    const conv = conversations.find(c => c.id === conversationId);
    if (!conv) return;
    
    const newTitle = prompt('Enter new title:', conv.title);
    if (!newTitle || newTitle.trim() === '') return;
    
    try {
        const response = await auth.authenticatedFetch(`/api/conversations/${conversationId}/title`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: { title: newTitle.trim() }
        });
        
        // Check if response is JSON before parsing (for error handling)
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            if (!response.ok && data.error) {
                console.error('Error updating title:', data.error);
            }
        }
        
        if (response.ok) {
            loadConversations();
        }
    } catch (error) {
        console.error('Error updating title:', error);
    }
}

// Filter conversations
function filterConversations() {
    const searchTerm = searchInput.value.toLowerCase().trim();
    
    if (!searchTerm) {
        renderConversationsList();
        return;
    }
    
    const filtered = conversations.filter(conv => 
        conv.title.toLowerCase().includes(searchTerm)
    );
    
    renderConversationsList(filtered);
}

// Copy message
function copyMessage(messageId) {
    const messageElement = document.getElementById(messageId);
    const content = messageElement.querySelector('.message-content').textContent;
    
    navigator.clipboard.writeText(content).then(() => {
        // Show feedback
        const btn = messageElement.querySelector('.message-actions button');
        const originalHTML = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-check"></i>';
        setTimeout(() => {
            btn.innerHTML = originalHTML;
        }, 2000);
    });
}

// Regenerate message
async function regenerateMessage(messageId) {
    const messageElement = document.getElementById(messageId);
    const content = messageElement.querySelector('.message-content').textContent;
    
    // Remove the message
    messageElement.remove();
    
    // Get the previous user message
    const messages = Array.from(chatMessages.querySelectorAll('.message'));
    const userMessageIndex = messages.findIndex(msg => msg.id === messageId) - 1;
    
    if (userMessageIndex >= 0 && messages[userMessageIndex].classList.contains('user')) {
        const userMessage = messages[userMessageIndex].querySelector('.message-content').textContent;
        
        // Show loading
        const loadingId = addMessageToUI('assistant', '', true);
        
        try {
            const response = await auth.authenticatedFetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: {
                    message: userMessage,
                    conversation_id: currentConversationId,
                    model: currentModel
                }
            });
            
            // Check if response is JSON before parsing
            const contentType = response.headers.get('content-type');
            let data;
            
            if (contentType && contentType.includes('application/json')) {
                data = await response.json();
            } else {
                throw new Error('Server returned non-JSON response');
            }
            
            if (response.ok) {
                const loadingElement = document.getElementById(loadingId);
                if (loadingElement) {
                    loadingElement.remove();
                }
                addMessageToUI('assistant', data.response);
            }
        } catch (error) {
            console.error('Error regenerating:', error);
            const loadingElement = document.getElementById(loadingId);
            if (loadingElement) {
                loadingElement.remove();
            }
            addMessageToUI('assistant', `Error: ${error.message}`);
        }
    }
}

// Scroll to bottom
function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Format message content with proper line breaks and markdown-like formatting
function formatMessageContent(content) {
    if (!content) return '';
    
    // Escape HTML first
    let formatted = escapeHtml(content);
    
    // Convert markdown-style formatting
    // Bold text: **text** -> <strong>text</strong>
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    
    // Headers: ### Header -> <h3>Header</h3>
    formatted = formatted.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    formatted = formatted.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    formatted = formatted.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    
    // Links: [text](url) -> <a href="url">text</a>
    formatted = formatted.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    
    // Bullet points: - item or → item -> <li>item</li>
    formatted = formatted.replace(/^[-•→]\s+(.+)$/gm, '<li>$1</li>');
    
    // Wrap consecutive list items in <ul>
    formatted = formatted.replace(/(<li>.*<\/li>\n?)+/g, function(match) {
        return '<ul>' + match + '</ul>';
    });
    
    // Numbered lists: 1. item -> <li>item</li>
    formatted = formatted.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');
    
    // Code blocks: ```code``` -> <pre><code>code</code></pre>
    formatted = formatted.replace(/```(\w+)?\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    
    // Inline code: `code` -> <code>code</code>
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // Preserve line breaks
    formatted = formatted.replace(/\n/g, '<br>');
    
    return formatted;
}

