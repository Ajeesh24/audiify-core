# Development environment configuration
aws_region  = "ap-southeast-2"
environment = "dev"

# Domain configuration (leave empty for default domains)
domain_name     = ""  # CloudFront default domain
api_domain_name = ""  # API Gateway default domain
certificate_arn = ""

# Lambda configuration for dev
lambda_timeout = 900  # 15 minutes (max for Lambda)
lambda_memory  = 2048 # 2GB memory

# GitHub configuration
github_repo_url = "https://github.com/Ajeesh24/audiify-core"
github_branch   = "main"

# CORS configuration (allow all origins in dev)
cors_origins = ["*"]

# Logging (disabled in dev to save costs)
enable_cloudfront_logs = false

# OpenAI API Key (will be provided via GitHub Secrets or CLI)
# openai_api_key = "sk-..." # Don't put actual keys in files!