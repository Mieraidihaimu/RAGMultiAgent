/**
 * Stream Controller
 * Handles Server-Sent Events (SSE) for real-time updates
 */
class StreamController {
    constructor(thoughtController) {
        this.thoughtController = thoughtController;
        this.eventSource = null;
        this.reconnectTimeout = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.baseUrl = 'http://localhost:8000';
    }

    /**
     * Initialize SSE connection
     */
    connect(userId, isAnonymous = false) {
        // Close existing connection
        this.disconnect();

        let streamUrl;
        if (isAnonymous) {
            const sessionToken = authManager.getAnonymousSession();
            if (!sessionToken) return;
            streamUrl = `${this.baseUrl}/stream/${sessionToken}`;
        } else {
            streamUrl = `${this.baseUrl}/stream/${userId}`;
        }

        try {
            this.eventSource = new EventSource(streamUrl);
            this.attachEventListeners();
            console.log('SSE connection established');
        } catch (error) {
            console.error('Failed to establish SSE connection:', error);
            this.scheduleReconnect(userId, isAnonymous);
        }
    }

    /**
     * Attach SSE event listeners
     */
    attachEventListeners() {
        if (!this.eventSource) return;

        // Connection opened
        this.eventSource.onopen = () => {
            console.log('SSE connection opened');
            this.reconnectAttempts = 0;
        };

        // Connection error
        this.eventSource.onerror = (error) => {
            console.error('SSE connection error:', error);
            this.eventSource.close();
            
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                const userId = this.thoughtController.userId;
                const isAnonymous = this.thoughtController.isAnonymous;
                this.scheduleReconnect(userId, isAnonymous);
            }
        };

        // Thought created
        this.eventSource.addEventListener('thought_created', (e) => {
            const data = JSON.parse(e.data);
            console.log('Thought created:', data);
        });

        // Thought processing
        this.eventSource.addEventListener('thought_processing', (e) => {
            const data = JSON.parse(e.data);
            console.log('Thought processing:', data);
            this.thoughtController.handleThoughtUpdate(data.thought_id, {
                status: 'processing'
            });
        });

        // Group processing started
        this.eventSource.addEventListener('group_processing_started', (e) => {
            const data = JSON.parse(e.data);
            console.log('Group processing started:', data);
        });

        // Persona completed
        this.eventSource.addEventListener('persona_completed', (e) => {
            const data = JSON.parse(e.data);
            console.log('Persona completed:', data);
            
            // Update processing progress
            if (data.progress) {
                this.thoughtController.handleThoughtUpdate(data.thought_id, {
                    processing_progress: data.progress
                });
            }
        });

        // Consolidation started
        this.eventSource.addEventListener('consolidation_started', (e) => {
            const data = JSON.parse(e.data);
            console.log('Consolidation started:', data);
        });

        // Thought completed
        this.eventSource.addEventListener('thought_completed', (e) => {
            const data = JSON.parse(e.data);
            console.log('Thought completed:', data);
            this.thoughtController.handleThoughtUpdate(data.thought_id, {
                status: 'completed',
                summary: data.summary,
                insights: data.insights,
                processing_progress: 100
            });
        });

        // Thought failed
        this.eventSource.addEventListener('thought_failed', (e) => {
            const data = JSON.parse(e.data);
            console.error('Thought failed:', data);
            this.thoughtController.handleThoughtUpdate(data.thought_id, {
                status: 'failed',
                error: data.error
            });
        });
    }

    /**
     * Schedule reconnection
     */
    scheduleReconnect(userId, isAnonymous) {
        this.reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
        
        console.log(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
        
        this.reconnectTimeout = setTimeout(() => {
            console.log('Attempting to reconnect...');
            this.connect(userId, isAnonymous);
        }, delay);
    }

    /**
     * Disconnect SSE
     */
    disconnect() {
        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
            this.reconnectTimeout = null;
        }

        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
            console.log('SSE connection closed');
        }
    }

    /**
     * Check if connected
     */
    isConnected() {
        return this.eventSource && this.eventSource.readyState === EventSource.OPEN;
    }
}
