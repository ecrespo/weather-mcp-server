FROM python:3.13.7-slim-trixie AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies to virtual environment
RUN uv sync --frozen --no-cache

# Production stage
FROM python:3.13.7-slim-trixie AS production

LABEL authors="Ernesto Crespo <ecrespo@gmail.com>"

# Install only runtime dependencies and clean up in single layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && useradd -m -u 1000 -s /bin/sh mcpuser

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder --chown=mcpuser:mcpuser /app/.venv /app/.venv

# Copy source code
COPY --chown=mcpuser:mcpuser utils ./utils/
COPY --chown=mcpuser:mcpuser weather.py ./

# Switch to non-root user
USER mcpuser

# Use direct Python execution (lighter than uv run)
CMD ["python3", "weather.py"]