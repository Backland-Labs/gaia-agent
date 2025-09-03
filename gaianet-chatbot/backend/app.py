#!/usr/bin/env python3
"""
GaiaNet Chatbot Backend - Single file production-ready backend
Implements secure chat completion with GaiaNet integration
"""

import os
import re
import time
import json
import logging
import collections
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RequestValidator:
    """Input validation and XSS prevention (specs/security-privacy.md:176-248)"""

    def __init__(self):
        self.max_message_length = int(os.getenv("MAX_MESSAGE_LENGTH", "10000"))
        self.max_messages = 100
        self.allowed_roles = {"user", "assistant", "system"}

    def validate_chat_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize chat completion request"""
        validated = {}

        # Validate model
        model = request_data.get("model", "")
        if not re.match(r"^[a-zA-Z0-9_-]+$", model):
            raise ValueError("Invalid model name format")
        validated["model"] = model

        # Validate messages
        messages = request_data.get("messages", [])
        if not isinstance(messages, list) or len(messages) > self.max_messages:
            raise ValueError(
                f"Invalid messages format or too many messages (max: {self.max_messages})"
            )

        validated_messages = []
        for msg in messages:
            if not isinstance(msg, dict):
                raise ValueError("Message must be a dictionary")

            role = msg.get("role")
            if role not in self.allowed_roles:
                raise ValueError(f"Invalid role: {role}")

            content = msg.get("content", "")
            if len(content) > self.max_message_length:
                raise ValueError(f"Message too long (max: {self.max_message_length})")

            # Sanitize content
            sanitized_content = self.sanitize_content(content)

            validated_messages.append({"role": role, "content": sanitized_content})

        validated["messages"] = validated_messages

        # Validate optional parameters
        if "max_tokens" in request_data:
            max_tokens = request_data["max_tokens"]
            if not isinstance(max_tokens, int) or max_tokens < 1 or max_tokens > 4096:
                raise ValueError("Invalid max_tokens value")
            validated["max_tokens"] = max_tokens

        if "temperature" in request_data:
            temp = request_data["temperature"]
            if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
                raise ValueError("Invalid temperature value")
            validated["temperature"] = temp

        return validated

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
    """Sensitive data detection and redaction (specs/security-privacy.md:258-308)"""

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

    def validate_request_privacy(self, messages: List[Dict]) -> List[str]:
        """Validate request doesn't contain sensitive data"""
        violations = []
        for i, message in enumerate(messages):
            content = message.get("content", "")
            sensitive_data = self.detect_sensitive_data(content)
            if sensitive_data:
                violations.append(
                    f"Message {i}: Found {[d[0] for d in sensitive_data]}"
                )
        return violations


class SecurityMonitor:
    """Simple in-memory rate limiting (specs/security-privacy.md:516-535)"""

    def __init__(self):
        self.rate_limits = collections.defaultdict(list)
        self.failed_attempts = collections.defaultdict(int)
        self.blocked_ips = set()

    def check_rate_limit(
        self, ip_address: str, limit: int = 100, window: int = 3600
    ) -> bool:
        """Check if IP is within rate limits"""
        if limit == 100:  # Use default from env
            limit = int(os.getenv("RATE_LIMIT_PER_HOUR", "100"))

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
        logger.warning("Blocked IP %s: %s", ip_address, reason)


class SecureGaiaClient:
    """Secure GaiaNet client wrapper (specs/security-privacy.md:91-125)"""

    def __init__(self):
        self.base_url = os.getenv("GAIANET_BASE_URL")
        self.api_key = os.getenv("GAIANET_API_KEY")
        self.model = os.getenv("GAIANET_MODEL", "default")

        if not self.base_url or not self.api_key:
            raise ValueError("GAIANET_BASE_URL and GAIANET_API_KEY must be set")

        # Initialize OpenAI client for GaiaNet (specs/api-integration-patterns.md:15-22)
        self.client = openai.OpenAI(base_url=self.base_url, api_key=self.api_key)

    def chat_completion(self, messages: List[Dict], model: str = "", **kwargs):
        """Secure chat completion with validation"""
        try:
            response = self.client.chat.completions.create(
                model=model or self.model, messages=messages, **kwargs
            )
            return response
        except openai.BadRequestError as e:
            logger.error("Bad request to GaiaNet: %s", e)
            raise ValueError("Invalid request format")
        except openai.NotFoundError as e:
            logger.error(f"Model not found: {e}")
            raise ValueError("Model not available")
        except openai.InternalServerError as e:
            logger.error(f"GaiaNet server error: {e}")
            raise RuntimeError("Service temporarily unavailable")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise RuntimeError("Request failed")


# Initialize global components
app = Flask(__name__)
CORS(app)

request_validator = RequestValidator()
privacy_filter = DataPrivacyFilter()
security_monitor = SecurityMonitor()
gaia_client = None

try:
    gaia_client = SecureGaiaClient()
except ValueError as e:
    logger.warning(f"GaiaNet client not initialized: {e}")


@app.before_request
def security_checks():
    """Security checks before processing requests"""
    client_ip = request.environ.get("HTTP_X_REAL_IP", request.remote_addr)

    # Check if IP is blocked
    if security_monitor.is_blocked(client_ip):
        return jsonify({"error": "Access denied"}), 403

    # Rate limiting
    if not security_monitor.check_rate_limit(client_ip):
        return jsonify({"error": "Rate limit exceeded"}), 429


@app.after_request
def security_headers(response):
    """Add security headers to all responses"""
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint (specs/api-integration-patterns.md:278-313)"""
    status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
    }

    # Check GaiaNet connectivity if client is available
    if gaia_client:
        try:
            # Simple test request
            test_response = gaia_client.client.chat.completions.create(
                model=gaia_client.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
            )
            status["gaianet_status"] = "connected"
        except Exception as e:
            status["gaianet_status"] = "error"
            status["gaianet_error"] = str(e)
    else:
        status["gaianet_status"] = "not_configured"

    return jsonify(status)


@app.route("/api/chat", methods=["POST"])
def chat_completion():
    """Send message and get response"""
    try:
        if not gaia_client:
            return jsonify({"error": "GaiaNet not configured"}), 500

        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        # Convert simple message format to OpenAI format
        if "message" in data:
            messages = [{"role": "user", "content": data["message"]}]
            model = data.get("model", gaia_client.model)
        else:
            messages = data.get("messages", [])
            model = data.get("model", gaia_client.model)

        # Create request for validation
        chat_request = {"model": model, "messages": messages}

        # Add optional parameters
        if "max_tokens" in data:
            chat_request["max_tokens"] = data["max_tokens"]
        if "temperature" in data:
            chat_request["temperature"] = data["temperature"]

        # Validate request
        validated_request = request_validator.validate_chat_request(chat_request)

        # Privacy check
        if os.getenv("ENABLE_DATA_PRIVACY_FILTER", "true").lower() == "true":
            violations = privacy_filter.validate_request_privacy(
                validated_request["messages"]
            )
            if violations:
                return jsonify({"error": "Privacy violation detected"}), 400

        # Make request to GaiaNet
        response = gaia_client.chat_completion(
            messages=validated_request["messages"],
            model=validated_request["model"],
            **{
                k: v
                for k, v in validated_request.items()
                if k not in ["model", "messages"]
            },
        )

        # Extract response content
        content = response.choices[0].message.content

        # Ensure content is a string
        if content is None:
            content = ""
        else:
            content = str(content)

        # Redact sensitive data from response
        if os.getenv("ENABLE_DATA_PRIVACY_FILTER", "true").lower() == "true":
            content = privacy_filter.redact_sensitive_data(content)

        return jsonify(
            {
                "response": content,
                "model": response.model if hasattr(response, "model") else model,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error("Unexpected error in chat completion: %s", e)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/chat/stream", methods=["GET"])
def chat_stream():
    """SSE endpoint for streaming responses (specs/api-integration-patterns.md:59-71)"""

    def generate():
        try:
            # Get parameters from query string
            message = request.args.get("message")
            model = request.args.get(
                "model", gaia_client.model if gaia_client else "default"
            )

            if not message:
                yield f"data: {json.dumps({'error': 'Message parameter required'})}\n\n"
                return

            if not gaia_client:
                yield f"data: {json.dumps({'error': 'GaiaNet not configured'})}\n\n"
                return

            # Validate message
            chat_request = {
                "model": model,
                "messages": [{"role": "user", "content": message}],
            }

            validated_request = request_validator.validate_chat_request(chat_request)

            # Stream response from GaiaNet
            stream = gaia_client.client.chat.completions.create(
                model=validated_request["model"],
                messages=validated_request["messages"],
                stream=True,
            )

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content

                    # Redact sensitive data from streaming content
                    if (
                        os.getenv("ENABLE_DATA_PRIVACY_FILTER", "true").lower()
                        == "true"
                    ):
                        content = privacy_filter.redact_sensitive_data(content)

                    yield f"data: {json.dumps({'content': content})}\n\n"

            # Send completion signal
            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


if __name__ == "__main__":
    # Configuration
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "8080"))
    debug = os.getenv("FLASK_ENV") == "development"

    logger.info("Starting GaiaNet Chatbot Backend on %s:%s", host, port)
    app.run(host=host, port=port, debug=debug)
