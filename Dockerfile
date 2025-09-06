# Use official Python runtime as parent image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender1 \
    imagemagick \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Relax ImageMagick security policy to allow MoviePy/Captacity to read text via @/tmp/*.txt
# This adjusts the default Debian policy that blocks '@*' paths.
RUN set -eux; \
  for f in /etc/ImageMagick-6/policy.xml /etc/ImageMagick-7/policy.xml; do \
    if [ -f "$f" ]; then \
      sed -i 's~<policy domain="path" rights="none" pattern="@\*"/>~<policy domain="path" rights="read|write" pattern="@\*"/>~' "$f" || true; \
      sed -i 's~<policy domain="coder" rights="none" pattern="MVG"/>~<policy domain="coder" rights="read|write" pattern="MVG"/>~' "$f" || true; \
    fi; \
  done

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run the application
ENTRYPOINT ["python", "main.py"]
