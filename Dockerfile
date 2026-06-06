FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python requirements
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN pip install gunicorn

# Copy project files
COPY . /app/

# Expose port
EXPOSE 8000

# Start server
CMD gunicorn config.wsgi:application --bind 0.0.0.0:$PORT

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ensure your startup command matches this:
CMD ["gunicorn", "GreenLoopAI.wsgi:application", "--bind", "0.0.0.0:10000"]
