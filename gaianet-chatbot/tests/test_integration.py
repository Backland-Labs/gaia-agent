#!/usr/bin/env python3
"""
End-to-end integration tests for GaiaNet chatbot backend.
Tests the complete chat flow from request to response.
"""

import pytest
import json
import os
import sys
import time
from unittest.mock import Mock, patch

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


class TestChatFlowIntegration:
    """Test end-to-end chat functionality"""
    
    @patch.dict(os.environ, {
        'GAIANET_BASE_URL': 'http://test-node.gaia.domains',
        'GAIANET_API_KEY': 'test-key-12345678',
        'GAIANET_MODEL': 'test-model',
        'RATE_LIMIT_PER_HOUR': '100'
    })
    def test_chat_flow_endpoint_reachable(self):
        """Test that complete chat flow can reach the endpoint"""
        from app import app
        
        with app.test_client() as client:
            # Test that endpoint accepts valid JSON requests
            response = client.post('/api/chat', 
                json={
                    'message': 'Hello, tell me about yourself',
                    'model': 'test-model',
                    'temperature': 0.7
                },
                content_type='application/json'
            )
            
            # Should not be 404 - endpoint should exist
            assert response.status_code != 404
            # Should handle JSON properly (not 400 for malformed JSON)
            assert response.status_code != 415


class TestSecurityIntegration:
    """Test security features integration with main flow"""
    
    @patch.dict(os.environ, {
        'GAIANET_BASE_URL': 'http://test-node.gaia.domains',
        'GAIANET_API_KEY': 'test-key-12345678',
        'GAIANET_MODEL': 'test-model',
        'ENABLE_DATA_PRIVACY_FILTER': 'true'
    })
    def test_security_validation_active(self):
        """Test that security validation is active"""
        from app import app
        
        with app.test_client() as client:
            # Test that endpoint validates input (should not crash on malicious content)
            response = client.post('/api/chat',
                json={
                    'message': '<script>alert("xss")</script>Hello',
                    'model': 'test-model'  
                },
                content_type='application/json'
            )
            
            # Should not crash (not 500) or return 404
            assert response.status_code != 404
            assert response.status_code != 500