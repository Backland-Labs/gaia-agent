# Gaia Troubleshooting and Common Gotchas

## Overview

This specification documents common issues, debugging approaches, and gotchas that developers encounter when deploying and integrating with Gaia AI agents. These are real-world problems not covered in standard documentation.

**Related Documentation:**
- [Troubleshooting](https://docs.gaianet.ai/getting-started/troubleshooting/) - Official troubleshooting guide
- [FAQs](https://docs.gaianet.ai/faqs) - Frequently asked questions
- [System Requirements](https://docs.gaianet.ai/getting-started/system-requirements/) - Prerequisites and compatibility

## Installation and Initialization Issues

### Download Failures
**Symptom**: Installation hangs or fails during model download
```bash
curl: (56) Recv failure: Connection was reset
Error downloading model files
```

**Causes and Solutions:**
- **Network Timeouts**: Large model files (1-10GB+) timeout on slow connections
  ```bash
  # Increase timeout and retry
  export GAIANET_DOWNLOAD_TIMEOUT=3600
  gaianet init --retry-count 5
  ```
- **Insufficient Disk Space**: Models require 2-3x their size during download
  ```bash
  # Check space before installation
  df -h $HOME/gaianet
  # Clean up partial downloads
  rm -rf $HOME/gaianet/tmp/*
  ```
- **Firewall/Proxy Issues**: Corporate networks may block model downloads
  ```bash
  # Configure proxy if needed
  export https_proxy=http://proxy.company.com:8080
  gaianet init
  ```

### Port Conflicts
**Symptom**: Service fails to start with "Address already in use"
```bash
Error: Failed to bind to port 8080: Address already in use
```

**Debugging Approach:**
```bash
# Check what's using the port
lsof -i :8080
netstat -tulpn | grep :8080

# Kill conflicting process or change ports
gaianet start --port 8081 --qdrant-port 9070
```

### Permission Issues
**Symptom**: Installation fails with permission errors
```bash
Permission denied: /Users/username/.gaianet/
```

**Solutions:**
```bash
# Fix ownership
sudo chown -R $USER:$USER $HOME/.gaianet/

# Alternative installation path
export GAIANET_HOME=/tmp/gaianet
curl -sSfL 'install_script_url' | bash
```

## Runtime and Performance Issues

### Memory Exhaustion
**Symptom**: Node crashes with OOM or becomes unresponsive
```bash
gaianet process killed (signal 9)
```

**Diagnostic Commands:**
```bash
# Monitor memory usage
ps aux | grep gaianet | awk '{print $4, $11}'
cat /proc/$(pgrep gaianet)/status | grep VmRSS

# Check swap usage
free -h
swapon --show
```

**Resolution Strategy:**
```json
{
  "chat_ctx_size": "8192",     // Reduce from 16384
  "chat_batch_size": "64",     // Reduce from 128
  "embedding_ctx_size": "4096" // Reduce from 8192
}
```

### API Timeout Issues
**Symptom**: Requests hang or timeout without response
```python
requests.exceptions.ReadTimeout: HTTPSConnectionPool(host='node.gaia.domains', port=443)
```

**Common Causes:**
1. **Cold Start Latency**: First request after idle period
   ```python
   # Implement retry with longer timeout for first request
   import time
   import requests
   
   def robust_request(url, data, max_retries=3):
       for attempt in range(max_retries):
           try:
               timeout = 60 if attempt == 0 else 30  # Longer timeout for first attempt
               response = requests.post(url, json=data, timeout=timeout)
               return response
           except requests.exceptions.ReadTimeout:
               if attempt == max_retries - 1:
                   raise
               time.sleep(2 ** attempt)  # Exponential backoff
   ```

2. **Context Window Overflow**: Request exceeds configured limits
   ```python
   def estimate_tokens(text):
       # Rough estimation: 1 token ≈ 4 characters
       return len(text) // 4
   
   def validate_context_size(messages, max_tokens=16384):
       total_tokens = sum(estimate_tokens(msg["content"]) for msg in messages)
       if total_tokens > max_tokens:
           raise ValueError(f"Context too large: {total_tokens} > {max_tokens}")
   ```

### Model Loading Failures
**Symptom**: Service starts but models are unavailable
```bash
curl localhost:8080/v1/models
# Returns empty models list or 404
```

**Debugging Steps:**
```bash
# Check model files exist
ls -la $HOME/.gaianet/models/

# Check configuration
cat $HOME/.gaianet/config.json | jq '.chat_model'

# Check logs for loading errors
gaianet logs | grep -i "model\|error\|fail"

# Verify model format compatibility
file $HOME/.gaianet/models/*.gguf
```

## API Integration Gotchas

### Authentication Edge Cases
**Gotcha**: API key validation appears inconsistent
```python
# Some endpoints work, others return 401 with same key
response = requests.get("https://node.gaia.domains/v1/models")  # Works without auth
response = requests.post("https://node.gaia.domains/v1/chat/completions", 
                        headers={"Authorization": "Bearer key"})  # Requires auth
```

**Solution Pattern:**
```python
def make_authenticated_request(endpoint, method="GET", **kwargs):
    """Consistent authentication for all endpoints"""
    headers = kwargs.get('headers', {})
    
    # Always include auth header, even for endpoints that might not need it
    if 'Authorization' not in headers:
        headers['Authorization'] = f"Bearer {api_key}"
    
    kwargs['headers'] = headers
    return requests.request(method, endpoint, **kwargs)
```

### Response Format Inconsistencies
**Gotcha**: Streaming responses differ from OpenAI format
```python
# Gaia streaming chunks may have different structure
for chunk in stream:
    # This might fail if chunk structure differs
    content = chunk.choices[0].delta.content
```

**Robust Handling:**
```python
def extract_stream_content(chunk):
    """Safely extract content from streaming response"""
    try:
        if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
            delta = chunk.choices[0].delta
            if hasattr(delta, 'content') and delta.content is not None:
                return delta.content
    except (AttributeError, IndexError, KeyError):
        pass
    return ""
```

### Model Name Mismatches
**Gotcha**: Model names in requests vs responses may differ
```python
# Request with "gpt-3.5-turbo", response shows "llama-2-7b"
response = client.chat.completions.create(
    model="gpt-3.5-turbo",  # Generic name
    messages=messages
)
print(response.model)  # May show actual model name: "llama-2-7b"
```

**Best Practice:**
```python
# Always check available models first
def get_available_models(base_url):
    response = requests.get(f"{base_url}/v1/models")
    return [model["id"] for model in response.json()["data"]]

# Use actual model names from the list
available_models = get_available_models(base_url)
model_to_use = available_models[0] if available_models else "default"
```

## Configuration and Deployment Gotchas

### Context Size vs Batch Size Trade-offs
**Gotcha**: High context size + high batch size = OOM
```json
{
  "chat_ctx_size": "32768",    // High context
  "chat_batch_size": "256"     // High batch - May cause OOM
}
```

**Memory Calculation:**
```python
def estimate_memory_usage(ctx_size, batch_size, model_size_gb):
    """Rough memory estimation for configuration validation"""
    # Base model memory
    base_memory = model_size_gb * 1024  # MB
    
    # Context memory (rough approximation)
    context_memory = (ctx_size * batch_size * 4) / (1024 * 1024)  # MB
    
    # Overhead
    overhead = base_memory * 0.3
    
    total_mb = base_memory + context_memory + overhead
    return total_mb / 1024  # GB
```

### Domain Configuration Pitfalls
**Gotcha**: Domain setup doesn't propagate immediately
```bash
gaianet start --domain my-agent
# Domain https://my-agent.gaia.domains may not be accessible immediately
```

**Robust Domain Check:**
```python
import time
import requests

def wait_for_domain_ready(domain, max_wait=300):
    """Wait for domain to become accessible"""
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"https://{domain}.gaia.domains/v1/models", timeout=10)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(10)
    
    return False
```

### Configuration File Persistence
**Gotcha**: Configuration changes may not persist across restarts
```bash
# Manual config changes might be overwritten
vim ~/.gaianet/config.json
gaianet restart  # Config might revert to defaults
```

**Persistent Configuration:**
```bash
# Use initialization with custom config
gaianet init --config /path/to/custom/config.json

# Or use environment variables
export GAIANET_CHAT_CTX_SIZE=8192
export GAIANET_BATCH_SIZE=64
gaianet start
```

## Debugging and Monitoring

### Log Analysis Patterns
```bash
# Common error patterns to grep for
gaianet logs | grep -E "(error|fail|timeout|oom|segfault)"

# Model loading issues
gaianet logs | grep -i "model" | grep -E "(fail|error|not found)"

# Memory issues
gaianet logs | grep -i "memory\|malloc\|alloc"

# Network issues
gaianet logs | grep -E "(connection|timeout|refused|reset)"
```

### Health Check Implementation
```python
def comprehensive_health_check(base_url, api_key):
    """Comprehensive health check for debugging"""
    checks = {}
    
    # Basic connectivity
    try:
        response = requests.get(f"{base_url}/v1/models", timeout=5)
        checks["connectivity"] = response.status_code == 200
    except:
        checks["connectivity"] = False
    
    # Authentication
    try:
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": "test", "messages": [{"role": "user", "content": "test"}]},
            timeout=10
        )
        checks["authentication"] = response.status_code != 401
    except:
        checks["authentication"] = False
    
    # Model availability
    try:
        response = requests.get(f"{base_url}/v1/models")
        models = response.json().get("data", [])
        checks["models_available"] = len(models) > 0
    except:
        checks["models_available"] = False
    
    # Performance test
    start_time = time.time()
    try:
        response = requests.get(f"{base_url}/v1/info", timeout=5)
        latency = time.time() - start_time
        checks["performance"] = latency < 2.0  # Under 2 seconds
    except:
        checks["performance"] = False
    
    return checks
```

### Performance Regression Detection
```python
def detect_performance_regression(metrics_history, window_size=50):
    """Detect if performance has degraded"""
    if len(metrics_history) < window_size * 2:
        return False
    
    recent_metrics = metrics_history[-window_size:]
    historical_metrics = metrics_history[-window_size*2:-window_size]
    
    recent_avg_latency = sum(m["latency"] for m in recent_metrics) / len(recent_metrics)
    historical_avg_latency = sum(m["latency"] for m in historical_metrics) / len(historical_metrics)
    
    # Alert if recent latency is 50% higher than historical
    return recent_avg_latency > historical_avg_latency * 1.5
```

## Recovery Procedures

### Complete Reset Procedure
```bash
# Stop all services
gaianet stop

# Backup configuration if needed
cp ~/.gaianet/config.json ~/.gaianet/config.json.backup

# Clean installation
rm -rf ~/.gaianet/
curl -sSfL 'install_script_url' | bash

# Restore configuration
cp ~/.gaianet/config.json.backup ~/.gaianet/config.json

# Reinitialize
gaianet init
gaianet start
```

### Partial Recovery Patterns
```bash
# Model corruption recovery
rm -rf ~/.gaianet/models/
gaianet init --download-models-only

# Configuration corruption recovery
gaianet init --reset-config

# Database corruption recovery
rm -rf ~/.gaianet/vector_db/
gaianet init --rebuild-index
```