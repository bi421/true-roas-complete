# Stage 1: Build dependencies
FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Production image
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies (curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -u 1000 -m trueroas

COPY --from=builder /install /usr/local
COPY . .

# Secure filesystem: Code is read-only for the user, data is writable
RUN chown -R root:root /app && chmod -R 555 /app && \
    mkdir -p /app/data && chown -R trueroas:trueroas /app/data && \
    chmod -R 770 /app/data

USER 1000
CMD ["uvicorn", "src.trueroas.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4"]