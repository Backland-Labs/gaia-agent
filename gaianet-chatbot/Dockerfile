# Build stage
FROM python:3.11-slim as builder

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 chatbot

# Install dependencies from builder
COPY --from=builder /root/.local /home/chatbot/.local

# Copy application code
WORKDIR /app
COPY backend/ .
RUN chown -R chatbot:chatbot /app

# Switch to non-root user
USER chatbot

# Add user's local bin to PATH
ENV PATH=/home/chatbot/.local/bin:$PATH

EXPOSE 8080

CMD ["python", "app.py"]