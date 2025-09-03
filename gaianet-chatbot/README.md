# GaiaNet Chatbot

A production-ready chatbot backend that integrates directly with GaiaNet's OpenAI-compatible APIs. Built with comprehensive security features, input validation, and data privacy protection.

## Features

- **Direct GaiaNet Integration**: Uses OpenAI Python client for seamless GaiaNet API access
- **Security First**: Input sanitization, XSS prevention, data privacy filtering, and rate limiting
- **Production Ready**: Comprehensive error handling, logging, and health monitoring
- **Streaming Support**: Server-Sent Events (SSE) for real-time response streaming
- **Simple Architecture**: Single Python file backend for easy deployment and maintenance

## Quick Start

1. **Copy environment configuration**:
   ```bash
   cp backend/.env.example backend/.env
   ```

2. **Configure your GaiaNet node**:
   Edit `backend/.env` and set:
   ```env
   GAIANET_BASE_URL=https://your-node.gaia.domains
   GAIANET_API_KEY=your-api-key
   GAIANET_MODEL=your-model
   ```

3. **Run with Docker**:
   ```bash
   docker build -t gaianet-chatbot .
   docker run -p 8080:8080 --env-file backend/.env gaianet-chatbot
   ```

4. **Or run directly**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   python app.py
   ```

5. **Access the API**:
   - Health check: http://localhost:8080/api/health
   - Chat endpoint: POST to http://localhost:8080/api/chat
   - Streaming: http://localhost:8080/api/chat/stream?message=Hello

## API Endpoints

### POST /api/chat
Send a chat message and receive a response.

**Request:**
```json
{
  "message": "Hello, how are you?",
  "model": "your-model",
  "max_tokens": 150,
  "temperature": 0.7
}
```

**Response:**
```json
{
  "response": "Hello! I'm doing well, thank you for asking.",
  "model": "your-model",
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

### GET /api/chat/stream
Stream chat responses in real-time using Server-Sent Events.

**Parameters:**
- `message`: The chat message (required)
- `model`: Model to use (optional, uses default if not specified)

**Response:** Stream of JSON events

### GET /api/health
Check service health and GaiaNet connectivity.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "version": "1.0.0",
  "gaianet_status": "connected"
}
```

## Configuration

Configuration is handled through environment-specific files:

### Environment Files
- **Development**: Use `backend/.env.development` for local development
- **Production**: Use `backend/.env.production` for production deployment
- **Testing**: Copy and modify `.env.example` for testing

### Required Settings
- `GAIANET_BASE_URL`: Your GaiaNet node URL
- `GAIANET_API_KEY`: Your GaiaNet API key (minimum 16 characters)
- `GAIANET_MODEL`: Default model to use

### Security Settings
- `RATE_LIMIT_PER_HOUR`: Max requests per IP per hour (default: 100)
- `MAX_MESSAGE_LENGTH`: Max message length in characters (default: 10000)
- `ENABLE_DATA_PRIVACY_FILTER`: Enable PII detection and redaction (default: true)

### Server Settings
- `SERVER_HOST`: Server bind address (127.0.0.1 for dev, 0.0.0.0 for prod)
- `SERVER_PORT`: Server port (default: 8080)
- `FLASK_ENV`: 'development' or 'production'

### Performance Tuning (Based on specs/configuration-optimization.md)
**Development:**
- `CHAT_CTX_SIZE`: 8192 (faster iteration)
- `CHAT_BATCH_SIZE`: 32 (lower latency)
- `EMBEDDING_CTX_SIZE`: 4096
- `EMBEDDING_BATCH_SIZE`: 16

**Production:**
- `CHAT_CTX_SIZE`: 16384 (better quality)
- `CHAT_BATCH_SIZE`: 128 (higher throughput)
- `EMBEDDING_CTX_SIZE`: 8192
- `EMBEDDING_BATCH_SIZE`: 64

### Configuration Validation
Validate your configuration files:
```bash
python backend/validate_config.py backend/.env.development
python backend/validate_config.py backend/.env.production
```

## Security Features

### Input Validation
- XSS prevention through content sanitization
- Model name validation
- Message length limits
- Parameter type validation

### Data Privacy
Automatic detection and redaction of:
- Credit card numbers
- Social Security Numbers
- Email addresses
- Phone numbers
- API keys and tokens
- Passwords

### Rate Limiting
- IP-based rate limiting with configurable limits
- Automatic blocking of abusive IPs
- Configurable time windows

### Security Headers
- Strict Transport Security (HSTS)
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- Referrer-Policy: strict-origin-when-cross-origin

## Development

### Running Tests
```bash
# All tests
python -m pytest tests/ -v

# Security tests specifically
python -m pytest tests/test_security_standalone.py -v

# Configuration validation
python backend/validate_config.py backend/.env.development
```

### Security Testing
```bash
# Security vulnerability scanning
bandit -r backend/

# Check for critical security issues
python -m pytest tests/test_security_standalone.py::TestXSSPrevention -v
python -m pytest tests/test_security_standalone.py::TestSensitiveDataRedaction -v
python -m pytest tests/test_security_standalone.py::TestRateLimiting -v
```

### Code Quality
```bash
# Format code
black backend/

# Lint code
pylint backend/app.py
```

### Project Structure
```
gaianet-chatbot/
├── backend/
│   ├── app.py                    # Main application with security features
│   ├── ui.py                     # Streamlit web interface
│   ├── validate_config.py        # Configuration validation script
│   ├── requirements.txt          # Python dependencies
│   ├── .env.example             # Environment template
│   ├── .env.development         # Development configuration
│   ├── .env.production          # Production configuration
│   └── .env                     # Your current configuration (not in git)
├── tests/
│   ├── test_critical_path.py    # Core functionality tests
│   ├── test_ui.py              # UI integration tests
│   └── test_security_standalone.py  # Security feature tests
├── .gitignore
└── README.md
```

## Troubleshooting

### Common Issues

**"GaiaNet not configured" error:**
- Ensure `GAIANET_BASE_URL` and `GAIANET_API_KEY` are set in your `.env` file
- Check that your GaiaNet node is running and accessible

**Rate limiting errors:**
- Adjust `RATE_LIMIT_PER_HOUR` in your `.env` file
- Check if your IP was temporarily blocked

**Model not found errors:**
- Verify your `GAIANET_MODEL` setting matches available models
- Check your GaiaNet node's model configuration

**Connection errors:**
- Verify your GaiaNet node URL is correct and accessible
- Check firewall settings and network connectivity

For more detailed troubleshooting, check the application logs and the health check endpoint.

## Docker Deployment

### Quick Deploy with Script

1. **Configure environment**:
   ```bash
   # Copy and edit production environment file
   cp backend/.env.production .env
   # Edit .env with your GaiaNet node details
   ```

2. **Deploy with one command**:
   ```bash
   ./deploy.sh
   ```

The script will build the Docker image, start the container, and provide status information.

### Manual Docker Commands

**Build image**:
```bash
docker build -t gaianet-chatbot .
```

**Run container**:
```bash
docker run -d \
  --name chatbot \
  --env-file .env \
  -p 8080:8080 \
  --restart unless-stopped \
  gaianet-chatbot
```

**Check status**:
```bash
docker ps
docker logs chatbot
```

### Docker Compose (Alternative)

For local development with Docker Compose:

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Container Management

**Useful commands**:
```bash
# View logs
docker logs chatbot

# Stop container
docker stop chatbot

# Restart container
docker restart chatbot

# Remove container
docker rm -f chatbot

# Check image size
./check-image-size.sh gaianet-chatbot
```

### Image Optimization

The Docker image is optimized for production:
- Multi-stage build reduces image size (~100-150MB)
- Runs as non-root user for security
- Python 3.11-slim base for minimal footprint
- Health checks enabled for monitoring

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request