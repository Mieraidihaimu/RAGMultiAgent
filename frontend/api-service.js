/**
 * API Service
 * Handles communication with the backend or mock data
 */

class ApiService {
    constructor() {
        this.API_BASE = 'http://localhost:8000';
        this.useMock = localStorage.getItem('use_mock_api') === 'true';
        console.log(`ApiService initialized. Mode: ${this.useMock ? 'MOCK' : 'REAL'}`);
    }

    setMockMode(enabled) {
        this.useMock = enabled;
        localStorage.setItem('use_mock_api', enabled);
        window.location.reload();
    }

    async request(endpoint, options = {}) {
        if (this.useMock) {
            return this.mockRequest(endpoint, options);
        }
        return this.realRequest(endpoint, options);
    }

    // Real API Implementation
    async realRequest(endpoint, options = {}) {
        const headers = authManager.getAuthHeaders();
        const response = await fetch(`${this.API_BASE}${endpoint}`, {
            ...options,
            headers: {
                ...headers,
                ...options.headers
            }
        });

        if (response.status === 401) {
            authManager.logout('Session expired');
            throw new Error('Unauthorized');
        }

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Request failed');
        }

        // Handle 204 No Content
        if (response.status === 204) {
            return null;
        }

        return response.json();
    }

    // Mock API Implementation
    async mockRequest(endpoint, options = {}) {
        console.log(`[MOCK] Request: ${options.method || 'GET'} ${endpoint}`);

        // Simulate network delay
        await new Promise(resolve => setTimeout(resolve, 500));

        // Auth endpoints
        if (endpoint === '/api/auth/login') {
            const body = JSON.parse(options.body);
            if (body.email === 'mock@example.com') {
                return {
                    access_token: 'mock-jwt-token',
                    token_type: 'bearer',
                    user_id: MOCK_DATA.user.id
                };
            }
            throw new Error('Invalid credentials (use mock@example.com)');
        }

        if (endpoint === '/api/auth/me') {
            return MOCK_DATA.user;
        }

        if (endpoint === '/api/auth/signup') {
            return {
                access_token: 'mock-jwt-token',
                token_type: 'bearer',
                user_id: MOCK_DATA.user.id,
                email: MOCK_DATA.user.email
            };
        }

        // Thoughts endpoints
        if (endpoint.match(/^\/thoughts\/[^/]+$/)) { // GET /thoughts/{user_id}
            return {
                thoughts: MOCK_DATA.thoughts,
                count: MOCK_DATA.thoughts.length
            };
        }

        if (endpoint === '/thoughts' && options.method === 'POST') {
            const body = JSON.parse(options.body);
            const newThought = {
                id: `thought-${Date.now()}`,
                user_id: MOCK_DATA.user.id,
                text: body.text,
                status: 'pending',
                created_at: new Date().toISOString(),
                processing_mode: body.processing_mode || 'single'
            };
            MOCK_DATA.thoughts.unshift(newThought);

            // Simulate processing in background
            setTimeout(() => {
                newThought.status = 'completed';
                newThought.classification = { type: 'idea', urgency: 'soon' };
                // Trigger mock SSE if we implemented it
            }, 2000);

            return newThought;
        }

        // Groups endpoints
        if (endpoint.includes('/groups')) {
            return { groups: MOCK_DATA.groups, count: MOCK_DATA.groups.length };
        }

        // Anonymous endpoints
        if (endpoint === '/anonymous/thoughts' && options.method === 'POST') {
            const body = JSON.parse(options.body);
            return {
                id: `anon-${Date.now()}`,
                status: 'pending',
                message: 'Mock anonymous thought saved',
                created_at: new Date().toISOString(),
                session_info: {
                    session_token: 'mock-session-token',
                    thoughts_remaining: 2,
                    thoughts_used: 1,
                    limit_reached: false
                }
            };
        }

        if (endpoint.match(/^\/anonymous\/thoughts\/.+/)) {
            return { thoughts: [], count: 0 };
        }

        console.warn(`[MOCK] Unhandled endpoint: ${endpoint}`);
        return {};
    }
}

const apiService = new ApiService();
