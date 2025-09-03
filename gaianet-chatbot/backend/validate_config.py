#!/usr/bin/env python3
"""
Configuration validation script for GaiaNet Chatbot Backend
Validates environment-specific configurations for security and performance
"""

import os
import sys
import re
from typing import List, Dict, Any
from urllib.parse import urlparse

class ConfigValidator:
    """Validate environment configuration settings"""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
    
    def validate_gaianet_config(self, config: Dict[str, str]) -> None:
        """Validate GaiaNet connection settings"""
        # Check base URL format
        base_url = config.get('GAIANET_BASE_URL', '')
        if not base_url:
            self.issues.append("GAIANET_BASE_URL is required")
        else:
            parsed = urlparse(base_url)
            if not parsed.scheme or not parsed.netloc:
                self.issues.append("GAIANET_BASE_URL must be a valid URL")
            elif parsed.scheme not in ['http', 'https']:
                self.issues.append("GAIANET_BASE_URL must use http or https")
        
        # Check API key strength
        api_key = config.get('GAIANET_API_KEY', '')
        if not api_key:
            self.issues.append("GAIANET_API_KEY is required")
        elif api_key in ['dev-key-placeholder', 'REPLACE_WITH_PRODUCTION_API_KEY', 'your-api-key']:
            self.issues.append("GAIANET_API_KEY must be set to a real value")
        elif len(api_key) < 16:
            self.issues.append("GAIANET_API_KEY appears too short (minimum 16 characters)")
        
        # Check model name
        model = config.get('GAIANET_MODEL', '')
        if not model:
            self.warnings.append("GAIANET_MODEL not set, will use default")
    
    def validate_performance_config(self, config: Dict[str, str]) -> None:
        """Validate performance-related settings"""
        # Context size validation
        chat_ctx = config.get('CHAT_CTX_SIZE', '16384')
        try:
            ctx_size = int(chat_ctx)
            if ctx_size < 1024:
                self.warnings.append("CHAT_CTX_SIZE very low, may affect quality")
            elif ctx_size > 32768:
                self.warnings.append("CHAT_CTX_SIZE very high, may cause memory issues")
        except ValueError:
            self.issues.append("CHAT_CTX_SIZE must be a valid integer")
        
        # Batch size validation
        batch_size = config.get('CHAT_BATCH_SIZE', '128')
        try:
            batch = int(batch_size)
            if batch < 1:
                self.issues.append("CHAT_BATCH_SIZE must be positive")
            elif batch > 512:
                self.warnings.append("CHAT_BATCH_SIZE very high, may cause memory issues")
        except ValueError:
            self.issues.append("CHAT_BATCH_SIZE must be a valid integer")
    
    def validate_security_config(self, config: Dict[str, str]) -> None:
        """Validate security settings"""
        # Rate limiting
        rate_limit = config.get('RATE_LIMIT_PER_HOUR', '100')
        try:
            limit = int(rate_limit)
            if limit < 1:
                self.issues.append("RATE_LIMIT_PER_HOUR must be positive")
            elif limit > 10000:
                self.warnings.append("RATE_LIMIT_PER_HOUR very high, may not provide DoS protection")
        except ValueError:
            self.issues.append("RATE_LIMIT_PER_HOUR must be a valid integer")
        
        # Message length
        max_msg_len = config.get('MAX_MESSAGE_LENGTH', '10000')
        try:
            max_len = int(max_msg_len)
            if max_len < 100:
                self.warnings.append("MAX_MESSAGE_LENGTH very low, may truncate normal messages")
            elif max_len > 100000:
                self.warnings.append("MAX_MESSAGE_LENGTH very high, may allow abuse")
        except ValueError:
            self.issues.append("MAX_MESSAGE_LENGTH must be a valid integer")
        
        # Privacy filter
        privacy_filter = config.get('ENABLE_DATA_PRIVACY_FILTER', 'true').lower()
        if privacy_filter not in ['true', 'false']:
            self.issues.append("ENABLE_DATA_PRIVACY_FILTER must be true or false")
    
    def validate_server_config(self, config: Dict[str, str]) -> None:
        """Validate server settings"""
        # Host binding
        host = config.get('SERVER_HOST', '0.0.0.0')
        if config.get('FLASK_ENV') == 'development' and host == '0.0.0.0':
            self.warnings.append("SERVER_HOST set to 0.0.0.0 in development - consider 127.0.0.1")
        
        # Port validation
        port = config.get('SERVER_PORT', '8080')
        try:
            port_num = int(port)
            if port_num < 1024 and os.getuid() != 0:
                self.warnings.append(f"Port {port_num} requires root privileges")
            elif port_num > 65535:
                self.issues.append("SERVER_PORT must be <= 65535")
        except ValueError:
            self.issues.append("SERVER_PORT must be a valid integer")
        except AttributeError:
            # os.getuid() not available on Windows
            pass
        
        # Environment validation
        flask_env = config.get('FLASK_ENV', 'production')
        if flask_env not in ['development', 'production']:
            self.warnings.append("FLASK_ENV should be 'development' or 'production'")
    
    def validate_production_specific(self, config: Dict[str, str]) -> None:
        """Additional validation for production environments"""
        if config.get('FLASK_ENV') == 'production':
            # Debug mode should be off
            debug = config.get('DEBUG_MODE', 'false').lower()
            if debug == 'true':
                self.issues.append("DEBUG_MODE should be false in production")
            
            # HTTPS for production
            base_url = config.get('GAIANET_BASE_URL', '')
            if base_url.startswith('http://'):
                self.warnings.append("Consider using HTTPS in production")
            
            # Stricter rate limiting
            rate_limit = int(config.get('RATE_LIMIT_PER_HOUR', '100'))
            if rate_limit > 1000:
                self.warnings.append("Consider lower rate limits for production")
    
    def validate_all(self, config: Dict[str, str]) -> bool:
        """Run all validation checks"""
        self.issues.clear()
        self.warnings.clear()
        
        self.validate_gaianet_config(config)
        self.validate_performance_config(config)
        self.validate_security_config(config)
        self.validate_server_config(config)
        self.validate_production_specific(config)
        
        return len(self.issues) == 0


def load_env_file(filepath: str) -> Dict[str, str]:
    """Load environment variables from file"""
    config = {}
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    except FileNotFoundError:
        print(f"ERROR: Configuration file {filepath} not found")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to read {filepath}: {e}")
        sys.exit(1)
    
    return config


def main():
    """Main validation function"""
    if len(sys.argv) != 2:
        print("Usage: python validate_config.py <env_file>")
        print("Examples:")
        print("  python validate_config.py .env.development")
        print("  python validate_config.py .env.production")
        sys.exit(1)
    
    env_file = sys.argv[1]
    
    print(f"Validating configuration: {env_file}")
    print("-" * 50)
    
    # Load configuration
    config = load_env_file(env_file)
    
    # Validate
    validator = ConfigValidator()
    is_valid = validator.validate_all(config)
    
    # Report results
    if validator.issues:
        print("CRITICAL ISSUES:")
        for issue in validator.issues:
            print(f"  ❌ {issue}")
        print()
    
    if validator.warnings:
        print("WARNINGS:")
        for warning in validator.warnings:
            print(f"  ⚠️  {warning}")
        print()
    
    if is_valid and not validator.warnings:
        print("✅ Configuration is valid!")
    elif is_valid:
        print("✅ Configuration is valid (with warnings)")
    else:
        print("❌ Configuration has critical issues")
        sys.exit(1)


if __name__ == "__main__":
    main()