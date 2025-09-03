#!/bin/bash

# Test Docker deployment health
# Usage: ./test-deployment.sh [port]

PORT=${1:-8080}
HOST="localhost"
URL="http://$HOST:$PORT"

echo "🔍 Testing GaiaNet Chatbot deployment at $URL"

# Test health endpoint
echo "📡 Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s -f "$URL/health" || echo "FAILED")

if [ "$HEALTH_RESPONSE" = "FAILED" ]; then
    echo "❌ Health check failed - is the container running?"
    echo "   Try: docker ps | grep chatbot"
    exit 1
fi

# Parse health response
STATUS=$(echo "$HEALTH_RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

if [ "$STATUS" = "healthy" ]; then
    echo "✅ Health check passed"
else
    echo "⚠️  Health check returned: $STATUS"
fi

# Test API endpoint structure
echo "🔌 Testing API endpoint structure..."
API_RESPONSE=$(curl -s "$URL/api/health" || echo "FAILED")

if [ "$API_RESPONSE" != "FAILED" ]; then
    echo "✅ API endpoint accessible"
else
    echo "⚠️  API endpoint not accessible"
fi

# Check if using HTTPS (for production)
if [[ "$URL" == "https://"* ]]; then
    echo "🔒 HTTPS connection detected"
else
    echo "🔓 HTTP connection (OK for development)"
fi

echo ""
echo "📊 Deployment Summary:"
echo "   Health Status: $STATUS"
echo "   Endpoint: $URL/health"
echo "   API: $URL/api/health"
echo ""
echo "🚀 Ready for chat requests at: $URL/api/chat"