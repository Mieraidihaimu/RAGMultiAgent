/**
 * Application Entry Point
 * Initializes the MVC architecture and starts the application
 */
class App {
    constructor() {
        this.thoughtController = null;
        this.streamController = null;
    }

    /**
     * Initialize application
     */
    async init() {
        console.log('Initializing application...');

        // Initialize models
        const thoughtModel = new ThoughtModel(apiService);
        const groupModel = new GroupModel(apiService);

        // Initialize views
        const thoughtView = new ThoughtView();
        const formView = new FormView();
        const filterView = new FilterView();

        // Initialize controllers
        this.thoughtController = new ThoughtController(
            thoughtModel,
            groupModel,
            thoughtView,
            formView,
            filterView
        );

        this.streamController = new StreamController(this.thoughtController);

        // Initialize controllers
        await this.thoughtController.init();

        // Connect to SSE stream
        this.connectStream();

        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });

        console.log('Application initialized');
    }

    /**
     * Connect to event stream
     */
    connectStream() {
        const userId = this.thoughtController.userId;
        const isAnonymous = this.thoughtController.isAnonymous;
        
        if (userId || isAnonymous) {
            this.streamController.connect(userId, isAnonymous);
        }
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        if (this.streamController) {
            this.streamController.disconnect();
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const app = new App();
    app.init().catch(error => {
        console.error('Failed to initialize application:', error);
    });
});
