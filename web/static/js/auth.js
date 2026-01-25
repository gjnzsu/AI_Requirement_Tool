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
                console.log('[Auth] Login successful, storing token...');
                localStorage.setItem(this.TOKEN_KEY, data.token);
                if (data.user) {
                    localStorage.setItem(this.USER_KEY, JSON.stringify(data.user));
                }
                // Verify token was stored
                const storedToken = localStorage.getItem(this.TOKEN_KEY);
                console.log('[Auth] Token stored:', storedToken ? storedToken.substring(0, 20) + '...' : 'FAILED');
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
            console.error('[Auth] No token available for request:', url);
            // Redirect to login if not authenticated
            window.location.href = '/login';
            throw new Error('Not authenticated');
        }

        // Properly handle headers - ensure it's always an object
        const existingHeaders = options.headers || {};
        
        // Convert Headers object to plain object if needed
        let headersObj = {};
        if (existingHeaders instanceof Headers) {
            existingHeaders.forEach((value, key) => {
                headersObj[key] = value;
            });
        } else if (existingHeaders && typeof existingHeaders === 'object') {
            headersObj = { ...existingHeaders };
        }

        // Always add Authorization header
        headersObj['Authorization'] = `Bearer ${token}`;

        // Handle body - stringify if object and Content-Type is application/json
        let body = options.body;
        if (body && typeof body === 'object' && !(body instanceof FormData)) {
            const contentType = headersObj['Content-Type'] || headersObj['content-type'];
            if (contentType && contentType.includes('application/json')) {
                // Content-Type is set to JSON, so stringify the body
                body = JSON.stringify(body);
            } else if (!contentType) {
                // No Content-Type set, default to JSON and stringify
                headersObj['Content-Type'] = 'application/json';
                body = JSON.stringify(body);
            }
        }

        // Create new options object with proper headers
        const fetchOptions = {
            ...options,
            headers: headersObj,
            body: body
        };

        console.log('[Auth] Making authenticated request:', url, 'with token:', token.substring(0, 20) + '...');

        const response = await fetch(url, fetchOptions);

        // Handle 401 Unauthorized - token expired or invalid
        if (response.status === 401) {
            console.error('[Auth] 401 Unauthorized for:', url);
            console.error('[Auth] Response status:', response.status, response.statusText);
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
// This is a fallback for any direct fetch() calls (not through authenticatedFetch)
(function() {
    const originalFetch = window.fetch;
    
    window.fetch = function(url, options) {
        // Ensure options is an object
        options = options || {};
        
        // Only add auth token for API routes (except login)
        if (typeof url === 'string' && url.startsWith('/api/') && !url.startsWith('/api/auth/login')) {
            const token = auth.getToken();
            if (token) {
                // Ensure headers object exists
                if (!options.headers) {
                    options.headers = {};
                }
                
                // Check if Authorization header is already set (e.g., by authenticatedFetch)
                let hasAuth = false;
                if (options.headers instanceof Headers) {
                    hasAuth = options.headers.has('Authorization');
                    if (!hasAuth) {
                        options.headers.set('Authorization', `Bearer ${token}`);
                    }
                } else {
                    // Plain object - check if Authorization already exists
                    hasAuth = options.headers && options.headers['Authorization'];
                    if (!hasAuth) {
                        // Create new object to avoid mutation
                        options.headers = {
                            ...options.headers,
                            'Authorization': `Bearer ${token}`
                        };
                    }
                    // If Authorization already exists, don't overwrite it
                }
            }
        }
        
        return originalFetch.call(this, url, options);
    };
})();
