# Multi-stage build for PDF Parser application
# Stage 1: Build Next.js frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY pdf-parser-client/package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY pdf-parser-client/ ./

# Build Next.js app
RUN npm run build

# Stage 2: Python backend with frontend static files
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for matplotlib and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy backend source code
COPY app.py ./
COPY generate_exam.py ./
COPY generate_variants.py ./
COPY draw_geometry.py ./
COPY llm_tracker.py ./
COPY config/ ./config/

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/frontend/.next/standalone ./frontend/
COPY --from=frontend-builder /app/frontend/.next/static ./frontend/.next/static
COPY --from=frontend-builder /app/frontend/public ./frontend/public

# Create necessary directories
RUN mkdir -p data flask_uploads variants_output

# Environment variables
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Expose ports (Flask: 4001, Next.js: 3000)
EXPOSE 4001 3000

# Copy startup script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
