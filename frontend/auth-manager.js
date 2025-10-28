/**
 * Authentication Manager
 * Centralized auth state management with industry best practices
 * Version: 1.0.0
 */

class AuthManager {
    constructor() {
        this.API_BASE = 'http://localhost:8000';
        this.TOKEN_KEY = 'auth_token';
        this.USER_ID_KEY = 'user_id';
        this.USER_EMAIL_KEY = 'user_email';
        this.ANON_SESSION_KEY = 'anonymous_session_token';
        this.TOKEN_EXPIRY_KEY = 'token_expiry';
        this.LAST_ACTIVITY_KEY = 'last_activity';
        
        // Session timeout: 24 hours
        this.SESSION_TIMEOUT = 24 * 60 * 60 * 1000;
        // Inactivity timeout: 2 hours
        this.INACTIVITY_TIMEOUT = 2 * 60 * 60 * 1000;
        
        // Initialize activity tracking
        this.initActivityTracking();
    }

    /**
     * Initialize activity tracking to prevent session timeout
     */
    initActivityTracking() {
        // Update last activity on user interaction
        const updateActivity = () => {
            if (this.isAuthenticated()) {
                localStorage.setItem(this.LAST_ACTIVITY_KEY, Date.now().toString());
            }
        };

        // Track various user activities
        ['mousedown', 'keydown', 'scroll', 'touchstart'].forEach(event => {
            document.addEventListener(event, updateActivity, { passive: true });
        });

        // Check session validity every minute
        setInterval(() => this.validateSession(), 60000);
        
        // Also check when tab becomes visible (user switches back to tab)
        document.addEventListener('visibilitychange', async () => {
            if (!document.hidden && this.isAuthenticated()) {
                const isValid = await this.validateSession();
                if (!isValid) {
                    // Session became invalid while tab was hidden
                    this.logout('Your session has expired. Please login again.');
                }
            }
        });
    }

    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        const token = this.getToken();
        if (!token) return false;
        
        // Check if session is expired
        if (this.isSessionExpired()) {
            // Clean up expired session silently
            this.clearAuthData();
            return false;
        }
        
        return true;
    }
    
    /**
     * Clear authentication data without redirect
     */
    clearAuthData() {
        localStorage.removeItem(this.TOKEN_KEY);
        localStorage.removeItem(this.USER_ID_KEY);
        localStorage.removeItem(this.USER_EMAIL_KEY);
        localStorage.removeItem(this.TOKEN_EXPIRY_KEY);
        localStorage.removeItem(this.LAST_ACTIVITY_KEY);
        localStorage.removeItem('thought_user_id');
    }

    /**
     * Check if user is anonymous
     */
    isAnonymous() {
        return !this.isAuthenticated() && !!this.getAnonymousSession();
    }

    /**
     * Get authentication token
     */
    getToken() {
        return localStorage.getItem(this.TOKEN_KEY);
    }

    /**
     * Get user ID
     */
    getUserId() {
        return localStorage.getItem(this.USER_ID_KEY);
    }

    /**
     * Get user email
     */
    getUserEmail() {
        return localStorage.getItem(this.USER_EMAIL_KEY);
    }

    /**
     * Get anonymous session token
     */
    getAnonymousSession() {
        return localStorage.getItem(this.ANON_SESSION_KEY);
    }

    /**
     * Check if session has expired
     */
    isSessionExpired() {
        const token = this.getToken();
        if (!token) return true;

        // Check token expiry
        const expiry = localStorage.getItem(this.TOKEN_EXPIRY_KEY);
        if (expiry && Date.now() > parseInt(expiry)) {
            console.log('Session expired: token expired');
            return true;
        }

        // Check inactivity timeout
        const lastActivity = localStorage.getItem(this.LAST_ACTIVITY_KEY);
        if (lastActivity && Date.now() - parseInt(lastActivity) > this.INACTIVITY_TIMEOUT) {
            console.log('Session expired: inactivity timeout');
            return true;
        }

        return false;
    }

    /**
     * Validate current session
     */
    async validateSession() {
        if (!this.isAuthenticated()) return false;

        try {
            const response = await fetch(`${this.API_BASE}/api/auth/me`, {
                headers: this.getAuthHeaders()
            });

            if (response.status === 401 || response.status === 403) {
                // Don't call logout here to avoid redirect loops
                // Just clear the invalid token
                localStorage.removeItem(this.TOKEN_KEY);
                localStorage.removeItem(this.USER_ID_KEY);
                localStorage.removeItem(this.USER_EMAIL_KEY);
                localStorage.removeItem(this.TOKEN_EXPIRY_KEY);
                localStorage.removeItem(this.LAST_ACTIVITY_KEY);
                return false;
            }

            if (response.ok) {
                const userData = await response.json();
                // Update user data in storage
                localStorage.setItem(this.USER_ID_KEY, userData.id);
                localStorage.setItem(this.USER_EMAIL_KEY, userData.email);
                // Update activity timestamp
                localStorage.setItem(this.LAST_ACTIVITY_KEY, Date.now().toString());
                return true;
            }

            return false;
        } catch (error) {
            console.error('Session validation error:', error);
            // Network errors shouldn't invalidate the session
            return false;
        }
    }

    /**
     * Login user
     */
    async login(email, password) {
        try {
            const response = await fetch(`${this.API_BASE}/api/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Login failed');
            }

            const data = await response.json();
            
            // Store authentication data
            this.setAuthData(data.access_token, email);
            
            // Fetch and store user ID
            await this.fetchUserProfile(data.access_token);
            
            // Convert anonymous thoughts if any
            await this.convertAnonymousThoughts();

            return { success: true, data };
        } catch (error) {
            console.error('Login error:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Signup new user
     */
    async signup(userData) {
        try {
            const response = await fetch(`${this.API_BASE}/api/auth/signup`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(userData)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Signup failed');
            }

            const data = await response.json();
            
            // Store authentication data
            this.setAuthData(data.access_token, userData.email, data.user_id);
            
            // Convert anonymous thoughts if any
            await this.convertAnonymousThoughts();

            return { success: true, data };
        } catch (error) {
            console.error('Signup error:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Logout user
     */
    logout(reason = '') {
        // Close any active SSE connections
        if (window.eventSource) {
            window.eventSource.close();
            window.eventSource = null;
        }
        
        // Clear all auth-related data
        localStorage.removeItem(this.TOKEN_KEY);
        localStorage.removeItem(this.USER_ID_KEY);
        localStorage.removeItem(this.USER_EMAIL_KEY);
        localStorage.removeItem(this.TOKEN_EXPIRY_KEY);
        localStorage.removeItem(this.LAST_ACTIVITY_KEY);
        localStorage.removeItem('thought_user_id'); // Legacy compatibility
        localStorage.removeItem('analytics_enabled'); // Clear preferences
        localStorage.removeItem('marketing_enabled'); // Clear preferences

        // Clear session storage as well
        sessionStorage.clear();

        // Show logout reason if provided
        if (reason) {
            console.log('Logout reason:', reason);
        }

        // Force page reload to clear any cached state
        const redirectUrl = reason 
            ? `login.html?reason=${encodeURIComponent(reason)}`
            : 'login.html';
        
        // Use replace to prevent back button from restoring session
        window.location.replace(redirectUrl);
    }

    /**
     * Set authentication data
     */
    setAuthData(token, email, userId = null) {
        localStorage.setItem(this.TOKEN_KEY, token);
        localStorage.setItem(this.USER_EMAIL_KEY, email);
        
        if (userId) {
            localStorage.setItem(this.USER_ID_KEY, userId);
            localStorage.setItem('thought_user_id', userId); // Legacy compatibility
        }
        
        // Set token expiry (24 hours from now)
        const expiry = Date.now() + this.SESSION_TIMEOUT;
        localStorage.setItem(this.TOKEN_EXPIRY_KEY, expiry.toString());
        
        // Set initial activity timestamp
        localStorage.setItem(this.LAST_ACTIVITY_KEY, Date.now().toString());
    }

    /**
     * Fetch user profile
     */
    async fetchUserProfile(token = null) {
        try {
            const headers = token 
                ? { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
                : this.getAuthHeaders();

            const response = await fetch(`${this.API_BASE}/api/auth/me`, { headers });

            if (response.ok) {
                const userData = await response.json();
                localStorage.setItem(this.USER_ID_KEY, userData.id);
                localStorage.setItem(this.USER_EMAIL_KEY, userData.email);
                localStorage.setItem('thought_user_id', userData.id); // Legacy compatibility
                return userData;
            }
        } catch (error) {
            console.error('Error fetching user profile:', error);
        }
        return null;
    }

    /**
     * Convert anonymous thoughts to user account
     */
    async convertAnonymousThoughts() {
        const sessionToken = localStorage.getItem('pending_conversion_token') || 
                            this.getAnonymousSession();
        
        if (!sessionToken) return;

        try {
            const response = await fetch(
                `${this.API_BASE}/api/auth/convert-anonymous?session_token=${sessionToken}`,
                {
                    method: 'POST',
                    headers: this.getAuthHeaders()
                }
            );

            if (response.ok) {
                const data = await response.json();
                console.log(`Converted ${data.thoughts_converted} anonymous thoughts`);
                
                // Clean up anonymous session data
                localStorage.removeItem(this.ANON_SESSION_KEY);
                localStorage.removeItem('pending_conversion_token');
            }
        } catch (error) {
            console.error('Error converting anonymous thoughts:', error);
        }
    }

    /**
     * Get authentication headers
     */
    getAuthHeaders() {
        const token = this.getToken();
        return {
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : ''
        };
    }

    /**
     * Require authentication (redirect to login if not authenticated)
     */
    requireAuth(allowAnonymous = false) {
        if (this.isAuthenticated()) {
            return true;
        }

        if (allowAnonymous && this.isAnonymous()) {
            return true;
        }

        // Not authenticated, redirect to login
        window.location.href = 'login.html?redirect=' + encodeURIComponent(window.location.pathname);
        return false;
    }

    /**
     * Handle API errors globally
     */
    async handleApiResponse(response) {
        if (response.status === 401) {
            this.logout('Session expired');
            throw new Error('Unauthorized');
        }

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Request failed');
        }

        return response;
    }

    /**
     * Make authenticated API request
     */
    async apiRequest(endpoint, options = {}) {
        const defaultOptions = {
            headers: this.getAuthHeaders()
        };

        const response = await fetch(`${this.API_BASE}${endpoint}`, {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        });

        return this.handleApiResponse(response);
    }

    /**
     * Setup anonymous session
     */
    setupAnonymousSession(sessionToken = null) {
        if (sessionToken) {
            localStorage.setItem(this.ANON_SESSION_KEY, sessionToken);
        }
    }

    /**
     * Update anonymous session info
     */
    updateAnonymousInfo(sessionInfo) {
        if (sessionInfo && sessionInfo.session_token) {
            this.setupAnonymousSession(sessionInfo.session_token);
        }
    }
}

// Create global instance
const authManager = new AuthManager();

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AuthManager;
}
