# Dockerfile for running the checkout service in a container.
#
# This is useful for running the API locally in an isolated environment
# and documents how the service would be containerised. The AWS
# deployment uses SAM and Lambda rather than this image, so this is an
# alternative way to run the same application.

FROM python:3.12-slim

# Set a working directory inside the container.
WORKDIR /app

# Install dependencies first so this layer is cached when only the
# application code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt uvicorn boto3

# Copy the application code.
COPY app ./app

# The API listens on port 8000 inside the container.
EXPOSE 8000

# Start the API with uvicorn. The host 0.0.0.0 makes it reachable from
# outside the container.
CMD ["uvicorn", "app.main:api", "--host", "0.0.0.0", "--port", "8000"]
