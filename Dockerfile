# Lambda-optimized Dockerfile for Audifyy Backend
FROM public.ecr.aws/lambda/python:3.11

# Set environment variables for Lambda
ENV PYTHONPATH=/var/task
ENV AWS_LAMBDA_FUNCTION_NAME=audifyy-backend

# Install system dependencies required for our application
RUN dnf update -y && \
    dnf install -y \
        gcc \
        gcc-c++ \
        make \
        libnss3 \
        libXrandr \
        libXcomposite \
        libXcursor \
        libXdamage \
        libXext \
        libXi \
        libXtst \
        cups-libs \
        libXScrnSaver \
        libXrandr \
        GConf2 \
        alsa-lib \
        atk \
        gtk3 \
        libdrm \
        libxkbcommon \
        libatspi \
        libXss \
    && dnf clean all

# Copy requirements and install Python dependencies
COPY backend/requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (optimized for Lambda)
RUN playwright install chromium --with-deps

# Copy application code
COPY backend/ ${LAMBDA_TASK_ROOT}/

# Create temporary directory for audio processing
RUN mkdir -p /tmp/audifyy && \
    chmod 755 /tmp/audifyy

# Set the Lambda handler
CMD ["app.main.lambda_handler"]