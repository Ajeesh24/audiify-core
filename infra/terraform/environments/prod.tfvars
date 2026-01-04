# Production environment configuration
aws_region  = "ap-southeast-2"
environment = "prod"

# Docker image version (semantic versioning)
image_tag = "0.0.1"

# Domain configuration (configure with your production domain)
domain_name     = ""  # e.g., "audifyy.com"
api_domain_name = ""  # e.g., "api.audifyy.com"
certificate_arn = ""  # ACM certificate ARN for production domain

# Lambda configuration for production
lambda_timeout = 900  # 15 minutes (max for Lambda)
lambda_memory  = 3008 # 3GB memory for production workloads

# GitHub configuration
github_repo_url = "https://github.com/Ajeesh24/audiify-core"
github_branch   = "main"

# CORS configuration (restrict to production domain)
cors_origins = [
  "https://audifyy.com",
  "https://www.audifyy.com"
]

# Logging enabled for production
enable_cloudfront_logs = true

# OpenAI API Key (will be provided via GitHub Secrets or CLI)
# openai_api_key = "sk-..." # Don't put actual keys in files!