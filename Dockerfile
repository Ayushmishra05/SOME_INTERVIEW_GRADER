# Use official Python base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install speechRecognition
RUN pip install mediapipe
# Copy all source files
COPY . .

# Expose Flask port
EXPOSE 80

# Start the app
CMD ["python", "app.py"]