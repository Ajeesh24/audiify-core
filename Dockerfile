# Lambda-optimized Dockerfile with Function URL Streaming Support
FROM public.ecr.aws/lambda/python:3.11

# Add Lambda Web Adapter for Function URL streaming
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.8.4 /lambda-adapter /opt/extensions/lambda-adapter

# Set environment variables for Lambda Web Adapter
ENV PYTHONPATH=/var/task
ENV AWS_LAMBDA_FUNCTION_NAME=audifyy-backend
ENV AWS_LWA_ENABLE_COMPRESSION=true
ENV AWS_LWA_INVOKE_MODE=response_stream
ENV PORT=8080

# Install UV first for much faster Python package management
RUN pip install --no-cache-dir uv

# Install system dependencies required for our application
RUN yum update -y && \
    yum install -y \
        gcc \
        gcc-c++ \
        make \
        curl \
    && yum clean all

# Install Rust (required for tiktoken compilation)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy requirements and install Python dependencies with UV (much faster than pip)
COPY backend/requirements.txt ${LAMBDA_TASK_ROOT}/

# Install Python dependencies with UV for 10x faster builds
RUN uv pip install --system --no-cache -r requirements.txt

# Copy application code
COPY backend/ ${LAMBDA_TASK_ROOT}/

# Create temporary directory for audio processing
RUN mkdir -p /tmp/audifyy && \
    chmod 755 /tmp/audifyy

# Start uvicorn server for Lambda Web Adapter (Function URL streaming)
# Lambda Web Adapter will detect environment and start the server
CMD ["python", "app/main.py"]