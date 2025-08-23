# Gaia API Integration Patterns

## Overview

Gaia provides OpenAI-compatible APIs with unique characteristics that require specific integration patterns. This specification covers practical integration approaches, authentication patterns, and handling of Gaia-specific behaviors.

**Related Documentation:**
- [API Reference](https://docs.gaianet.ai/getting-started/api-reference) - Complete API endpoint documentation
- [Authentication](https://docs.gaianet.ai/getting-started/authentication/) - API key setup and management
- [Agent Integrations & Plugins](https://docs.gaianet.ai/agent-integrations) - Integration examples

## Authentication Patterns

### Bearer Token Authentication
```python
import openai

client = openai.OpenAI(
    base_url="https://your-node.gaia.domains",
    api_key="your-api-key"  # Used as Bearer token
)
```

### Direct HTTP Integration
```javascript
const headers = {
    'Authorization': 'Bearer YOUR_API_KEY_GOES_HERE',
    'Content-Type': 'application/json'
};

const response = await fetch('https://your-node.gaia.domains/v1/chat/completions', {
    method: 'POST',
    headers: headers,
    body: JSON.stringify(payload)
});
```

### Key Management Patterns
- **Environment Variables**: Store API keys in environment variables
- **Configuration Files**: Use secure configuration management
- **Rotation Strategy**: Plan for manual key rotation (no automatic rotation)

## Core API Endpoints

### Chat Completions
```python
# Standard chat completion
response = client.chat.completions.create(
    model="your-model",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the weather like?"}
    ],
    max_tokens=150,
    temperature=0.7
)
```

### Streaming Responses
```python
# Streaming for real-time responses
stream = client.chat.completions.create(
    model="your-model",
    messages=messages,
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="")
```

### Embeddings API
```python
# Generate embeddings for knowledge retrieval
response = client.embeddings.create(
    model="your-embedding-model",
    input="Text to embed"
)

embedding_vector = response.data[0].embedding
```

### Knowledge Retrieval
```python
# Gaia-specific retrieve endpoint
import requests

response = requests.post(
    "https://your-node.gaia.domains/v1/retrieve",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    json={"query": "search query", "limit": 5}
)

documents = response.json()
```

## Error Handling Patterns

### Standard Error Codes
```python
try:
    response = client.chat.completions.create(
        model="your-model",
        messages=messages
    )
except openai.BadRequestError as e:
    # Handle 400 errors - invalid request format
    print(f"Bad request: {e}")
except openai.NotFoundError as e:
    # Handle 404 errors - model or endpoint not found
    print(f"Not found: {e}")
except openai.InternalServerError as e:
    # Handle 500 errors - server issues
    print(f"Server error: {e}")
```

### Gaia-Specific Error Patterns
```python
def handle_gaia_errors(response):
    if response.status_code == 400:
        # Common causes: invalid model name, context too large
        error_data = response.json()
        if "context" in error_data.get("error", ""):
            # Reduce context size and retry
            pass
    elif response.status_code == 404:
        # Model not available or endpoint misconfigured
        # Check model list endpoint
        pass
    elif response.status_code == 500:
        # Server overload or model loading issues
        # Implement retry with exponential backoff
        pass
```

## Request Optimization Patterns

### Context Management
```python
def manage_context(messages, max_tokens=16384):
    """Manage conversation context to avoid token limits"""
    total_tokens = estimate_tokens(messages)
    
    if total_tokens > max_tokens:
        # Keep system message and recent conversation
        system_msgs = [msg for msg in messages if msg["role"] == "system"]
        recent_msgs = messages[-(max_tokens // 100):]  # Rough estimation
        return system_msgs + recent_msgs
    
    return messages
```

### Batch Processing Pattern
```python
async def process_batch(requests_list, batch_size=10):
    """Process multiple requests efficiently"""
    results = []
    
    for i in range(0, len(requests_list), batch_size):
        batch = requests_list[i:i + batch_size]
        batch_results = await asyncio.gather(*[
            process_single_request(req) for req in batch
        ])
        results.extend(batch_results)
    
    return results
```

## Knowledge Base Integration

### RAG Pattern Implementation
```python
class GaiaRAGClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def retrieve_context(self, query, limit=5):
        """Retrieve relevant documents from knowledge base"""
        response = requests.post(
            f"{self.base_url}/v1/retrieve",
            headers=self.headers,
            json={"query": query, "limit": limit}
        )
        return response.json()
    
    def chat_with_context(self, user_query, model):
        """Chat with automatic context retrieval"""
        # Retrieve relevant context
        context_docs = self.retrieve_context(user_query)
        
        # Build context-aware prompt
        context_text = "\n".join([doc["content"] for doc in context_docs])
        system_message = f"Use this context to answer: {context_text}"
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_query}
        ]
        
        # Make chat request
        return self.chat_completion(messages, model)
```

### Custom Embedding Workflow
```python
def build_custom_knowledge_base(documents, embedding_model):
    """Build custom knowledge base with embeddings"""
    embeddings = []
    
    for doc in documents:
        # Generate embedding
        response = client.embeddings.create(
            model=embedding_model,
            input=doc["content"]
        )
        
        embedding = {
            "id": doc["id"],
            "content": doc["content"],
            "vector": response.data[0].embedding,
            "metadata": doc.get("metadata", {})
        }
        embeddings.append(embedding)
    
    return embeddings
```

## Performance Optimization Patterns

### Connection Pooling
```python
import httpx

class OptimizedGaiaClient:
    def __init__(self, base_url, api_key):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
    
    async def chat_completion(self, messages, model):
        response = await self.client.post(
            "/v1/chat/completions",
            json={"model": model, "messages": messages}
        )
        return response.json()
```

### Caching Strategy
```python
import hashlib
import json
from functools import lru_cache

@lru_cache(maxsize=128)
def cached_embedding(text, model):
    """Cache embeddings for repeated queries"""
    response = client.embeddings.create(model=model, input=text)
    return response.data[0].embedding

def cache_key(messages, model, temperature):
    """Generate cache key for chat responses"""
    content = json.dumps({
        "messages": messages,
        "model": model,
        "temperature": temperature
    }, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()
```

## Integration Testing Patterns

### Health Check Implementation
```python
def health_check(base_url, api_key):
    """Verify Gaia node health"""
    tests = []
    
    # Test models endpoint
    try:
        response = requests.get(f"{base_url}/v1/models")
        tests.append(("models_endpoint", response.status_code == 200))
    except Exception as e:
        tests.append(("models_endpoint", False))
    
    # Test info endpoint
    try:
        response = requests.get(f"{base_url}/v1/info")
        tests.append(("info_endpoint", response.status_code == 200))
    except Exception as e:
        tests.append(("info_endpoint", False))
    
    # Test chat completion
    try:
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "default",
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 10
            }
        )
        tests.append(("chat_completion", response.status_code == 200))
    except Exception as e:
        tests.append(("chat_completion", False))
    
    return tests
```

### Load Testing Pattern
```python
import asyncio
import time

async def load_test(base_url, api_key, concurrent_requests=10, duration=60):
    """Load test Gaia node performance"""
    results = []
    start_time = time.time()
    
    async def single_request():
        start = time.time()
        # Make request
        response = await make_chat_request(base_url, api_key)
        end = time.time()
        return end - start, response.status_code
    
    while time.time() - start_time < duration:
        tasks = [single_request() for _ in range(concurrent_requests)]
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)
        
        # Small delay between batches
        await asyncio.sleep(1)
    
    return analyze_results(results)
```

## Common Integration Gotchas

### Model Name Handling
- Model names in responses may differ from request model names
- Always check available models via `/v1/models` endpoint
- Default model fallback behavior varies by deployment

### Response Format Differences
- Streaming response chunks may have different structure
- Error message formats not identical to OpenAI
- Usage statistics may be unavailable or approximate

### Rate Limiting
- No built-in rate limiting at API level
- Client-side rate limiting recommended
- Resource exhaustion manifests as 500 errors

### Context Window Management
- Hard context limits enforced at model level
- No graceful truncation - requests fail with 400 error
- Context size includes system messages and previous conversation