/**
 * Thought Model
 * Handles thought data and API interactions
 */
class ThoughtModel {
    constructor(apiService) {
        this.api = apiService;
        this.thoughts = [];
        this.filters = {
            status: 'all',
            priority: 'all',
            category: 'all',
            sortBy: 'created_desc'
        };
    }

    /**
     * Fetch thoughts for user
     */
    async fetchThoughts(userId, isAnonymous = false) {
        try {
            let data;
            if (isAnonymous) {
                const sessionToken = authManager.getAnonymousSession();
                if (!sessionToken) {
                    this.thoughts = [];
                    return { success: true, thoughts: [] };
                }
                data = await this.api.get(`/anonymous/thoughts`, {
                    headers: { 'X-Anonymous-Session': sessionToken }
                });
            } else {
                data = await this.api.get(`/thoughts?user_id=${userId}`);
            }

            this.thoughts = data.thoughts || [];
            return { success: true, thoughts: this.thoughts };
        } catch (error) {
            console.error('Error fetching thoughts:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Create new thought
     */
    async createThought(thoughtData, isAnonymous = false) {
        try {
            let result;
            if (isAnonymous) {
                const sessionToken = authManager.getAnonymousSession();
                const endpoint = sessionToken 
                    ? `/anonymous/thoughts/${sessionToken}`
                    : '/anonymous/thoughts';
                result = await this.api.post(endpoint, thoughtData, {
                    headers: sessionToken ? { 'X-Anonymous-Session': sessionToken } : {}
                });
            } else {
                result = await this.api.post('/thoughts', thoughtData);
            }

            // Add to local cache
            if (result.thought) {
                this.thoughts.unshift(result.thought);
            }

            return { success: true, data: result };
        } catch (error) {
            console.error('Error creating thought:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Trigger thought processing
     */
    async processThought(thoughtId, processingMode, groupId = null) {
        try {
            const payload = {
                thought_id: thoughtId,
                processing_mode: processingMode
            };

            if (groupId) {
                payload.group_id = groupId;
            }

            const result = await this.api.post('/process/trigger', payload);
            return { success: true, data: result };
        } catch (error) {
            console.error('Error processing thought:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Update thought in local cache
     */
    updateThought(thoughtId, updates) {
        const index = this.thoughts.findIndex(t => t.id === thoughtId);
        if (index !== -1) {
            this.thoughts[index] = { ...this.thoughts[index], ...updates };
        }
    }

    /**
     * Get filtered and sorted thoughts
     */
    getFilteredThoughts() {
        let filtered = [...this.thoughts];

        // Apply status filter
        if (this.filters.status !== 'all') {
            filtered = filtered.filter(t => t.status === this.filters.status);
        }

        // Apply priority filter
        if (this.filters.priority !== 'all') {
            filtered = filtered.filter(t => t.priority === this.filters.priority);
        }

        // Apply category filter
        if (this.filters.category !== 'all') {
            filtered = filtered.filter(t => t.category === this.filters.category);
        }

        // Apply sorting
        filtered.sort((a, b) => {
            switch (this.filters.sortBy) {
                case 'created_desc':
                    return new Date(b.created_at) - new Date(a.created_at);
                case 'created_asc':
                    return new Date(a.created_at) - new Date(b.created_at);
                case 'priority_desc':
                    const priorityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
                    return (priorityOrder[b.priority] || 0) - (priorityOrder[a.priority] || 0);
                case 'value_desc':
                    return (b.value_score || 0) - (a.value_score || 0);
                default:
                    return 0;
            }
        });

        return filtered;
    }

    /**
     * Set filters
     */
    setFilters(filters) {
        this.filters = { ...this.filters, ...filters };
    }

    /**
     * Reset filters
     */
    resetFilters() {
        this.filters = {
            status: 'all',
            priority: 'all',
            category: 'all',
            sortBy: 'created_desc'
        };
    }

    /**
     * Get all thoughts
     */
    getAllThoughts() {
        return this.thoughts;
    }

    /**
     * Clear thoughts cache
     */
    clear() {
        this.thoughts = [];
    }
}
