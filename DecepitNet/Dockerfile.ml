# ML Pipeline Dockerfile
# Multi-stage build for production deployment

FROM python:3.10-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.10-slim

# Set labels
LABEL maintainer="DECEPTINET Team"
LABEL description="DECEPTINET ML Pipeline with Kafka Consumer"
LABEL version="1.0.0"

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash mlpipeline && \
    mkdir -p /app /data /logs /models && \
    chown -R mlpipeline:mlpipeline /app /data /logs /models

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/mlpipeline/.local

# Copy application code
COPY --chown=mlpipeline:mlpipeline . .

# Set Python path
ENV PATH=/home/mlpipeline/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER mlpipeline

# Health check (check if process is running)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD pgrep -f "ml/kafka_consumer.py" || exit 1

# Run the ML Kafka consumer
CMD ["python", "-m", "ml.kafka_consumer"]
