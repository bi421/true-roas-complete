# Use an official lightweight Python image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# INSTALL SYSTEM DEPENDENCIES FOR WEASYPRINT & BUILD TOOLS FOR PIP
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libcairo2 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# ШИЙДЭЛ: Python-д код хайх замыг зааж өгөх
ENV PYTHONPATH=/app

# Make port 10000 available to the world outside the container
EXPOSE 10000

# Run the FastAPI application using uvicorn
CMD ["uvicorn", "src.trueroas.main:app", "--host", "0.0.0.0", "--port", "10000"]