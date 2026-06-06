FROM python:3.11-slim
WORKDIR /app
# Install system dependencies for WeasyPrint and healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libpangocairo-1.0-0 \
    shared-mime-info \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "trueroas.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8001"]