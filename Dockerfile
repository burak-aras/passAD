FROM python:3.10-slim

# Proxy ayarları (build sırasında)
# ARG http_proxy
# ARG https_proxy
ENV http_proxy=$http_proxy
ENV https_proxy=$https_proxy

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libldap2-dev \
    libsasl2-dev \
    curl \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY admin.py .
COPY services/ ./services/
COPY jobs/ ./jobs/
COPY templates/ ./templates/
COPY static/ ./static/

# Create data directory
RUN mkdir -p /app/data

# Clear proxy for runtime
ENV http_proxy=
ENV https_proxy=

EXPOSE 80

CMD ["python3", "app.py"]
