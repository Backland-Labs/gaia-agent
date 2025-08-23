# Gaia Security and Privacy Considerations

## Overview

Deploying AI agents on Gaia introduces unique security and privacy challenges due to decentralized architecture, multiple network endpoints, and handling of potentially sensitive data. This specification provides comprehensive security guidance for production deployments.

**Related Documentation:**
- [Authentication](https://docs.gaianet.ai/getting-started/authentication/) - API key management and security
- [Domain Operator Guide](https://docs.gaianet.ai/domain-operator-guide) - Network security considerations
- [FAQs](https://docs.gaianet.ai/faqs) - Data privacy and compliance questions

## Network Security

### Port Exposure and Access Control
```bash
# Default exposed ports
8080   # API endpoint (public)
9068   # Metrics endpoint (should be internal)
9069   # Qdrant vector database (should be internal)
```

**Security Hardening:**
```bash
# Use firewall to restrict access
sudo ufw allow from 10.0.0.0/8 to any port 9068  # Metrics - internal only
sudo ufw allow from 10.0.0.0/8 to any port 9069  # Qdrant - internal only
sudo ufw allow 8080                                # API - public

# Alternative: bind to specific interfaces
gaianet start --api-bind 0.0.0.0:8080 --metrics-bind 127.0.0.1:9068 --qdrant-bind 127.0.0.1:9069
```

### TLS/SSL Configuration
```json
{
  "tls_config": {
    "enabled": true,
    "cert_path": "/etc/ssl/certs/gaia.crt",
    "key_path": "/etc/ssl/private/gaia.key",
    "min_version": "1.2",
    "cipher_suites": [
      "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
      "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256"
    ]
  }
}
```

### Reverse Proxy Security
```nginx
# Nginx security configuration
server {
    listen 443 ssl http2;
    server_name your-agent.gaia.domains;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    # Hide internal endpoints
    location /metrics {
        deny all;
        return 404;
    }
    
    location /qdrant {
        deny all;
        return 404;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## API Security

### Authentication and Authorization
```python
class SecureGaiaClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        
        # Security headers for all requests
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'User-Agent': 'SecureGaiaClient/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def make_request(self, endpoint, method='GET', **kwargs):
        """Secure request wrapper with validation"""
        # Validate endpoint
        if not endpoint.startswith('/v1/'):
            raise ValueError("Invalid endpoint format")
        
        # Construct full URL
        url = f"{self.base_url}{endpoint}"
        
        # Add timeout and retries
        kwargs.setdefault('timeout', 30)
        
        # Make request
        response = self.session.request(method, url, **kwargs)
        
        # Validate response
        if response.status_code == 401:
            raise AuthenticationError("Invalid API key")
        
        return response
```

### API Key Management
```python
import os
import secrets
import hashlib
from cryptography.fernet import Fernet

class APIKeyManager:
    def __init__(self, encryption_key=None):
        self.encryption_key = encryption_key or Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)
    
    def generate_api_key(self, length=32):
        """Generate cryptographically secure API key"""
        return secrets.token_urlsafe(length)
    
    def hash_api_key(self, api_key):
        """Hash API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def encrypt_api_key(self, api_key):
        """Encrypt API key for secure storage"""
        return self.cipher.encrypt(api_key.encode())
    
    def decrypt_api_key(self, encrypted_key):
        """Decrypt stored API key"""
        return self.cipher.decrypt(encrypted_key).decode()
    
    def rotate_api_key(self, old_key):
        """Generate new API key and invalidate old one"""
        new_key = self.generate_api_key()
        # Implementation depends on key storage mechanism
        return new_key

# Environment-based key management
def load_api_key():
    """Securely load API key from environment"""
    api_key = os.getenv('GAIA_API_KEY')
    if not api_key:
        raise ValueError("GAIA_API_KEY environment variable not set")
    
    # Validate key format
    if len(api_key) < 16:
        raise ValueError("API key too short")
    
    return api_key
```

### Request Validation and Sanitization
```python
import re
from typing import Dict, Any

class RequestValidator:
    def __init__(self):
        self.max_message_length = 10000
        self.max_messages = 100
        self.allowed_roles = {'user', 'assistant', 'system'}
        
    def validate_chat_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize chat completion request"""
        validated = {}
        
        # Validate model
        model = request_data.get('model', '')
        if not re.match(r'^[a-zA-Z0-9_-]+$', model):
            raise ValueError("Invalid model name format")
        validated['model'] = model
        
        # Validate messages
        messages = request_data.get('messages', [])
        if not isinstance(messages, list) or len(messages) > self.max_messages:
            raise ValueError(f"Invalid messages format or too many messages (max: {self.max_messages})")
        
        validated_messages = []
        for msg in messages:
            if not isinstance(msg, dict):
                raise ValueError("Message must be a dictionary")
            
            role = msg.get('role')
            if role not in self.allowed_roles:
                raise ValueError(f"Invalid role: {role}")
            
            content = msg.get('content', '')
            if len(content) > self.max_message_length:
                raise ValueError(f"Message too long (max: {self.max_message_length})")
            
            # Sanitize content
            sanitized_content = self.sanitize_content(content)
            
            validated_messages.append({
                'role': role,
                'content': sanitized_content
            })
        
        validated['messages'] = validated_messages
        
        # Validate optional parameters
        if 'max_tokens' in request_data:
            max_tokens = request_data['max_tokens']
            if not isinstance(max_tokens, int) or max_tokens < 1 or max_tokens > 4096:
                raise ValueError("Invalid max_tokens value")
            validated['max_tokens'] = max_tokens
        
        if 'temperature' in request_data:
            temp = request_data['temperature']
            if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
                raise ValueError("Invalid temperature value")
            validated['temperature'] = temp
        
        return validated
    
    def sanitize_content(self, content: str) -> str:
        """Sanitize message content"""
        # Remove potential injection attempts
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'javascript:', '', content, flags=re.IGNORECASE)
        
        # Limit special characters
        content = re.sub(r'[^\w\s\.\,\!\?\-\(\)\'\"]+', '', content)
        
        return content.strip()
```

## Data Privacy and Protection

### Sensitive Data Handling
```python
import re
from typing import List, Tuple

class DataPrivacyFilter:
    def __init__(self):
        self.patterns = {
            'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}-\d{3}-\d{4}\b',
            'api_key': r'[A-Za-z0-9]{32,}',
            'password': r'(?i)password[:\s=]+[^\s]+',
            'token': r'(?i)token[:\s=]+[^\s]+'
        }
    
    def detect_sensitive_data(self, text: str) -> List[Tuple[str, str]]:
        """Detect sensitive data patterns in text"""
        findings = []
        for data_type, pattern in self.patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                findings.append((data_type, match.group()))
        return findings
    
    def redact_sensitive_data(self, text: str) -> str:
        """Redact sensitive data from text"""
        redacted = text
        for data_type, pattern in self.patterns.items():
            redacted = re.sub(pattern, f'[REDACTED_{data_type.upper()}]', redacted)
        return redacted
    
    def validate_request_privacy(self, messages: List[Dict]) -> List[str]:
        """Validate request doesn't contain sensitive data"""
        violations = []
        for i, message in enumerate(messages):
            content = message.get('content', '')
            sensitive_data = self.detect_sensitive_data(content)
            if sensitive_data:
                violations.append(f"Message {i}: Found {[d[0] for d in sensitive_data]}")
        return violations

# Usage in request pipeline
def secure_chat_completion(client, messages, model):
    """Secure chat completion with privacy filtering"""
    privacy_filter = DataPrivacyFilter()
    
    # Check for sensitive data
    violations = privacy_filter.validate_request_privacy(messages)
    if violations:
        raise ValueError(f"Privacy violations detected: {violations}")
    
    # Proceed with request
    return client.chat.completions.create(model=model, messages=messages)
```

### Vector Database Security
```python
import qdrant_client
from qdrant_client.http import models

class SecureQdrantClient:
    def __init__(self, host, port, api_key=None):
        self.client = qdrant_client.QdrantClient(
            host=host,
            port=port,
            api_key=api_key,
            timeout=30
        )
    
    def create_secure_collection(self, collection_name: str, vector_size: int):
        """Create collection with security configurations"""
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE
            ),
            # Enable encryption at rest if available
            optimizers_config=models.OptimizersConfig(
                default_segment_number=2,
                max_segment_size=1000000,
                memmap_threshold=20000,
                indexing_threshold=20000,
                flush_interval_sec=5,
                max_optimization_threads=2
            )
        )
    
    def secure_search(self, collection_name: str, query_vector: List[float], 
                     user_id: str, limit: int = 5):
        """Search with user-based filtering"""
        return self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id",
                        match=models.MatchValue(value=user_id)
                    )
                ]
            ),
            limit=limit
        )
```

## Compliance and Auditing

### GDPR Compliance
```python
import json
import datetime
from typing import Dict, Any

class GDPRCompliance:
    def __init__(self, storage_backend):
        self.storage = storage_backend
    
    def log_data_processing(self, user_id: str, data_type: str, 
                           purpose: str, legal_basis: str):
        """Log data processing activities for GDPR compliance"""
        log_entry = {
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'user_id': user_id,
            'data_type': data_type,
            'purpose': purpose,
            'legal_basis': legal_basis,
            'retention_period': self.get_retention_period(data_type)
        }
        
        self.storage.store_audit_log('gdpr_processing', log_entry)
    
    def handle_data_subject_request(self, user_id: str, request_type: str):
        """Handle GDPR data subject requests"""
        if request_type == 'access':
            return self.export_user_data(user_id)
        elif request_type == 'deletion':
            return self.delete_user_data(user_id)
        elif request_type == 'rectification':
            return self.provide_rectification_form(user_id)
        elif request_type == 'portability':
            return self.export_portable_data(user_id)
    
    def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """Export all user data for GDPR access request"""
        user_data = {
            'conversations': self.storage.get_user_conversations(user_id),
            'embeddings': self.storage.get_user_embeddings(user_id),
            'metadata': self.storage.get_user_metadata(user_id),
            'processing_logs': self.storage.get_processing_logs(user_id)
        }
        
        # Redact any internal system data
        return self.redact_internal_data(user_data)
    
    def delete_user_data(self, user_id: str) -> bool:
        """Securely delete all user data"""
        try:
            # Delete from vector database
            self.storage.delete_user_vectors(user_id)
            
            # Delete conversation history
            self.storage.delete_user_conversations(user_id)
            
            # Delete metadata
            self.storage.delete_user_metadata(user_id)
            
            # Log deletion
            self.log_data_processing(
                user_id, 'all_data', 'deletion', 'data_subject_request'
            )
            
            return True
        except Exception as e:
            self.storage.store_audit_log('gdpr_deletion_error', {
                'user_id': user_id,
                'error': str(e),
                'timestamp': datetime.datetime.utcnow().isoformat()
            })
            return False
```

### Audit Logging
```python
import logging
import json
from datetime import datetime

class SecurityAuditLogger:
    def __init__(self, log_file='/var/log/gaia-security.log'):
        self.logger = logging.getLogger('gaia_security')
        self.logger.setLevel(logging.INFO)
        
        # File handler with rotation
        handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=100*1024*1024, backupCount=5
        )
        
        # JSON formatter for structured logging
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_api_access(self, user_id: str, endpoint: str, method: str, 
                      status_code: int, ip_address: str):
        """Log API access for security monitoring"""
        log_data = {
            'event_type': 'api_access',
            'user_id': user_id,
            'endpoint': endpoint,
            'method': method,
            'status_code': status_code,
            'ip_address': ip_address,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.logger.info(json.dumps(log_data))
    
    def log_authentication_event(self, user_id: str, event_type: str, 
                                success: bool, ip_address: str):
        """Log authentication events"""
        log_data = {
            'event_type': 'authentication',
            'user_id': user_id,
            'auth_event': event_type,
            'success': success,
            'ip_address': ip_address,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        level = logging.INFO if success else logging.WARNING
        self.logger.log(level, json.dumps(log_data))
    
    def log_security_violation(self, user_id: str, violation_type: str, 
                             details: Dict[str, Any]):
        """Log security violations"""
        log_data = {
            'event_type': 'security_violation',
            'user_id': user_id,
            'violation_type': violation_type,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.logger.error(json.dumps(log_data))
```

## Security Monitoring and Alerting

### Intrusion Detection
```python
import collections
import time
from typing import Dict, List

class SecurityMonitor:
    def __init__(self):
        self.rate_limits = collections.defaultdict(list)
        self.failed_attempts = collections.defaultdict(int)
        self.blocked_ips = set()
        
    def check_rate_limit(self, ip_address: str, limit: int = 100, 
                        window: int = 3600) -> bool:
        """Check if IP is within rate limits"""
        now = time.time()
        
        # Clean old requests
        self.rate_limits[ip_address] = [
            req_time for req_time in self.rate_limits[ip_address]
            if now - req_time < window
        ]
        
        # Check current rate
        if len(self.rate_limits[ip_address]) >= limit:
            self.block_ip(ip_address, f"Rate limit exceeded: {limit}/{window}s")
            return False
        
        # Record this request
        self.rate_limits[ip_address].append(now)
        return True
    
    def detect_attack_patterns(self, requests: List[Dict]) -> List[str]:
        """Detect common attack patterns"""
        alerts = []
        
        # SQL injection attempts
        sql_patterns = ['union select', 'drop table', "'; --", 'exec(']
        for req in requests:
            content = req.get('content', '').lower()
            for pattern in sql_patterns:
                if pattern in content:
                    alerts.append(f"SQL injection attempt from {req['ip']}")
        
        # Excessive failed authentications
        failed_auth_counts = collections.Counter(
            req['ip'] for req in requests 
            if req.get('status_code') == 401
        )
        for ip, count in failed_auth_counts.items():
            if count > 10:
                alerts.append(f"Brute force attempt from {ip}: {count} failed auths")
        
        # Unusual payload sizes
        large_requests = [
            req for req in requests 
            if req.get('content_length', 0) > 1000000  # 1MB
        ]
        if large_requests:
            alerts.append(f"Large payload attack: {len(large_requests)} requests")
        
        return alerts
    
    def block_ip(self, ip_address: str, reason: str):
        """Block suspicious IP address"""
        self.blocked_ips.add(ip_address)
        
        # Log the blocking
        audit_logger.log_security_violation(
            user_id='system',
            violation_type='ip_blocked',
            details={'ip': ip_address, 'reason': reason}
        )
        
        # Could integrate with firewall here
        # subprocess.run(['iptables', '-A', 'INPUT', '-s', ip_address, '-j', 'DROP'])
```

### Security Configuration Checklist
```python
def security_configuration_audit(config_path: str) -> List[str]:
    """Audit Gaia configuration for security issues"""
    issues = []
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Check for weak configurations
    if config.get('debug_mode', False):
        issues.append("Debug mode enabled in production")
    
    if not config.get('tls_enabled', False):
        issues.append("TLS not enabled")
    
    if config.get('allow_origin') == '*':
        issues.append("CORS configured to allow all origins")
    
    # Check for exposed internal endpoints
    bind_addresses = [
        config.get('metrics_bind', ''),
        config.get('qdrant_bind', '')
    ]
    for addr in bind_addresses:
        if addr.startswith('0.0.0.0:'):
            issues.append(f"Internal endpoint exposed on all interfaces: {addr}")
    
    # Check for default credentials
    if config.get('api_key') in ['default', 'test', 'changeme']:
        issues.append("Default or weak API key detected")
    
    # Check log level
    if config.get('log_level', '').lower() == 'debug':
        issues.append("Debug logging enabled (may expose sensitive data)")
    
    return issues
```

## Incident Response

### Security Incident Response Plan
```python
class IncidentResponse:
    def __init__(self, notification_service):
        self.notifications = notification_service
        self.response_procedures = {
            'data_breach': self.handle_data_breach,
            'unauthorized_access': self.handle_unauthorized_access,
            'dos_attack': self.handle_dos_attack,
            'malware_detection': self.handle_malware_detection
        }
    
    def handle_security_incident(self, incident_type: str, details: Dict):
        """Handle security incident according to response plan"""
        timestamp = datetime.utcnow().isoformat()
        
        # Log incident
        audit_logger.log_security_violation(
            user_id='system',
            violation_type=incident_type,
            details=details
        )
        
        # Execute response procedure
        if incident_type in self.response_procedures:
            self.response_procedures[incident_type](details)
        
        # Notify security team
        self.notifications.send_alert(
            f"Security Incident: {incident_type}",
            f"Incident detected at {timestamp}: {details}"
        )
    
    def handle_data_breach(self, details: Dict):
        """Handle potential data breach"""
        # Immediate containment
        affected_users = details.get('affected_users', [])
        
        # Block suspicious activity
        if 'source_ip' in details:
            security_monitor.block_ip(details['source_ip'], 'Data breach incident')
        
        # Preserve evidence
        self.preserve_logs(details.get('timeframe'))
        
        # Initiate breach notification process
        self.initiate_breach_notification(affected_users)
    
    def preserve_logs(self, timeframe: Dict):
        """Preserve logs for forensic analysis"""
        # Copy relevant logs to secure storage
        # Implementation depends on log storage system
        pass
```

This comprehensive security specification covers the critical security considerations that developers often overlook when deploying AI agents on Gaia infrastructure.