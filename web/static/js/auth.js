/**
 * Authentication handler for frontend.
 * Manages JWT tokens and API request authentication.
 */

const auth = {
    TOKEN_KEY: 'chatbot_auth_token',
    USER_KEY: 'chatbot_user',

    /**
     * Login user with username and password.
     * @param {string} username - Username
     * @param {string} password - Password
     * @returns {Promise<boolean>} - True if login successful
     */
    async login(username, password) {
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password })
            });

            // Check if response is JSON before parsing
            const contentType = response.headers.get('content-type');
            let data;
            
            if (contentType && contentType.includes('application/json')) {
                data = await response.json();
            } else {
                const text = await response.text();
                throw new Error(`Server returned non-JSON response: ${response.status} ${response.statusText}`);
            }

            if (response.ok && data.token) {
                // Store token and user info
                localStorage.setItem(this.TOKEN_KEY, data.token);
                if (data.user) {
                    localStorage.setItem(this.USER_KEY, JSON.stringify(data.user));
                }
                return true;
            } else {
                throw new Error(data.error || 'Login failed');
            }
        } catch (error) {
            console.error('Login error:', error);
            throw error;
        }
    },

    /**
     * Logout current user.
     */
    logout() {
        localStorage.removeItem(this.TOKEN_KEY);
        localStorage.removeItem(this.USER_KEY);
        window.location.href = '/login';
    },

    /**
     * Get stored authentication token.
     * @returns {string|null} - JWT token or null
     */
    getToken() {
        return localStorage.getItem(this.TOKEN_KEY);
    },

    /**
     * Get current user information.
     * @returns {Object|null} - User object or null
     */
    getCurrentUser() {
        const userStr = localStorage.getItem(this.USER_KEY);
        if (userStr) {
            try {
                return JSON.parse(userStr);
            } catch (e) {
                return null;
            }
        }
        return null;
    },

    /**
     * Check if user is authenticated.
     * @returns {boolean} - True if authenticated
     */
    isAuthenticated() {
        return !!this.getToken();
    },

    /**
     * Get authorization header value.
     * @returns {string|null} - Authorization header value or null
     */
    getAuthHeader() {
        const token = this.getToken();
        return token ? `Bearer ${token}` : null;
    },

    /**
     * Make authenticated API request.
     * Automatically includes authentication token.
     * @param {string} url - API endpoint
     * @param {Object} options - Fetch options
     * @returns {Promise<Response>} - Fetch response
     */
    async authenticatedFetch(url, options = {}) {
        const token = this.getToken();
        
        if (!token) {
            // Redirect to login if not authenticated
            window.location.href = '/login';
            throw new Error('Not authenticated');
        }

        // Add authorization header
        const headers = {
            ...options.headers,
            'Authorization': `Bearer ${token}`,
        };

        // Handle body - stringify if object and Content-Type is application/json
        let body = options.body;
        if (body && typeof body === 'object' && !(body instanceof FormData)) {
            const contentType = options.headers?.['Content-Type'] || options.headers?.['content-type'];
            if (contentType && contentType.includes('application/json')) {
                // Content-Type is set to JSON, so stringify the body
                body = JSON.stringify(body);
            } else if (!contentType) {
                // No Content-Type set, default to JSON and stringify
                headers['Content-Type'] = 'application/json';
                body = JSON.stringify(body);
            }
        }

        const response = await fetch(url, {
            ...options,
            headers,
            body
        });

        // Handle 401 Unauthorized - token expired or invalid
        if (response.status === 401) {
            this.logout();
            throw new Error('Session expired. Please login again.');
        }

        return response;
    },

    /**
     * Refresh current user information from server.
     * @returns {Promise<Object|null>} - Updated user object or null
     */
    async refreshUserInfo() {
        try {
            const response = await this.authenticatedFetch('/api/auth/me');
            
            // Check if response is JSON before parsing
            const contentType = response.headers.get('content-type');
            let data;
            
            if (contentType && contentType.includes('application/json')) {
                data = await response.json();
            } else {
                console.error('Server returned non-JSON response for user info');
                return null;
            }
            
            if (response.ok && data.user) {
                localStorage.setItem(this.USER_KEY, JSON.stringify(data.user));
                return data.user;
            }
            return null;
        } catch (error) {
            console.error('Error refreshing user info:', error);
            return null;
        }
    }
};

// Override fetch to automatically include auth token for all API requests
(function() {
    const originalFetch = window.fetch;
    
    window.fetch = function(url, options = {}) {
        // Only add auth token for API routes
        if (typeof url === 'string' && url.startsWith('/api/') && !url.startsWith('/api/auth/login')) {
            const token = auth.getToken();
            if (token) {
                options.headers = options.headers || {};
                options.headers['Authorization'] = `Bearer ${token}`;
            }
        }
        
        return originalFetch.call(this, url, options);
    };
})();
