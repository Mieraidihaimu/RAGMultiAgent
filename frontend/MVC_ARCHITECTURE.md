# Frontend MVC Architecture

This document describes the Model-View-Controller (MVC) architecture implemented in the frontend.

## Architecture Overview

The frontend has been refactored to follow the MVC pattern, separating concerns into three main layers:

### **Models** (Data Layer)
Handle data management and API interactions.

- **`ThoughtModel.js`**: Manages thought data, CRUD operations, filtering, and sorting
- **`GroupModel.js`**: Manages persona group data and API interactions

### **Views** (Presentation Layer)
Handle DOM manipulation and rendering.

- **`ThoughtView.js`**: Renders thought list, individual thought cards, and manages UI updates
- **`FormView.js`**: Manages form inputs, validation, and status messages
- **`FilterView.js`**: Handles filter UI elements and user selections

### **Controllers** (Business Logic Layer)
Orchestrate flow between Models and Views.

- **`ThoughtController.js`**: Main controller coordinating thought operations, form submissions, and filters
- **`StreamController.js`**: Manages Server-Sent Events (SSE) for real-time updates

### **Services** (Infrastructure Layer)
Provide shared utilities and infrastructure.

- **`ApiService.js`**: Centralized HTTP client for API communication
- **`auth-manager.js`**: Authentication and session management (existing)

### **Application Entry Point**
- **`app.js`**: Initializes the MVC architecture and bootstraps the application

## File Structure

```
frontend/
├── models/
│   ├── ThoughtModel.js       # Thought data and API operations
│   └── GroupModel.js          # Group data and API operations
├── views/
│   ├── ThoughtView.js         # Thought list rendering
│   ├── FormView.js            # Form input handling
│   └── FilterView.js          # Filter UI management
├── controllers/
│   ├── ThoughtController.js   # Main application controller
│   └── StreamController.js    # SSE connection management
├── services/
│   └── ApiService.js          # HTTP API client
├── app.js                     # Application initialization
├── auth-manager.js            # Authentication (existing)
├── index-mvc.html             # MVC-based page (new)
└── index.html                 # Original page (preserved)
```

## Key Benefits

### 1. **Separation of Concerns**
- Models handle data and business logic
- Views handle presentation and rendering
- Controllers orchestrate the flow

### 2. **Maintainability**
- Each component has a single responsibility
- Easy to locate and fix bugs
- Clear dependencies between layers

### 3. **Testability**
- Models can be tested independently
- Views can be tested with mock data
- Controllers can be tested with mock models/views

### 4. **Reusability**
- Models can be reused across different views
- Views can work with different data sources
- Services are shared across the application

### 5. **Scalability**
- Easy to add new features
- Clear patterns to follow
- Modular architecture supports growth

## Usage

### Loading the MVC Application

```html
<!-- Load in this order -->
<script src="auth-manager.js"></script>
<script src="services/ApiService.js"></script>
<script src="models/ThoughtModel.js"></script>
<script src="models/GroupModel.js"></script>
<script src="views/ThoughtView.js"></script>
<script src="views/FormView.js"></script>
<script src="views/FilterView.js"></script>
<script src="controllers/ThoughtController.js"></script>
<script src="controllers/StreamController.js"></script>
<script src="app.js"></script>
```

### Example: Adding a New Feature

To add a new feature (e.g., thought editing):

1. **Add Model Method** (`ThoughtModel.js`):
```javascript
async updateThought(thoughtId, updates) {
    return await this.api.put(`/thoughts/${thoughtId}`, updates);
}
```

2. **Add View Method** (`ThoughtView.js`):
```javascript
renderEditForm(thought) {
    // Return HTML for edit form
}
```

3. **Add Controller Method** (`ThoughtController.js`):
```javascript
async handleEdit(thoughtId) {
    const thought = this.thoughtModel.getById(thoughtId);
    this.thoughtView.renderEditForm(thought);
}
```

## Data Flow

### Creating a Thought
1. User submits form → `FormView` validates input
2. `ThoughtController` receives form data
3. `ThoughtController` calls `ThoughtModel.createThought()`
4. `ThoughtModel` calls `ApiService.post()`
5. On success, `ThoughtModel` updates local cache
6. `ThoughtController` tells `ThoughtView` to re-render
7. `StreamController` receives SSE updates for real-time status

### Filtering Thoughts
1. User changes filter → `FilterView` detects change
2. `ThoughtController` receives filter update
3. `ThoughtController` calls `ThoughtModel.setFilters()`
4. `ThoughtModel` returns filtered data
5. `ThoughtController` tells `ThoughtView` to render filtered list

## Migration Guide

To migrate existing pages to MVC:

1. **Extract API calls** → Move to Models
2. **Extract DOM manipulation** → Move to Views
3. **Extract event handlers** → Move to Controllers
4. **Use ApiService** → Replace raw fetch calls
5. **Initialize in app.js** → Bootstrap the application

## Best Practices

1. **Models** should not touch the DOM
2. **Views** should not make API calls
3. **Controllers** coordinate but delegate work
4. **Services** are stateless utilities
5. **Keep components loosely coupled**
6. **Use dependency injection** for testability

## Testing Strategy

- **Unit Tests**: Test each class independently
- **Integration Tests**: Test Model ↔ Controller ↔ View interactions
- **E2E Tests**: Test complete user workflows

## Future Enhancements

- Add state management library (e.g., Redux-like pattern)
- Implement router for multi-page navigation
- Add TypeScript for type safety
- Create component library for reusable UI elements
- Add automated testing suite
