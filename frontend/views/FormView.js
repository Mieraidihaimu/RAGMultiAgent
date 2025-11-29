/**
 * Form View
 * Handles form rendering and input management
 */
class FormView {
    constructor() {
        this.form = null;
        this.textarea = null;
        this.submitBtn = null;
        this.charCount = null;
        this.statusMessage = null;
    }

    /**
     * Initialize form elements
     */
    init(formId = 'thoughtForm') {
        this.form = document.getElementById(formId);
        this.textarea = document.getElementById('thoughtText');
        this.submitBtn = document.getElementById('submitBtn');
        this.charCount = document.getElementById('charCount');
        this.statusMessage = document.getElementById('statusMessage');

        this.attachEventListeners();
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        if (this.textarea) {
            this.textarea.addEventListener('input', () => this.updateCharCount());
        }
    }

    /**
     * Update character count
     */
    updateCharCount() {
        if (!this.textarea || !this.charCount) return;
        const length = this.textarea.value.length;
        this.charCount.textContent = `${length} / 2000`;
        
        if (length > 2000) {
            this.charCount.style.color = '#ef4444';
        } else {
            this.charCount.style.color = '#6b7280';
        }
    }

    /**
     * Get form data
     */
    getFormData() {
        const formData = new FormData(this.form);
        return {
            content: formData.get('thoughtText'),
            processingMode: formData.get('processingMode'),
            selectedGroup: formData.get('selectedGroup')
        };
    }

    /**
     * Clear form
     */
    clearForm() {
        if (this.textarea) {
            this.textarea.value = '';
            this.updateCharCount();
        }
    }

    /**
     * Disable form
     */
    disable() {
        if (this.textarea) this.textarea.disabled = true;
        if (this.submitBtn) this.submitBtn.disabled = true;
    }

    /**
     * Enable form
     */
    enable() {
        if (this.textarea) this.textarea.disabled = false;
        if (this.submitBtn) this.submitBtn.disabled = false;
    }

    /**
     * Show status message
     */
    showStatus(message, type = 'info') {
        if (!this.statusMessage) return;

        this.statusMessage.textContent = message;
        this.statusMessage.className = `status-message ${type} show`;

        setTimeout(() => {
            this.statusMessage.classList.remove('show');
        }, 5000);
    }

    /**
     * Hide status message
     */
    hideStatus() {
        if (this.statusMessage) {
            this.statusMessage.classList.remove('show');
        }
    }

    /**
     * Validate form
     */
    validate() {
        const content = this.textarea?.value.trim();
        
        if (!content) {
            this.showStatus('Please enter your thought', 'error');
            return false;
        }

        if (content.length > 2000) {
            this.showStatus('Thought is too long (max 2000 characters)', 'error');
            return false;
        }

        return true;
    }
}
