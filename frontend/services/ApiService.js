/**
 * API Service
 * Centralized API communication layer
 */
class ApiService {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }

    /**
     * Get authentication headers
     */
    getHeaders() {
        if (typeof authManager !== 'undefined') {
            return authManager.getAuthHeaders();
        }
        return { 'Content-Type': 'application/json' };
    }

    /**
     * Make GET request
     */
    async get(endpoint, options = {}) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'GET',
            headers: { ...this.getHeaders(), ...options.headers },
            ...options
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return response.json();
    }

    /**
     * Make POST request
     */
    async post(endpoint, data = {}, options = {}) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'POST',
            headers: { ...this.getHeaders(), ...options.headers },
            body: JSON.stringify(data),
            ...options
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
        }

        return response.json();
    }

    /**
     * Make PUT request
     */
    async put(endpoint, data = {}, options = {}) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'PUT',
            headers: { ...this.getHeaders(), ...options.headers },
            body: JSON.stringify(data),
            ...options
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return response.json();
    }

    /**
     * Make DELETE request
     */
    async delete(endpoint, options = {}) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'DELETE',
            headers: { ...this.getHeaders(), ...options.headers },
            ...options
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return response.json();
    }
}

// Create global instance
const apiService = new ApiService();
