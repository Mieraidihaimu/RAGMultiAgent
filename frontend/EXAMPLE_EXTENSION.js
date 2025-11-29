/**
 * Example: Adding Search Functionality to MVC Architecture
 * This demonstrates how to extend the MVC pattern with a new feature
 */

// ============================================================================
// 1. MODEL: SearchModel.js
// ============================================================================

class SearchModel {
    constructor(apiService) {
        this.api = apiService;
        this.searchResults = [];
        this.searchQuery = '';
    }

    /**
     * Search thoughts by query
     */
    async search(query, filters = {}) {
        try {
            this.searchQuery = query;
            const params = new URLSearchParams({
                q: query,
                ...filters
            });

            const data = await this.api.get(`/search/thoughts?${params}`);
            this.searchResults = data.results || [];
            
            return { success: true, results: this.searchResults };
        } catch (error) {
            console.error('Search error:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Get current search results
     */
    getResults() {
        return this.searchResults;
    }

    /**
     * Clear search results
     */
    clear() {
        this.searchResults = [];
        this.searchQuery = '';
    }
}

// ============================================================================
// 2. VIEW: SearchView.js
// ============================================================================

class SearchView {
    constructor() {
        this.searchInput = null;
        this.searchButton = null;
        this.resultsContainer = null;
    }

    /**
     * Initialize search view
     */
    init(inputId = 'searchInput', buttonId = 'searchButton', resultsId = 'searchResults') {
        this.searchInput = document.getElementById(inputId);
        this.searchButton = document.getElementById(buttonId);
        this.resultsContainer = document.getElementById(resultsId);
    }

    /**
     * Get search query
     */
    getQuery() {
        return this.searchInput?.value.trim() || '';
    }

    /**
     * Clear search input
     */
    clearInput() {
        if (this.searchInput) {
            this.searchInput.value = '';
        }
    }

    /**
     * Render search results
     */
    renderResults(results, query) {
        if (!this.resultsContainer) return;

        if (results.length === 0) {
            this.renderEmpty(query);
            return;
        }

        const html = `
            <div class="search-header">
                <h3>Found ${results.length} result${results.length !== 1 ? 's' : ''} for "${query}"</h3>
            </div>
            <div class="search-results-list">
                ${results.map(result => this.renderResult(result)).join('')}
            </div>
        `;

        this.resultsContainer.innerHTML = html;
    }

    /**
     * Render single result
     */
    renderResult(result) {
        return `
            <div class="search-result-card" data-result-id="${result.id}">
                <div class="result-content">${this.escapeHtml(result.content)}</div>
                <div class="result-meta">
                    <span class="result-score">Match: ${(result.score * 100).toFixed(0)}%</span>
                    <span class="result-date">${this.formatDate(result.created_at)}</span>
                </div>
            </div>
        `;
    }

    /**
     * Render empty state
     */
    renderEmpty(query) {
        this.resultsContainer.innerHTML = `
            <div class="search-empty">
                <div class="empty-icon">🔍</div>
                <p>No results found for "${query}"</p>
            </div>
        `;
    }

    /**
     * Render loading state
     */
    renderLoading() {
        if (!this.resultsContainer) return;
        this.resultsContainer.innerHTML = `
            <div class="search-loading">
                <div class="spinner"></div>
                <p>Searching...</p>
            </div>
        `;
    }

    /**
     * Format date
     */
    formatDate(dateString) {
        return new Date(dateString).toLocaleDateString();
    }

    /**
     * Escape HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// ============================================================================
// 3. CONTROLLER: SearchController.js
// ============================================================================

class SearchController {
    constructor(searchModel, searchView) {
        this.searchModel = searchModel;
        this.searchView = searchView;
    }

    /**
     * Initialize search controller
     */
    init() {
        this.searchView.init();
        this.attachEventListeners();
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        const searchButton = document.getElementById('searchButton');
        const searchInput = document.getElementById('searchInput');

        if (searchButton) {
            searchButton.addEventListener('click', () => this.handleSearch());
        }

        if (searchInput) {
            // Search on Enter key
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.handleSearch();
                }
            });
        }
    }

    /**
     * Handle search action
     */
    async handleSearch() {
        const query = this.searchView.getQuery();

        if (!query) {
            alert('Please enter a search query');
            return;
        }

        // Show loading state
        this.searchView.renderLoading();

        // Perform search
        const result = await this.searchModel.search(query);

        if (result.success) {
            this.searchView.renderResults(result.results, query);
        } else {
            alert('Search failed: ' + result.error);
        }
    }

    /**
     * Clear search
     */
    clearSearch() {
        this.searchModel.clear();
        this.searchView.clearInput();
        this.searchView.renderResults([], '');
    }
}

// ============================================================================
// 4. INTEGRATION: Add to app.js
// ============================================================================

/**
 * In app.js, initialize the search feature:
 */

class App {
    constructor() {
        this.thoughtController = null;
        this.streamController = null;
        this.searchController = null; // Add this
    }

    async init() {
        // ... existing initialization ...

        // Initialize search feature
        const searchModel = new SearchModel(apiService);
        const searchView = new SearchView();
        this.searchController = new SearchController(searchModel, searchView);
        this.searchController.init();

        // ... rest of initialization ...
    }
}

// ============================================================================
// 5. HTML: Add to index-mvc.html
// ============================================================================

/**
 * Add this HTML to your page:
 * 
 * <div class="search-section">
 *     <div class="search-box">
 *         <input 
 *             type="text" 
 *             id="searchInput" 
 *             placeholder="Search thoughts..."
 *             class="search-input"
 *         />
 *         <button id="searchButton" class="search-btn">Search</button>
 *     </div>
 *     <div id="searchResults" class="search-results"></div>
 * </div>
 */

// ============================================================================
// 6. CSS: Add styles
// ============================================================================

/**
 * Add these styles:
 * 
 * .search-section {
 *     margin: 30px 0;
 *     padding: 20px;
 *     background: white;
 *     border-radius: 12px;
 * }
 * 
 * .search-box {
 *     display: flex;
 *     gap: 10px;
 * }
 * 
 * .search-input {
 *     flex: 1;
 *     padding: 12px;
 *     border: 2px solid #e5e7eb;
 *     border-radius: 8px;
 * }
 * 
 * .search-btn {
 *     padding: 12px 24px;
 *     background: #6366f1;
 *     color: white;
 *     border: none;
 *     border-radius: 8px;
 *     cursor: pointer;
 * }
 * 
 * .search-result-card {
 *     padding: 16px;
 *     margin: 10px 0;
 *     background: #f9fafb;
 *     border-radius: 8px;
 * }
 */

// ============================================================================
// SUMMARY
// ============================================================================

/**
 * This example demonstrates:
 * 
 * 1. Creating a new Model for data operations (SearchModel)
 * 2. Creating a new View for rendering (SearchView)
 * 3. Creating a Controller to coordinate them (SearchController)
 * 4. Integrating with the main App
 * 5. Adding necessary HTML and CSS
 * 
 * The same pattern can be applied to add:
 * - Analytics dashboard
 * - User settings
 * - Export functionality
 * - Any other feature
 * 
 * Key principles:
 * - Models handle data and API calls
 * - Views handle rendering and DOM manipulation
 * - Controllers handle user interactions and coordinate Model ↔ View
 * - Keep components loosely coupled and testable
 */
