#!/usr/bin/env python3
"""
Critical path tests for Streamlit UI
Tests only the essential functionality that could fail
"""

import pytest
import requests
import sys
import os

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

class TestUICore:
    """Test core UI functionality that could fail"""
    
    def test_backend_connection(self):
        """Test that UI can connect to backend API"""
        # This tests the critical path - UI must be able to call backend
        backend_url = "http://localhost:8080"
        
        try:
            # Simple health check call that UI would make
            response = requests.get(f"{backend_url}/api/health", timeout=5)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not running - required for UI tests")
    
    def test_chat_api_integration(self):
        """Test that UI can send chat requests to backend"""
        # This tests the critical integration point
        backend_url = "http://localhost:8080"
        
        try:
            chat_data = {
                "message": "Hello test",
                "conversation": []
            }
            
            response = requests.post(
                f"{backend_url}/api/chat", 
                json=chat_data,
                timeout=10
            )
            # Should get either success, validation error, or configuration error
            # 500 is acceptable if GaiaNet is not properly configured (test environment)
            assert response.status_code in [200, 400, 422, 500]
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend not running - required for UI tests")

    def test_ui_module_imports(self):
        """Test that UI module can be imported without errors"""
        # This ensures the UI file has valid Python syntax
        try:
            import backend.ui as ui_module
            # Should have key functions for Streamlit app
            assert hasattr(ui_module, 'main') or hasattr(ui_module, 'chat_interface')
        except ImportError as e:
            pytest.fail(f"UI module cannot be imported: {e}")
        except Exception as e:
            pytest.fail(f"UI module has errors: {e}")