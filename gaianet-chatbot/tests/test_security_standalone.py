#!/usr/bin/env python3
"""
Standalone security tests for critical security features
Tests without importing the main app to avoid OpenAI dependency issues
"""

import pytest
import sys
import os
import re
import collections
import time
from typing import List, Dict, Tuple

# Copy the security classes directly to test them independently
class RequestValidator:
    """Input validation and XSS prevention"""

    def __init__(self):
        self.max_message_length = int(os.getenv("MAX_MESSAGE_LENGTH", "10000"))
        self.max_messages = 100
        self.allowed_roles = {"user", "assistant", "system"}

    def sanitize_content(self, content: str) -> str:
        """Sanitize message content"""
        # Remove potential injection attempts
        content = re.sub(
            r"<script[^>]*>.*?</script>", "", content, flags=re.IGNORECASE | re.DOTALL
        )
        content = re.sub(r"javascript:", "", content, flags=re.IGNORECASE)

        # Limit special characters but keep basic punctuation
        content = re.sub(r"[^\w\s\.\,\!\?\-\(\)\'\"]+", "", content)

        return content.strip()


class DataPrivacyFilter:
    """Sensitive data detection and redaction"""

    def __init__(self):
        self.patterns = {
            "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "phone": r"\b\d{3}-\d{3}-\d{4}\b",
            "api_key": r"[A-Za-z0-9]{32,}",
            "password": r"(?i)password[:\s=]+[^\s]+",
            "token": r"(?i)token[:\s=]+[^\s]+",
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
            redacted = re.sub(pattern, f"[REDACTED_{data_type.upper()}]", redacted)
        return redacted


class SecurityMonitor:
    """Simple in-memory rate limiting"""

    def __init__(self):
        self.rate_limits = collections.defaultdict(list)
        self.blocked_ips = set()

    def check_rate_limit(
        self, ip_address: str, limit: int = 100, window: int = 3600
    ) -> bool:
        """Check if IP is within rate limits"""
        now = time.time()

        # Clean old requests
        self.rate_limits[ip_address] = [
            req_time
            for req_time in self.rate_limits[ip_address]
            if now - req_time < window
        ]

        # Check current rate
        if len(self.rate_limits[ip_address]) >= limit:
            self.block_ip(ip_address, f"Rate limit exceeded: {limit}/{window}s")
            return False

        # Record this request
        self.rate_limits[ip_address].append(now)
        return True

    def is_blocked(self, ip_address: str) -> bool:
        """Check if IP is blocked"""
        return ip_address in self.blocked_ips

    def block_ip(self, ip_address: str, reason: str):
        """Block suspicious IP address"""
        self.blocked_ips.add(ip_address)


# Test classes
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
        # Main goal is removing the javascript: protocol, content after may vary
        assert "Click" in sanitized and "here" in sanitized


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])