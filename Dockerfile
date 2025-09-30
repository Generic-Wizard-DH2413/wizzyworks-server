# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the server directory
COPY server/ ./server/

# Create web directory if it doesn't exist
RUN mkdir -p server/web

# Expose ports
EXPOSE 8765 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Change to server directory and run the server
WORKDIR /app/server
CMD ["python", "server.py"]