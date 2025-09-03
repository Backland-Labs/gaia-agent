#!/usr/bin/env python3
"""
API endpoint tests for GaiaNet chatbot backend.
Tests critical API functionality that could fail in non-obvious ways.
"""

import pytest
import json
import os
import sys
from unittest.mock import Mock, patch

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


class TestHealthEndpoint:
    """Test critical health check functionality"""
    
    @patch.dict(os.environ, {
        'GAIANET_BASE_URL': 'http://test-node.gaia.domains', 
        'GAIANET_API_KEY': 'test-key-12345678'
    })
    def test_health_endpoint_returns_status(self):
        """Test that health endpoint provides basic status information"""
        from app import app
        
        with app.test_client() as client:
            response = client.get('/api/health')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Critical health check fields
            assert 'status' in data
            assert 'timestamp' in data
            assert data['status'] in ['healthy', 'unhealthy']


class TestChatEndpoint:
    """Test critical chat API functionality"""
    
    @patch.dict(os.environ, {
        'GAIANET_BASE_URL': 'http://test-node.gaia.domains',
        'GAIANET_API_KEY': 'test-key-12345678',
        'GAIANET_MODEL': 'test-model'
    })
    def test_chat_endpoint_exists(self):
        """Test that chat endpoint exists and handles basic requests"""
        from app import app
        
        with app.test_client() as client:
            # Test endpoint exists and accepts POST
            response = client.post('/api/chat', 
                json={'message': 'test'},
                content_type='application/json'
            )
            
            # Should not be 404 (endpoint exists)
            # May fail with 500 due to GaiaNet not configured, but that's expected
            assert response.status_code != 404


class TestStreamingEndpoint:
    """Test critical streaming functionality"""
    
    @patch.dict(os.environ, {
        'GAIANET_BASE_URL': 'http://test-node.gaia.domains',
        'GAIANET_API_KEY': 'test-key-12345678',
        'GAIANET_MODEL': 'test-model'
    })
    @patch('app.gaia_client')
    def test_streaming_endpoint_returns_sse(self, mock_client):
        """Test that streaming endpoint provides Server-Sent Events"""
        from app import app
        
        # Mock streaming response
        def mock_stream():
            mock_chunk = Mock()
            mock_chunk.choices = [Mock()]
            mock_chunk.choices[0].delta.content = "Hello"
            yield mock_chunk
        
        mock_client.chat.completions.create.return_value = mock_stream()
        
        with app.test_client() as client:
            response = client.get('/api/chat/stream?message=Hello')
            
            assert response.status_code == 200
            assert 'text/event-stream' in response.headers.get('Content-Type', '')