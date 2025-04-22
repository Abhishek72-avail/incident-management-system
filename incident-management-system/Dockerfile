FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV FLASK_APP=run.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5000

# Create a non-root user and switch to it
RUN useradd -m appuser
USER appuser

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]