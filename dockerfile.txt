# Base stage with common dependencies
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs && \
    chown -R appuser:appuser /app

# Development stage
FROM base as development

# Install development dependencies
RUN pip install pytest pytest-asyncio black isort flake8

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Development command (can be overridden)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base as production

# Remove unnecessary files
RUN rm -rf /app/tests /app/.git /app/.gitignore /app/README.md

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]

# Migration stage
FROM base as migration

# Install additional tools for migrations
RUN pip install alembic

# Switch to non-root user
USER appuser

# Migration command
CMD ["alembic", "upgrade", "head"]

# Testing stage
FROM development as testing

# Copy test files
COPY tests/ /app/tests/

# Install additional testing dependencies
RUN pip install pytest-cov pytest-mock httpx

# Run tests
CMD ["python", "-m", "pytest", "tests/", "-v", "--cov=app", "--cov-report=html"]