#!/usr/bin/env python3
"""
Critical path tests for GaiaNet chatbot backend.
Tests only the core business logic that could fail in non-obvious ways.
"""

import pytest
import json
import os
import sys
from unittest.mock import Mock, patch
import importlib

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

def test_request_validator_prevents_xss():
    """Test that RequestValidator sanitizes XSS attempts."""
    from app import RequestValidator
    
    validator = RequestValidator()
    
    # Test XSS attempt in message content
    malicious_request = {
        'model': 'test-model',
        'messages': [
            {
                'role': 'user',
                'content': 'Hello <script>alert("xss")</script>world'
            }
        ]
    }
    
    validated = validator.validate_chat_request(malicious_request)
    
    # Should remove script tags
    assert '<script>' not in validated['messages'][0]['content']
    assert 'alert' not in validated['messages'][0]['content']
    assert 'Hello' in validated['messages'][0]['content']
    assert 'world' in validated['messages'][0]['content']


def test_data_privacy_filter_redacts_sensitive_data():
    """Test that DataPrivacyFilter detects and redacts PII."""
    from app import DataPrivacyFilter
    
    privacy_filter = DataPrivacyFilter()
    
    # Test credit card redaction
    text_with_cc = "My credit card is 4532-1234-5678-9012 please help"
    redacted = privacy_filter.redact_sensitive_data(text_with_cc)
    
    assert '4532-1234-5678-9012' not in redacted
    assert '[REDACTED_CREDIT_CARD]' in redacted
    assert 'please help' in redacted


def test_rate_limiter_blocks_excessive_requests():
    """Test that rate limiting blocks abuse attempts."""
    from app import SecurityMonitor
    
    monitor = SecurityMonitor()
    
    # Should allow initial requests
    assert monitor.check_rate_limit('192.168.1.1', limit=5, window=60) == True
    assert monitor.check_rate_limit('192.168.1.1', limit=5, window=60) == True
    
    # Fill up to limit
    for _ in range(3):
        monitor.check_rate_limit('192.168.1.1', limit=5, window=60)
    
    # Should block after exceeding limit
    assert monitor.check_rate_limit('192.168.1.1', limit=5, window=60) == False


def test_chat_completion_basic_flow():
    """Test basic chat completion flow works end-to-end."""
    # Test without GaiaNet configured - should return proper error
    from app import app
    
    with app.test_client() as client:
        response = client.post('/api/chat',
            json={
                'message': 'Hello, how are you?',
                'model': 'test-model'
            },
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['error'] == 'GaiaNet not configured'


def test_health_check_endpoint():
    """Test health check returns proper status."""
    from app import app
    
    with app.test_client() as client:
        response = client.get('/api/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'status' in data
        assert data['status'] == 'healthy'
        assert 'timestamp' in data