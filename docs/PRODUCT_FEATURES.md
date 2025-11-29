# Bare Product Features (MVP)

This document establishes the core "bare product features" for the AI Thought Processor. These features are currently implemented and verified in the codebase.

## 1. Core Functionality

### 1.1 Thought Submission
- **Description**: Users can submit text-based thoughts for analysis.
- **Modes**:
    - **Personal Feedback**: Single-agent pipeline analysis.
    - **Group Perspectives**: Multi-persona analysis (requires authenticated user).
- **Implementation**: `POST /thoughts` (Authenticated), `POST /anonymous/thoughts` (Anonymous).
- **Frontend**: Textarea input with character count and mode selector.

### 1.2 AI Analysis Pipeline
- **Description**: A 5-stage AI pipeline processes each thought.
- **Stages**:
    1. **Classification**: Determines type (idea, problem, etc.), urgency, and emotional tone.
    2. **Analysis**: Contextual analysis based on user profile.
    3. **Value Assessment**: Scores impact on economic, relational, health, etc. dimensions.
    4. **Action Planning**: Generates concrete steps and timing.
    5. **Prioritizer**: Assigns priority level and strategic fit.
- **Implementation**: `batch_processor/processor.py` (ThoughtProcessor class).

### 1.3 Real-Time Updates
- **Description**: Users receive live updates on the processing status.
- **Mechanism**: Server-Sent Events (SSE).
- **Events**: `thought_processing`, `thought_agent_completed`, `thought_completed`, `thought_failed`.
- **Implementation**: `api/sse.py`, `frontend/index.html` (EventSource).

### 1.4 Semantic Caching
- **Description**: Prevents reprocessing of similar thoughts to save costs and time.
- **Mechanism**: Vector embeddings (OpenAI) + Cosine similarity search (pgvector).
- **Threshold**: > 0.92 similarity triggers a cache hit.
- **Implementation**: `batch_processor/semantic_cache.py`.

## 2. User Management

### 2.1 Anonymous Access
- **Description**: Unauthenticated users can try the product with limits.
- **Limits**: Max 3 thoughts per session.
- **Implementation**: `api/anonymous_utils.py`, `frontend/auth-manager.js`.

### 2.2 Authenticated Access
- **Description**: Full access for registered users.
- **Features**: Unlimited thoughts, history retention, group mode.
- **Implementation**: `api/auth_routes.py`.

## 3. User Interface

### 3.1 Dashboard
- **Description**: Main view for submitting and viewing thoughts.
- **Features**:
    - "Summer Theme" design (Perplexity-inspired).
    - Real-time status indicators.
    - Filtering by status, priority, and category.
    - Sorting by date, priority, or value.
- **Implementation**: `frontend/index.html`.

### 3.2 Detail View
- **Description**: In-depth view of a specific thought's analysis.
- **Implementation**: `frontend/detail.html`.

## 4. Infrastructure

- **Database**: PostgreSQL with `pgvector` extension.
- **Message Queue**: Apache Kafka (optional, falls back to batch mode).
- **Cache**: Redis (for SSE pub/sub).
- **Containerization**: Docker Compose for all services.
