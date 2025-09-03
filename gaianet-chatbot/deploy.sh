#!/bin/bash

# GaiaNet Chatbot Docker Deployment Script
# Builds and runs the containerized application

set -e  # Exit on any error

# Configuration
IMAGE_NAME="gaianet-chatbot"
CONTAINER_NAME="chatbot"
PORT="8080"
ENV_FILE=".env"

echo "🚀 Starting GaiaNet Chatbot deployment..."

# Check if environment file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Environment file $ENV_FILE not found!"
    echo "   Create one from .env.example or use backend/.env.production"
    exit 1
fi

echo "📦 Building Docker image..."
docker build -t "$IMAGE_NAME" .

echo "🧹 Cleaning up any existing container..."
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

echo "🏃 Starting new container..."
docker run -d \
  --name "$CONTAINER_NAME" \
  --env-file "$ENV_FILE" \
  -p "$PORT:$PORT" \
  --restart unless-stopped \
  --health-cmd="curl -f http://localhost:$PORT/health || exit 1" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  "$IMAGE_NAME"

echo "⏳ Waiting for container to start..."
sleep 3

# Check if container is running
if docker ps --filter "name=$CONTAINER_NAME" --format "{{.Names}}" | grep -q "^$CONTAINER_NAME$"; then
    echo "✅ Container started successfully!"
    echo "🌐 Application available at: http://localhost:$PORT"
    echo "📋 Container status:"
    docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    echo ""
    echo "📝 Useful commands:"
    echo "   View logs:    docker logs $CONTAINER_NAME"
    echo "   Stop:         docker stop $CONTAINER_NAME"
    echo "   Restart:      docker restart $CONTAINER_NAME"
    echo "   Remove:       docker rm -f $CONTAINER_NAME"
else
    echo "❌ Container failed to start!"
    echo "🔍 Checking logs..."
    docker logs "$CONTAINER_NAME"
    exit 1
fi