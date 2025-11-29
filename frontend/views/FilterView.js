/**
 * Filter View
 * Handles filter UI and interactions
 */
class FilterView {
    constructor() {
        this.filterElements = {};
    }

    /**
     * Initialize filter elements
     */
    init() {
        this.filterElements = {
            status: document.getElementById('filterStatus'),
            priority: document.getElementById('filterPriority'),
            category: document.getElementById('filterCategory'),
            sortBy: document.getElementById('sortBy')
        };
    }

    /**
     * Get current filter values
     */
    getFilters() {
        return {
            status: this.filterElements.status?.value || 'all',
            priority: this.filterElements.priority?.value || 'all',
            category: this.filterElements.category?.value || 'all',
            sortBy: this.filterElements.sortBy?.value || 'created_desc'
        };
    }

    /**
     * Reset all filters
     */
    reset() {
        Object.values(this.filterElements).forEach(element => {
            if (element) element.value = element.querySelector('option')?.value || 'all';
        });
    }

    /**
     * Set filter change callback
     */
    onFilterChange(callback) {
        Object.values(this.filterElements).forEach(element => {
            if (element) {
                element.addEventListener('change', callback);
            }
        });
    }
}
