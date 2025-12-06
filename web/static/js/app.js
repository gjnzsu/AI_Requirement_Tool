// Chatbot Web UI JavaScript

let currentConversationId = null;
let conversations = [];

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const newChatBtn = document.getElementById('newChatBtn');
const conversationsList = document.getElementById('conversationsList');
const clearAllBtn = document.getElementById('clearAllBtn');
const searchInput = document.getElementById('searchInput');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadConversations();
    setupEventListeners();
});

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
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                conversation_id: currentConversationId
            })
        });
        
        const data = await response.json();
        
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
            throw new Error(data.error || 'Failed to get response');
        }
    } catch (error) {
        console.error('Error:', error);
        
        // Remove loading indicator
        const loadingElement = document.getElementById(loadingId);
        if (loadingElement) {
            loadingElement.remove();
        }
        
        // Show error message
        addMessageToUI('assistant', `Sorry, I encountered an error: ${error.message}`);
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
        contentDiv.textContent = content;
        
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
        const response = await fetch('/api/conversations');
        const data = await response.json();
        
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
        const response = await fetch(`/api/conversations/${conversationId}`);
        const data = await response.json();
        
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
        const response = await fetch('/api/new-chat', {
            method: 'POST'
        });
        const data = await response.json();
        
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
        const response = await fetch(`/api/conversations/${conversationId}`, {
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
        const response = await fetch('/api/conversations', {
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
        const response = await fetch(`/api/conversations/${conversationId}/title`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ title: newTitle.trim() })
        });
        
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
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: userMessage,
                    conversation_id: currentConversationId
                })
            });
            
            const data = await response.json();
            
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

