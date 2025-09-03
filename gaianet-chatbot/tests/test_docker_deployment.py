#!/usr/bin/env python3
"""
Docker deployment tests - Critical path testing for containerized deployment
Tests only essential deployment functionality to ensure production readiness.
"""

import pytest
import subprocess
import time
import requests
import os
from typing import Dict, Any


class TestDockerDeployment:
    """Critical tests for Docker container deployment"""
    
    @pytest.fixture(scope="class")
    def docker_image_name(self):
        """Docker image name for testing"""
        return "gaianet-chatbot-test"
    
    def test_docker_image_builds_successfully(self, docker_image_name: str):
        """Test that Docker image builds without errors"""
        # Build the Docker image
        result = subprocess.run([
            "docker", "build", 
            "-t", docker_image_name, 
            "."
        ], cwd="/Users/max/code/gaiaai-specs/gaianet-chatbot", 
           capture_output=True, text=True)
        
        assert result.returncode == 0, f"Docker build failed: {result.stderr}"
        assert "Successfully tagged" in result.stdout or "Successfully built" in result.stdout
    
    def test_container_starts_and_serves_app(self, docker_image_name: str):
        """Test that container starts and serves the application on port 8080"""
        # Start container in detached mode
        container_name = f"{docker_image_name}-test"
        
        # Clean up any existing container
        subprocess.run(["docker", "rm", "-f", container_name], 
                      capture_output=True)
        
        # Start new container
        result = subprocess.run([
            "docker", "run", "-d", 
            "--name", container_name,
            "-p", "8080:8080",
            "-e", "GAIANET_API_KEY=test_key",
            "-e", "GAIANET_BASE_URL=https://test.gaianet.ai",
            docker_image_name
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, f"Container failed to start: {result.stderr}"
        
        try:
            # Wait for container to start
            time.sleep(3)
            
            # Test health endpoint
            response = requests.get("http://localhost:8080/health", timeout=5)
            assert response.status_code == 200
            
            health_data = response.json()
            assert health_data.get("status") == "healthy"
            
        finally:
            # Clean up container
            subprocess.run(["docker", "rm", "-f", container_name], 
                          capture_output=True)
    
    def test_image_size_optimized(self, docker_image_name: str):
        """Test that Docker image size is under 200MB for optimization"""
        result = subprocess.run([
            "docker", "images", docker_image_name, 
            "--format", "{{.Size}}"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, f"Failed to get image size: {result.stderr}"
        
        size_str = result.stdout.strip()
        # Parse size (e.g., "180MB", "1.2GB")
        size_value = float(size_str.replace("MB", "").replace("GB", ""))
        
        if "GB" in size_str:
            size_mb = size_value * 1024  # Convert GB to MB
        else:
            size_mb = size_value
            
        assert size_mb < 200, f"Image size {size_mb}MB exceeds 200MB limit"