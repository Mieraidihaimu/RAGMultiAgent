/**
 * Thought Controller
 * Orchestrates thought operations between models and views
 */
class ThoughtController {
    constructor(thoughtModel, groupModel, thoughtView, formView, filterView) {
        this.thoughtModel = thoughtModel;
        this.groupModel = groupModel;
        this.thoughtView = thoughtView;
        this.formView = formView;
        this.filterView = filterView;
        this.isAnonymous = false;
        this.userId = null;
    }

    /**
     * Initialize controller
     */
    async init() {
        // Check authentication
        this.checkAuth();

        // Initialize views
        this.thoughtView.init();
        this.formView.init();
        this.filterView.init();

        // Attach event listeners
        this.attachEventListeners();

        // Load initial data
        await this.loadThoughts();
        
        if (!this.isAnonymous) {
            await this.loadGroups();
        }
    }

    /**
     * Check authentication status
     */
    checkAuth() {
        if (authManager.isAuthenticated()) {
            this.isAnonymous = false;
            this.userId = authManager.getUserId();
        } else {
            this.isAnonymous = true;
            this.setupAnonymousMode();
        }
    }

    /**
     * Setup anonymous mode
     */
    setupAnonymousMode() {
        const userEmailElement = document.getElementById('userEmail');
        if (userEmailElement) {
            userEmailElement.textContent = 'Anonymous (3 free)';
            userEmailElement.style.color = '#f59e0b';
        }
        this.showAnonymousBanner();
    }

    /**
     * Show anonymous banner
     */
    showAnonymousBanner() {
        const banner = document.getElementById('anonymousBanner');
        if (banner) {
            banner.style.display = 'flex';
            banner.innerHTML = `
                <span class="banner-text">💭 Try 3 thoughts free! No signup required.</span>
                <button class="btn-signup" onclick="window.location.href='login.html?signup=true'">Sign Up for More</button>
            `;
        }
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        // Form submission
        const form = document.getElementById('thoughtForm');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleSubmit();
            });
        }

        // Filter changes
        this.filterView.onFilterChange(() => this.applyFilters());

        // Reset filters
        const resetBtn = document.getElementById('resetFilters');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetFilters());
        }
    }

    /**
     * Load thoughts
     */
    async loadThoughts() {
        this.thoughtView.renderLoading();

        const result = await this.thoughtModel.fetchThoughts(this.userId, this.isAnonymous);
        
        if (result.success) {
            this.thoughtView.render(this.thoughtModel.getFilteredThoughts());
        } else {
            this.formView.showStatus('Failed to load thoughts: ' + result.error, 'error');
        }
    }

    /**
     * Load persona groups
     */
    async loadGroups() {
        const result = await this.groupModel.fetchGroups(this.userId, true);
        
        if (result.success) {
            this.updateGroupSelector(result.groups);
        }
    }

    /**
     * Update group selector dropdown
     */
    updateGroupSelector(groups) {
        const select = document.getElementById('selectedGroup');
        if (!select) return;

        select.innerHTML = '<option value="">Select a persona group...</option>';
        
        groups.forEach(group => {
            const option = document.createElement('option');
            option.value = group.id;
            const personaCount = group.personas?.length || 0;
            option.textContent = `${group.name} (${personaCount} persona${personaCount !== 1 ? 's' : ''})`;
            select.appendChild(option);
        });
    }

    /**
     * Handle form submission
     */
    async handleSubmit() {
        if (!this.formView.validate()) {
            return;
        }

        const formData = this.formView.getFormData();
        
        this.formView.disable();
        this.formView.showStatus('Creating thought...', 'info');

        // Create thought data
        const thoughtData = {
            content: formData.content,
            user_id: this.userId
        };

        // Create thought
        const result = await this.thoughtModel.createThought(thoughtData, this.isAnonymous);

        if (result.success) {
            this.formView.clearForm();
            this.formView.showStatus('Thought created!', 'success');

            // Update anonymous session info if present
            if (result.data.session_info) {
                authManager.updateAnonymousInfo(result.data.session_info);
                this.updateAnonymousBanner(result.data.session_info);
            }

            // Trigger processing if needed
            if (result.data.thought) {
                await this.processThought(
                    result.data.thought.id,
                    formData.processingMode,
                    formData.selectedGroup
                );
            }

            // Refresh thought list
            this.thoughtView.render(this.thoughtModel.getFilteredThoughts());
        } else {
            this.formView.showStatus('Failed to create thought: ' + result.error, 'error');
        }

        this.formView.enable();
    }

    /**
     * Process thought
     */
    async processThought(thoughtId, processingMode, groupId) {
        const result = await this.thoughtModel.processThought(thoughtId, processingMode, groupId);
        
        if (!result.success) {
            console.error('Failed to process thought:', result.error);
        }
    }

    /**
     * Apply filters
     */
    applyFilters() {
        const filters = this.filterView.getFilters();
        this.thoughtModel.setFilters(filters);
        this.thoughtView.render(this.thoughtModel.getFilteredThoughts());
    }

    /**
     * Reset filters
     */
    resetFilters() {
        this.filterView.reset();
        this.thoughtModel.resetFilters();
        this.thoughtView.render(this.thoughtModel.getFilteredThoughts());
    }

    /**
     * Update anonymous banner
     */
    updateAnonymousBanner(sessionInfo) {
        const bannerText = document.querySelector('.banner-text');
        if (bannerText && sessionInfo) {
            const remaining = sessionInfo.thoughts_remaining;
            if (remaining === 0) {
                bannerText.textContent = '🎉 You\'ve used all 3 free thoughts! Sign up to continue.';
            } else {
                bannerText.textContent = `💭 ${remaining} free thought${remaining !== 1 ? 's' : ''} remaining.`;
            }
        }
    }

    /**
     * Handle real-time thought update
     */
    handleThoughtUpdate(thoughtId, updates) {
        this.thoughtModel.updateThought(thoughtId, updates);
        
        // Re-render if the thought passes current filters
        const filteredThoughts = this.thoughtModel.getFilteredThoughts();
        const thought = filteredThoughts.find(t => t.id === thoughtId);
        
        if (thought) {
            this.thoughtView.updateThought(thoughtId, thought);
        }
    }
}
