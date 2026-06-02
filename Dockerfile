# Stage 1: Builder
FROM python:3.12-slim as builder
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential python3-dev
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim
WORKDIR /app

# Install system dependencies for WeasyPrint (PDF Generation)
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY src/ ./src/
COPY main.py .

# Production Persistence Setup
RUN mkdir -p data/tenants data/logs

ENV APP_HOST=0.0.0.0
ENV APP_PORT=8001

EXPOSE 8001
CMD ["uvicorn", "src.trueroas.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]