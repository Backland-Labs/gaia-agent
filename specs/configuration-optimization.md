# Gaia Configuration and Performance Optimization

## Overview

Gaia nodes require careful configuration tuning to achieve optimal performance for specific use cases. This specification provides actionable guidance for configuration optimization, performance tuning, and resource management.

## Core Configuration Parameters

### Context Window Configuration
```json
{
  "chat_ctx_size": "16384",      // Balance capability vs memory usage
  "embedding_ctx_size": "8192"   // Optimize for retrieval performance
}
```

**Optimization Guidelines:**
- **Memory-Constrained Systems**: Reduce to 8192/4096
- **High-Capability Requirements**: Increase to 32768/16384
- **Balanced Production**: Keep default 16384/8192

**Memory Impact Calculation:**
```
Estimated Memory = (chat_ctx_size × model_size_factor) + overhead
```

### Batch Processing Configuration
```json
{
  "chat_batch_size": "128",        // Higher = better throughput
  "embedding_batch_size": "64"     // Optimize for concurrent embeddings
}
```

**Tuning Strategy:**
- **Single-User Systems**: 32/16 for lower latency
- **Multi-User Production**: 256/128 for higher throughput
- **Memory-Limited**: 64/32 to prevent OOM conditions

### Vector Database Optimization
```json
{
  "qdrant_limit": "1",              // Number of vector results
  "qdrant_score_threshold": "0.5"   // Relevance filtering
}
```

**Performance Tuning:**
- **High Precision**: Increase threshold to 0.7-0.8
- **High Recall**: Decrease threshold to 0.3-0.4
- **Balanced Retrieval**: Default 0.5 threshold
- **Multiple Results**: Increase limit to 3-5 for complex queries

## Model Selection Optimization

### Chat Model Performance Matrix
| Model Size | Memory Usage | Latency | Quality | Use Case |
|------------|-------------|---------|---------|----------|
| 7B         | 8-12GB      | Fast    | Good    | Real-time chat |
| 13B        | 16-24GB     | Medium  | Better  | Production assistant |
| 30B+       | 32GB+       | Slow    | Best    | Complex reasoning |

### Embedding Model Selection
```json
{
  "embedding_model": {
    "small": "sentence-transformers/all-MiniLM-L6-v2",    // 384 dimensions
    "medium": "sentence-transformers/all-mpnet-base-v2",  // 768 dimensions  
    "large": "text-embedding-ada-002"                     // 1536 dimensions
  }
}
```

**Selection Criteria:**
- **Speed Priority**: Use smaller embedding models
- **Accuracy Priority**: Use larger, domain-specific models
- **Storage Constraints**: Consider dimension count impact

## Performance Optimization Strategies

### Startup Time Optimization
```json
{
  "preload_models": true,
  "cache_embeddings": true,
  "warm_start": {
    "enabled": true,
    "dummy_requests": 3
  }
}
```

**Implementation Pattern:**
```bash
# Pre-download models
gaianet init --preload

# Warm start sequence
gaianet start --warm-start
curl -X POST localhost:8080/v1/chat/completions -d '{"model":"default","messages":[{"role":"user","content":"warmup"}]}'
```

### Memory Management
```json
{
  "memory_optimization": {
    "garbage_collection": "aggressive",
    "model_offloading": true,
    "swap_threshold": 0.8
  }
}
```

### Network Optimization
```json
{
  "network_config": {
    "max_connections": 100,
    "connection_timeout": 30,
    "keep_alive": true,
    "compression": "gzip"
  }
}
```

## Environment-Specific Configurations

### Development Environment
```json
{
  "chat_ctx_size": "8192",
  "chat_batch_size": "32",
  "embedding_ctx_size": "4096",
  "embedding_batch_size": "16",
  "qdrant_limit": "3",
  "qdrant_score_threshold": "0.4",
  "debug_mode": true,
  "verbose_logging": true
}
```

### Production Environment
```json
{
  "chat_ctx_size": "16384",
  "chat_batch_size": "128",
  "embedding_ctx_size": "8192", 
  "embedding_batch_size": "64",
  "qdrant_limit": "1",
  "qdrant_score_threshold": "0.6",
  "debug_mode": false,
  "monitoring_enabled": true,
  "health_check_interval": 30
}
```

### High-Traffic Environment
```json
{
  "chat_ctx_size": "12288",
  "chat_batch_size": "256",
  "embedding_ctx_size": "6144",
  "embedding_batch_size": "128", 
  "qdrant_limit": "1",
  "qdrant_score_threshold": "0.7",
  "connection_pooling": true,
  "load_balancing": "round_robin"
}
```

## Resource Monitoring and Scaling

### Resource Usage Monitoring
```bash
# Monitor memory usage
ps aux | grep gaianet
htop -p $(pgrep gaianet)

# Monitor disk usage
du -sh ~/.gaianet/
df -h

# Monitor network connections
netstat -an | grep :8080
ss -tulpn | grep gaianet
```

### Performance Metrics Collection
```python
import psutil
import requests
import time

def monitor_gaia_performance(base_url, duration=300):
    """Monitor Gaia node performance metrics"""
    metrics = []
    start_time = time.time()
    
    while time.time() - start_time < duration:
        # System metrics
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        # API response time
        start = time.time()
        try:
            response = requests.get(f"{base_url}/v1/models", timeout=5)
            api_latency = time.time() - start
            api_success = response.status_code == 200
        except:
            api_latency = None
            api_success = False
        
        metrics.append({
            "timestamp": time.time(),
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available": memory.available,
            "api_latency": api_latency,
            "api_success": api_success
        })
        
        time.sleep(10)
    
    return metrics
```

### Scaling Decision Matrix
| Metric | Threshold | Action |
|--------|-----------|--------|
| Memory Usage | >85% | Reduce batch sizes or context windows |
| CPU Usage | >90% | Scale horizontally or upgrade hardware |
| API Latency | >2s | Optimize model size or increase resources |
| Error Rate | >5% | Check configuration and resource limits |

## Hardware Optimization

### CPU Optimization
```json
{
  "cpu_config": {
    "threads": "auto",          // Use all available cores
    "affinity": "numa_local",   // NUMA-aware scheduling
    "governor": "performance"   // CPU frequency scaling
  }
}
```

### GPU Acceleration
```json
{
  "gpu_config": {
    "enabled": true,
    "device": "cuda:0",
    "memory_fraction": 0.8,     // Reserve GPU memory
    "mixed_precision": true     // FP16 for better performance
  }
}
```

**GPU Memory Estimation:**
```
GPU Memory = Model Size × 1.2 + Batch Size × Context Length × Hidden Size × 4 bytes
```

### Storage Optimization
```json
{
  "storage_config": {
    "model_cache": "/fast/ssd/path",
    "vector_db": "/fast/ssd/path", 
    "logs": "/standard/hdd/path",
    "compression": "lz4"
  }
}
```

## Configuration Validation

### Pre-Deployment Validation
```python
def validate_configuration(config):
    """Validate Gaia configuration before deployment"""
    issues = []
    
    # Memory validation
    chat_memory = int(config.get("chat_ctx_size", 16384)) * 4  # Rough bytes estimate
    if chat_memory > get_available_memory() * 0.7:
        issues.append("chat_ctx_size may exceed available memory")
    
    # Batch size validation
    batch_size = int(config.get("chat_batch_size", 128))
    if batch_size > 512:
        issues.append("chat_batch_size very high, may cause OOM")
    
    # Port availability
    ports = [8080, 9068, 9069]
    for port in ports:
        if not is_port_available(port):
            issues.append(f"Port {port} is not available")
    
    # Disk space validation
    required_space = estimate_model_size(config.get("chat_model"))
    if get_free_space() < required_space * 1.5:
        issues.append("Insufficient disk space for model storage")
    
    return issues
```

### Runtime Configuration Tuning
```python
def dynamic_optimization(metrics_history):
    """Dynamically adjust configuration based on performance"""
    avg_latency = sum(m["api_latency"] for m in metrics_history) / len(metrics_history)
    avg_memory = sum(m["memory_percent"] for m in metrics_history) / len(metrics_history)
    
    recommendations = []
    
    if avg_latency > 1.0:  # > 1 second average
        recommendations.append("Reduce batch_size for lower latency")
        recommendations.append("Consider smaller model for faster inference")
    
    if avg_memory > 80:
        recommendations.append("Reduce ctx_size to lower memory usage")
        recommendations.append("Enable model offloading")
    
    if avg_latency < 0.2 and avg_memory < 50:
        recommendations.append("Increase batch_size for better throughput")
        recommendations.append("Consider larger model for better quality")
    
    return recommendations
```

## Configuration Templates

### Minimal Resource Template
```json
{
  "chat_ctx_size": "4096",
  "chat_batch_size": "16", 
  "embedding_ctx_size": "2048",
  "embedding_batch_size": "8",
  "qdrant_limit": "1",
  "qdrant_score_threshold": "0.5",
  "model_size": "7B"
}
```

### Balanced Production Template
```json
{
  "chat_ctx_size": "16384",
  "chat_batch_size": "128",
  "embedding_ctx_size": "8192",
  "embedding_batch_size": "64", 
  "qdrant_limit": "3",
  "qdrant_score_threshold": "0.6",
  "model_size": "13B",
  "monitoring": true,
  "health_checks": true
}
```

### High-Performance Template
```json
{
  "chat_ctx_size": "32768",
  "chat_batch_size": "256",
  "embedding_ctx_size": "16384",
  "embedding_batch_size": "128",
  "qdrant_limit": "5", 
  "qdrant_score_threshold": "0.7",
  "model_size": "30B",
  "gpu_acceleration": true,
  "connection_pooling": true
}
```