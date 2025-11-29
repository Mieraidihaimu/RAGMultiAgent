/**
 * Thought View
 * Handles thought list rendering and UI updates
 */
class ThoughtView {
    constructor() {
        this.container = null;
        this.countElement = null;
    }

    /**
     * Initialize view with DOM elements
     */
    init(containerId = 'thoughtsList', countId = 'thoughtCount') {
        this.container = document.getElementById(containerId);
        this.countElement = document.getElementById(countId);
    }

    /**
     * Render thoughts list
     */
    render(thoughts) {
        if (!this.container) return;

        this.updateCount(thoughts.length);

        if (thoughts.length === 0) {
            this.renderEmpty();
            return;
        }

        this.container.innerHTML = thoughts.map(thought => this.renderThought(thought)).join('');
    }

    /**
     * Render empty state
     */
    renderEmpty() {
        this.container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">💭</div>
                <p class="empty-text">No thoughts yet. Share your first thought above!</p>
            </div>
        `;
    }

    /**
     * Render loading state
     */
    renderLoading() {
        if (!this.container) return;
        this.container.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <p>Loading thoughts...</p>
            </div>
        `;
    }

    /**
     * Render single thought card
     */
    renderThought(thought) {
        const statusClass = thought.status || 'pending';
        const priorityClass = thought.priority || 'medium';
        const categoryClass = thought.category || 'general';

        return `
            <div class="thought-card ${statusClass}" data-thought-id="${thought.id}">
                <div class="thought-header">
                    <div class="thought-meta">
                        <span class="status-badge ${statusClass}">${this.formatStatus(thought.status)}</span>
                        <span class="priority-badge ${priorityClass}">${this.formatPriority(thought.priority)}</span>
                        <span class="category-badge ${categoryClass}">${this.formatCategory(thought.category)}</span>
                    </div>
                    <span class="thought-date">${this.formatDate(thought.created_at)}</span>
                </div>
                
                <div class="thought-content">
                    <p>${this.escapeHtml(thought.content)}</p>
                </div>

                ${thought.summary ? `
                    <div class="thought-summary">
                        <strong>Summary:</strong> ${this.escapeHtml(thought.summary)}
                    </div>
                ` : ''}

                ${thought.insights && thought.insights.length > 0 ? `
                    <div class="thought-insights">
                        <strong>Insights:</strong>
                        <ul>
                            ${thought.insights.map(insight => `<li>${this.escapeHtml(insight)}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}

                ${thought.processing_progress ? `
                    <div class="thought-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${thought.processing_progress}%"></div>
                        </div>
                        <span class="progress-text">${thought.processing_progress}% complete</span>
                    </div>
                ` : ''}
            </div>
        `;
    }

    /**
     * Update thought count
     */
    updateCount(count) {
        if (this.countElement) {
            this.countElement.textContent = `${count} thought${count !== 1 ? 's' : ''}`;
        }
    }

    /**
     * Update specific thought in the list
     */
    updateThought(thoughtId, thought) {
        const card = this.container?.querySelector(`[data-thought-id="${thoughtId}"]`);
        if (card) {
            const newCard = this.renderThought(thought);
            card.outerHTML = newCard;
        }
    }

    /**
     * Add new thought to the top
     */
    prependThought(thought) {
        if (!this.container) return;
        
        // Remove empty state if exists
        const emptyState = this.container.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }

        const thoughtHtml = this.renderThought(thought);
        this.container.insertAdjacentHTML('afterbegin', thoughtHtml);
    }

    /**
     * Format status for display
     */
    formatStatus(status) {
        const statusMap = {
            'pending': 'Pending',
            'processing': 'Processing',
            'completed': 'Completed',
            'failed': 'Failed'
        };
        return statusMap[status] || status;
    }

    /**
     * Format priority for display
     */
    formatPriority(priority) {
        const priorityMap = {
            'critical': '🔴 Critical',
            'high': '🟠 High',
            'medium': '🟡 Medium',
            'low': '🟢 Low'
        };
        return priorityMap[priority] || priority;
    }

    /**
     * Format category for display
     */
    formatCategory(category) {
        const categoryMap = {
            'idea': '💡 Idea',
            'question': '❓ Question',
            'concern': '⚠️ Concern',
            'observation': '👁️ Observation',
            'reflection': '🤔 Reflection'
        };
        return categoryMap[category] || category;
    }

    /**
     * Format date for display
     */
    formatDate(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        
        return date.toLocaleDateString();
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
