FROM python:3.12-slim

# System deps for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir 'uvicorn[standard]'

# Copy backend
COPY backend/ ./backend/

# Copy agent (for OnsiteAgent.exe download)
COPY agent/ ./agent/

# Copy pre-built frontend
COPY frontend/dist/ ./frontend/dist/

# Set env
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

WORKDIR /app/backend

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
