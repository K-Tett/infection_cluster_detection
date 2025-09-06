# NOTE: FastAPI backend container with PostgreSQL integration for medical data processing
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for PostgreSQL and health checks
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and data files
COPY . .
COPY ../data/*.csv /app/data/

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser
#RUN chown -R appuser:appuser /app
#USER appuser

# Create necessary directories and set permissions
RUN mkdir -p /app/data /app/uploads \
    && chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "from database import test_connection; exit(0 if test_connection() else 1)"

# Start FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]