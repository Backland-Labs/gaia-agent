#!/usr/bin/env python3
"""
Critical security tests for GaiaNet Chatbot Backend
Tests core security features: XSS prevention, sensitive data redaction, rate limiting
"""

import pytest
import json
from unittest.mock import Mock, patch
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Mock environment variables to prevent GaiaNet client initialization
with patch.dict(os.environ, {'GAIANET_BASE_URL': 'http://test', 'GAIANET_API_KEY': 'test-key'}):
    from app import (
        RequestValidator, DataPrivacyFilter, SecurityMonitor
    )


class TestXSSPrevention:
    """Test XSS prevention in message sanitization - CRITICAL for security"""
    
    def setup_method(self):
        self.validator = RequestValidator()
    
    def test_sanitize_content_removes_script_tags(self):
        """Test that script tags are removed from user input"""
        malicious_input = "Hello <script>alert('xss')</script> world"
        sanitized = self.validator.sanitize_content(malicious_input)
        assert "<script>" not in sanitized
        assert "alert" not in sanitized
        assert "Hello  world" == sanitized
    
    def test_sanitize_content_removes_javascript_protocol(self):
        """Test that javascript: protocol is removed"""
        malicious_input = "Click javascript:alert('xss') here"
        sanitized = self.validator.sanitize_content(malicious_input)
        assert "javascript:" not in sanitized
        assert "Click alert here" == sanitized


class TestSensitiveDataRedaction:
    """Test sensitive data detection and redaction - CRITICAL for privacy"""
    
    def setup_method(self):
        self.filter = DataPrivacyFilter()
    
    def test_detect_credit_card_numbers(self):
        """Test detection of credit card patterns"""
        text = "My card number is 4532-1234-5678-9012"
        findings = self.filter.detect_sensitive_data(text)
        assert len(findings) == 1
        assert findings[0][0] == "credit_card"
    
    def test_redact_sensitive_data_credit_card(self):
        """Test redaction of credit card numbers"""
        text = "Pay with card 4532-1234-5678-9012 please"
        redacted = self.filter.redact_sensitive_data(text)
        assert "4532-1234-5678-9012" not in redacted
        assert "[REDACTED_CREDIT_CARD]" in redacted


class TestRateLimiting:
    """Test IP-based rate limiting - CRITICAL for DoS protection"""
    
    def test_rate_limit_allows_normal_usage(self):
        """Test that normal usage is allowed"""
        monitor = SecurityMonitor()
        # Should allow first few requests
        assert monitor.check_rate_limit("192.168.1.1", limit=10, window=60)
        assert monitor.check_rate_limit("192.168.1.1", limit=10, window=60)
    
    def test_rate_limit_blocks_excessive_requests(self):
        """Test that excessive requests are blocked"""
        monitor = SecurityMonitor()
        ip = "192.168.1.100"
        limit = 5
        
        # Make requests up to limit
        for _ in range(limit):
            assert monitor.check_rate_limit(ip, limit=limit, window=60)
        
        # Next request should be blocked
        assert not monitor.check_rate_limit(ip, limit=limit, window=60)
        assert monitor.is_blocked(ip)


class TestSecurityHeaders:
    """Test security headers are properly set - CRITICAL for web security"""
    
    @pytest.fixture
    def client(self):
        # Import app with mocked environment
        with patch.dict(os.environ, {
            'GAIANET_BASE_URL': 'http://test', 
            'GAIANET_API_KEY': 'test-key',
            'GAIANET_MODEL': 'test-model'
        }):
            from app import app
            app.config['TESTING'] = True
            with app.test_client() as client:
                yield client
    
    def test_security_headers_present(self, client):
        """Test that security headers are added to responses"""
        response = client.get('/api/health')
        
        # Check critical security headers
        assert response.headers.get('Strict-Transport-Security') == "max-age=31536000; includeSubDomains"
        assert response.headers.get('X-Frame-Options') == "DENY"
        assert response.headers.get('X-Content-Type-Options') == "nosniff"
        assert response.headers.get('Referrer-Policy') == "strict-origin-when-cross-origin"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])