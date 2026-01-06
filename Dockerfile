# Lambda-optimized Dockerfile for Audifyy Backend with UV for faster builds
FROM public.ecr.aws/lambda/python:3.11

# Set environment variables for Lambda
ENV PYTHONPATH=/var/task
ENV AWS_LAMBDA_FUNCTION_NAME=audifyy-backend

# Install UV first for much faster Python package management
RUN pip install --no-cache-dir uv

# Install system dependencies required for our application
RUN yum update -y && \
    yum install -y \
        gcc \
        gcc-c++ \
        make \
        nss \
        libXrandr \
        libXcomposite \
        libXcursor \
        libXdamage \
        libXext \
        libXi \
        libXtst \
        cups-libs \
        libXScrnSaver \
        GConf2 \
        alsa-lib \
        atk \
        gtk3 \
        libdrm \
        libxkbcommon \
        at-spi2-atk \
        libXss \
        curl \
    && yum clean all

# Install Rust (required for tiktoken compilation)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy requirements and install Python dependencies with UV (much faster than pip)
COPY backend/requirements.txt ${LAMBDA_TASK_ROOT}/

# Install Python dependencies with UV for 10x faster builds
RUN uv pip install --system --no-cache -r requirements.txt

# Set Playwright environment variables for runtime browser installation
ENV PLAYWRIGHT_BROWSERS_PATH=/tmp/playwright
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0

# Copy application code
COPY backend/ ${LAMBDA_TASK_ROOT}/

# Create temporary directories for audio processing and Playwright browsers
RUN mkdir -p /tmp/audifyy /tmp/playwright && \
    chmod 755 /tmp/audifyy /tmp/playwright

# Set the Lambda handler
CMD ["app.main.lambda_handler"]