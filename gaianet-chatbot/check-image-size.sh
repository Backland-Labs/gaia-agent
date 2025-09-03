#!/bin/bash

# Check Docker image size for optimization verification
# Usage: ./check-image-size.sh [image-name]

IMAGE_NAME=${1:-"gaianet-chatbot"}

echo "📏 Checking Docker image size for: $IMAGE_NAME"

# Get image size
SIZE_OUTPUT=$(docker images "$IMAGE_NAME" --format "{{.Size}}" 2>/dev/null)

if [ -z "$SIZE_OUTPUT" ]; then
    echo "❌ Image '$IMAGE_NAME' not found. Build it first with:"
    echo "   docker build -t $IMAGE_NAME ."
    exit 1
fi

echo "📦 Image size: $SIZE_OUTPUT"

# Parse size to check if under 200MB
SIZE_VALUE=$(echo "$SIZE_OUTPUT" | sed 's/[^0-9.]//g')
SIZE_UNIT=$(echo "$SIZE_OUTPUT" | sed 's/[0-9.]//g')

case $SIZE_UNIT in
    *GB*)
        SIZE_MB=$(echo "$SIZE_VALUE * 1024" | bc -l)
        ;;
    *MB*)
        SIZE_MB=$SIZE_VALUE
        ;;
    *KB*)
        SIZE_MB=$(echo "$SIZE_VALUE / 1024" | bc -l)
        ;;
    *)
        SIZE_MB=0
        ;;
esac

# Check if under 200MB
if (( $(echo "$SIZE_MB < 200" | bc -l) )); then
    echo "✅ Image size is optimized (under 200MB limit)"
else
    echo "⚠️  Image size exceeds 200MB recommendation"
    echo "   Consider optimizing dependencies or using smaller base images"
fi

echo ""
echo "📊 Image details:"
docker images "$IMAGE_NAME" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"