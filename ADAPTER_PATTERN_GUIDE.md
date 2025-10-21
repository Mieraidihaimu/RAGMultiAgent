# Adapter Pattern Architecture Guide

## Overview

The AI Thought Processor now uses the **Adapter Pattern** to support multiple AI providers and databases. This makes the system flexible, maintainable, and easy to extend.

## Why Adapter Pattern?

### Problems Solved

1. **Tight Coupling**: Previously tightly coupled to Supabase and Anthropic
2. **Vendor Lock-in**: Difficult to switch providers
3. **Testing**: Hard to mock dependencies
4. **Flexibility**: Limited ability to choose providers based on cost/features

### Benefits

- ✅ **Provider Independence**: Switch between providers easily
- ✅ **Cost Optimization**: Choose cheapest provider for each task
- ✅ **Feature Selection**: Use best features from each provider
- ✅ **Testing**: Easy to mock adapters for unit tests
- ✅ **Future-Proof**: Add new providers without changing core code

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Application Layer                  │
│           (API, Batch Processor, etc.)              │
└────────────────────┬────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌────────────────┐      ┌────────────────┐
│   AI Provider  │      │    Database    │
│    Adapter     │      │    Adapter     │
└────────┬───────┘      └────────┬───────┘
         │                       │
    ┌────┴────┐            ┌─────┴─────┐
    │         │            │           │
    ▼         ▼            ▼           ▼
┌────────┐ ┌────────┐  ┌──────────┐ ┌──────────┐
│Anthropic│ │OpenAI  │  │PostgreSQL│ │Supabase  │
│(Claude) │ │(GPT)   │  │(Local)   │ │(Cloud)   │
└─────────┘ └────────┘  └──────────┘ └──────────┘
              │
              ▼
          ┌────────┐
          │Google  │
          │(Gemini)│
          └────────┘
```

---

## AI Provider Adapters

### Supported Providers

| Provider | Models | Caching | Context | Cost |
|----------|--------|---------|---------|------|
| **Anthropic** | Claude Sonnet, Opus, Haiku | Native (90% savings) | 200K tokens | $$$ |
| **OpenAI** | GPT-4, GPT-4 Turbo, GPT-3.5 | No | 128K tokens | $$ |
| **Google** | Gemini 1.5 Pro/Flash | Context caching | 2M tokens | $ |

### Usage

```python
from batch_processor.ai_providers import AIProviderFactory, AIMessage

# Create provider
provider = AIProviderFactory.create(
    provider_type="anthropic",  # or "openai" or "google"
    api_key="sk-ant-...",
    model="claude-sonnet-4-20250514"
)

# Generate response
messages = [AIMessage(role="user", content="Hello, AI!")]
response = await provider.generate(messages=messages)

print(response.content)
print(f"Cost: ${provider.estimate_cost(**response.usage):.4f}")
```

### Switching Providers

**Environment Variable:**
```bash
# In .env file
AI_PROVIDER=anthropic  # or openai or google
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

**Programmatic:**
```python
# Anthropic
provider = AIProviderFactory.create("anthropic", api_key="...")

# OpenAI
provider = AIProviderFactory.create("openai", api_key="...")

# Google
provider = AIProviderFactory.create("google", api_key="...")
```

### Provider Comparison

#### Anthropic (Claude)

**Pros:**
- Best reasoning and analysis quality
- Native prompt caching (90% cost savings)
- Long context (200K tokens)

**Cons:**
- Higher cost without caching
- Requires Anthropic account

**Best For:**
- Complex thought analysis
- Value assessment
- Context-heavy tasks

#### OpenAI (GPT)

**Pros:**
- Fast and reliable
- Wide ecosystem support
- Good general performance

**Cons:**
- No native prompt caching
- Higher cost for large contexts
- Shorter context window

**Best For:**
- Quick classifications
- Simple extractions
- Cost-sensitive workloads

#### Google (Gemini)

**Pros:**
- Lowest cost
- Longest context (2M tokens with 1.5)
- Multimodal capabilities
- Context caching in 1.5 models

**Cons:**
- Newer, less proven
- API may have more changes

**Best For:**
- Very long contexts
- Cost optimization
- Multimodal future features

---

## Database Adapters

### Supported Databases

| Database | Type | Use Case | Complexity |
|----------|------|----------|------------|
| **PostgreSQL** | Self-hosted | Local dev, full control | Medium |
| **Supabase** | Managed | Production, quick setup | Low |

### Usage

```python
from common.database import DatabaseFactory

# PostgreSQL (local Docker)
db = await DatabaseFactory.create(
    db_type="postgresql",
    host="localhost",
    port=5432,
    database="thoughtprocessor",
    user="thoughtprocessor",
    password="your-password"
)

# Supabase (cloud)
db = await DatabaseFactory.create(
    db_type="supabase",
    url="https://xxx.supabase.co",
    key="eyJxxx..."
)

# Auto-detect from environment
db = await DatabaseFactory.create_from_env(
    use_supabase=bool(os.getenv("SUPABASE_URL"))
)
```

### Switching Databases

**Using Local PostgreSQL (Docker):**
```bash
# In .env file
# Comment out or remove SUPABASE_URL
#SUPABASE_URL=
#SUPABASE_KEY=

# Set PostgreSQL connection
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=thoughtprocessor
POSTGRES_USER=thoughtprocessor
POSTGRES_PASSWORD=your-password
DATABASE_URL=postgresql://thoughtprocessor:your-password@db:5432/thoughtprocessor
```

**Using Supabase:**
```bash
# In .env file
# Set Supabase credentials (auto-detected)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
```

### Database Comparison

#### PostgreSQL (Local)

**Pros:**
- Full control
- No external dependencies
- Better for development
- No cost

**Cons:**
- Requires setup and maintenance
- Need to manage backups
- No built-in auth

**Best For:**
- Local development
- Self-hosted deployments
- Full data control

#### Supabase

**Pros:**
- Managed service
- Built-in auth and realtime
- Auto backups
- Quick setup

**Cons:**
- External dependency
- Costs after free tier
- Less control

**Best For:**
- Production deployments
- Quick prototyping
- Cloud-native apps

---

## Configuration

### Environment Variables

```bash
# ===================================
# Database Selection
# ===================================
# If SUPABASE_URL is set, Supabase is used
# Otherwise, PostgreSQL is used

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-key

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=thoughtprocessor
POSTGRES_USER=thoughtprocessor
POSTGRES_PASSWORD=password
DATABASE_URL=postgresql://user:pass@host:port/db

# ===================================
# AI Provider Selection
# ===================================
AI_PROVIDER=anthropic  # anthropic | openai | google

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview

# Google
GOOGLE_API_KEY=...
GOOGLE_MODEL=gemini-2.5-flash-lite
```

---

## Implementation Details

### AI Provider Interface

```python
class AIProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: List[AIMessage],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        **kwargs
    ) -> AIResponse:
        """Generate AI response"""
        pass

    @abstractmethod
    async def generate_with_cache(
        self,
        messages: List[AIMessage],
        cacheable_context: Optional[str] = None,
        **kwargs
    ) -> AIResponse:
        """Generate with prompt caching"""
        pass

    @abstractmethod
    def supports_caching(self) -> bool:
        """Check if provider supports caching"""
        pass

    @abstractmethod
    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Estimate cost"""
        pass
```

### Database Interface

```python
class DatabaseAdapter(ABC):
    # Thought operations
    @abstractmethod
    async def create_thought(self, user_id, text) -> Dict: pass

    @abstractmethod
    async def get_thoughts(self, user_id, status=None) -> List: pass

    @abstractmethod
    async def update_thought(self, thought_id, **fields) -> Dict: pass

    # User operations
    @abstractmethod
    async def get_user(self, user_id) -> Dict: pass

    @abstractmethod
    async def update_user_context(self, user_id, context) -> Dict: pass

    # Cache operations
    @abstractmethod
    async def find_similar_cached_thought(
        self,
        embedding,
        user_id,
        threshold
    ) -> Optional[Dict]: pass

    @abstractmethod
    async def save_to_cache(
        self,
        user_id,
        thought_text,
        embedding,
        response
    ) -> Dict: pass
```

---

## Cost Optimization Strategies

### Strategy 1: Mix Providers by Task

```python
# Use cheap provider for classification
classifier = AIProviderFactory.create("google", ...)
classification = await classifier.generate(...)

# Use powerful provider for analysis
analyzer = AIProviderFactory.create("anthropic", ...)
analysis = await analyzer.generate_with_cache(...)
```

### Strategy 2: Use Caching Strategically

```python
# Anthropic: Best caching (90% savings)
if provider.supports_caching():
    response = await provider.generate_with_cache(
        messages=messages,
        cacheable_context=user_context  # Cached!
    )
```

### Strategy 3: Tiered Processing

```python
# Simple tasks: Gemini Flash (cheap est)
# Medium tasks: GPT-3.5 Turbo
# Complex tasks: Claude Sonnet with caching
```

---

## Migration Guide

### From Old to New Architecture

**Before (Tightly Coupled):**
```python
from supabase import create_client
from anthropic import Anthropic

# Hardcoded providers
supabase = create_client(url, key)
claude = Anthropic(api_key=key)
```

**After (Adapter Pattern):**
```python
from common.database import DatabaseFactory
from batch_processor.ai_providers import AIProviderFactory

# Flexible providers
db = await DatabaseFactory.create_from_env()
ai = AIProviderFactory.create(
    provider_type=os.getenv("AI_PROVIDER"),
    api_key=os.getenv("ANTHROPIC_API_KEY")
)
```

### Testing with Adapters

**Mock Adapter:**
```python
class MockAIProvider(AIProvider):
    async def generate(self, messages, **kwargs):
        return AIResponse(
            content="Mock response",
            usage={"input_tokens": 10, "output_tokens": 20}
        )

# Use in tests
provider = MockAIProvider(api_key="test")
```

---

## File Structure

```
RAGMultiAgent/
├── common/
│   └── database/                 # Database adapters
│       ├── __init__.py
│       ├── base.py              # Abstract interface
│       ├── postgres_adapter.py  # PostgreSQL implementation
│       ├── supabase_adapter.py  # Supabase implementation
│       └── factory.py           # Factory pattern
│
├── batch_processor/
│   └── ai_providers/            # AI provider adapters
│       ├── __init__.py
│       ├── base.py              # Abstract interface
│       ├── anthropic_provider.py # Claude implementation
│       ├── openai_provider.py    # GPT implementation
│       ├── google_provider.py    # Gemini implementation
│       └── factory.py            # Factory pattern
│
├── api/
│   └── database.py              # Uses database adapter
│
└── batch_processor/
    ├── config.py                # Multi-provider config
    └── processor.py             # Uses both adapters
```

---

## Best Practices

### 1. Use Factory Pattern

```python
# ✅ Good: Use factory
provider = AIProviderFactory.create("anthropic", ...)

# ❌ Bad: Direct instantiation
provider = AnthropicProvider(...)
```

### 2. Check Provider Capabilities

```python
if provider.supports_caching():
    response = await provider.generate_with_cache(...)
else:
    response = await provider.generate(...)
```

### 3. Handle Provider-Specific Errors

```python
try:
    response = await provider.generate(...)
except Exception as e:
    logger.error(f"Provider {provider.get_model_name()} failed: {e}")
    # Fallback to different provider
```

### 4. Monitor Costs

```python
response = await provider.generate(...)
cost = provider.estimate_cost(**response.usage)
logger.info(f"Request cost: ${cost:.4f}")
```

---

## Future Extensions

### Adding New AI Provider

1. Create `new_provider.py` in `batch_processor/ai_providers/`
2. Implement `AIProvider` interface
3. Add to factory in `factory.py`
4. Update `.env.example` with new provider config

### Adding New Database

1. Create `new_db_adapter.py` in `common/database/`
2. Implement `DatabaseAdapter` interface
3. Add to factory in `factory.py`
4. Update connection logic

---

## Troubleshooting

### Provider Not Found

**Error:** `Unsupported provider type: xyz`

**Solution:** Check `AI_PROVIDER` in `.env` matches supported providers

### Database Connection Failed

**Error:** `Failed to connect to database`

**Solution:**
1. Check if `SUPABASE_URL` is set for Supabase
2. Check PostgreSQL connection params if using local DB
3. Verify credentials are correct

### API Key Missing

**Error:** `ANTHROPIC_API_KEY must be set`

**Solution:** Set the appropriate API key for your selected provider

---

## Summary

The Adapter Pattern provides:

- **Flexibility**: Easy provider switching
- **Maintainability**: Clean separation of concerns
- **Testability**: Easy to mock dependencies
- **Scalability**: Add new providers without core changes
- **Cost Optimization**: Mix providers for best value

**Quick Start:**
```bash
# Set your preferences in .env
AI_PROVIDER=anthropic
SUPABASE_URL=  # Leave empty for local PostgreSQL

# System automatically uses right adapters
docker-compose up -d
```

---

**Need Help?**
- See full examples in `batch_processor/processor.py`
- Check interface definitions in `base.py` files
- Review factory implementations for usage patterns

**Version:** 2.0.0 (Adapter Pattern)
