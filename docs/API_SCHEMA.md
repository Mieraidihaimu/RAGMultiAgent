# API Schema Documentation

## Overview
- **Base URL**: `http://localhost:8000`
- **Version**: 1.0.0
- **Authentication**: Bearer Token (JWT)

## HTTP Endpoints

### Thoughts
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| `POST` | `/thoughts` | Create a new thought (Single or Group mode) | Yes |
| `GET` | `/thoughts/{user_id}` | Get all thoughts for a user | Yes |
| `GET` | `/thoughts/{user_id}/{thought_id}` | Get a specific thought | Yes |
| `DELETE` | `/thoughts/{user_id}/{thought_id}` | Delete a thought | Yes |
| `POST` | `/anonymous/thoughts` | Create an anonymous thought | No |
| `GET` | `/anonymous/thoughts/{session_token}` | Get anonymous thoughts | No |
| `GET` | `/anonymous/session/{session_token}` | Get anonymous session info | No |

### Users
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| `GET` | `/users/{user_id}` | Get user profile | Yes |
| `PUT` | `/users/{user_id}/context` | Update user context/preferences | Yes |

### Authentication (`/api/auth`)
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| `POST` | `/signup` | Create new account | No |
| `POST` | `/login` | Login and get JWT | No |
| `GET` | `/me` | Get current user info | Yes |
| `POST` | `/refresh` | Refresh access token | Yes |
| `POST` | `/logout` | Logout user | Yes |
| `POST` | `/convert-anonymous` | Convert anonymous session to user | Yes |
| `GET` | `/consent/status` | Get GDPR consent status | Yes |
| `PUT` | `/consent/update` | Update consent preferences | Yes |
| `GET` | `/consent/history` | Get consent audit trail | Yes |
| `DELETE` | `/consent/withdraw-all` | Withdraw all consents (delete account) | Yes |

### Persona Groups
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| `POST` | `/groups` | Create a persona group | Yes |
| `GET` | `/groups` | List persona groups | Yes |
| `GET` | `/groups/{group_id}` | Get group details | Yes |
| `PUT` | `/groups/{group_id}` | Update group details | Yes |
| `DELETE` | `/groups/{group_id}` | Delete group | Yes |
| `POST` | `/groups/{group_id}/personas` | Add persona to group | Yes |
| `GET` | `/personas/{persona_id}` | Get persona details | Yes |
| `PUT` | `/personas/{persona_id}` | Update persona | Yes |
| `DELETE` | `/personas/{persona_id}` | Remove persona | Yes |

### Synthesis
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| `GET` | `/synthesis/{user_id}/latest` | Get latest weekly synthesis | Yes |
| `GET` | `/synthesis/{user_id}` | Get all weekly syntheses | Yes |

### Payments (`/api`)
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| `GET` | `/stripe-config` | Get Stripe publishable key | No |
| `POST` | `/create-subscription` | Create paid subscription | Yes |
| `POST` | `/create-free-account` | Create free account | No |
| `POST` | `/cancel-subscription` | Cancel subscription | Yes |
| `GET` | `/subscription/{user_id}` | Get subscription details | Yes |

### System
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| `GET` | `/health` | System health check | No |
| `POST` | `/process/trigger` | Trigger manual batch processing | No |

## Server-Sent Events (SSE)

**Endpoint**: `GET /events/{user_id}?token={jwt_token}`

### Events

#### `connected`
Sent immediately upon successful connection.
```json
{
  "message": "SSE connection established",
  "user_id": "uuid",
  "timestamp": "ISO8601"
}
```

#### `thought_created`
Sent when a thought is successfully submitted and queued.
```json
{
  "thought_id": "uuid",
  "status": "pending"
}
```

#### `thought_processing`
Sent when analysis begins.
```json
{
  "thought_id": "uuid",
  "status": "processing",
  "mode": "single|group",
  "message": "Starting AI analysis..."
}
```

#### `thought_agent_completed`
Sent when a specific agent in the pipeline finishes (Single Mode).
```json
{
  "thought_id": "uuid",
  "agent": "Classifier|Analyzer|Value Assessor|Action Planner|Prioritizer",
  "progress": "1/5",
  "agent_number": 1,
  "total_agents": 5
}
```

#### `group_processing_started`
Sent when group analysis begins (Group Mode).
```json
{
  "thought_id": "uuid",
  "group_name": "Board of Advisors",
  "persona_count": 3
}
```

#### `persona_completed`
Sent when a specific persona finishes analysis (Group Mode).
```json
{
  "thought_id": "uuid",
  "persona_id": "uuid",
  "persona_name": "Steve Jobs",
  "progress": "1/3",
  "has_error": false
}
```

#### `consolidation_started`
Sent when all personas are done and synthesis begins (Group Mode).
```json
{
  "thought_id": "uuid",
  "message": "Synthesizing perspectives..."
}
```

#### `thought_completed`
Sent when the entire process is finished.
```json
{
  "thought_id": "uuid",
  "status": "completed",
  "mode": "single|group",
  "message": "Analysis complete!",
  "processing_time_seconds": 15.5
}
```

#### `thought_failed`
Sent if an error occurs during processing.
```json
{
  "thought_id": "uuid",
  "status": "failed",
  "error": "Error message description"
}
```
