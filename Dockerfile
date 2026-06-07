# Use an official lightweight Python image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies (NO WEASYPRINT)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Python-д код хайх замыг зааж өгөх
ENV PYTHONPATH=/app

# Make port 10000 available to the world outside the container
EXPOSE 10000

# Run the FastAPI application using uvicorn
CMD ["uvicorn", "src.trueroas.main:app", "--host", "0.0.0.0", "--port", "10000"]