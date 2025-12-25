# Staging environment configuration
aws_region  = "ap-southeast-2"
environment = "staging"

# Domain configuration (configure with your staging domain)
domain_name     = ""  # e.g., "staging.audifyy.com"
api_domain_name = ""  # e.g., "api-staging.audifyy.com"
certificate_arn = ""  # ACM certificate ARN for staging domain

# Lambda configuration for staging
lambda_timeout = 900  # 15 minutes (max for Lambda)
lambda_memory  = 2048 # 2GB memory for staging workloads

# GitHub configuration
github_repo_url = "https://github.com/Ajeesh24/audiify-core"
github_branch   = "staging"

# CORS configuration (restrict to staging domain)
cors_origins = [
  "https://staging.audifyy.com",
  "https://*.audifyy.com"
]

# Logging enabled for staging
enable_cloudfront_logs = true

# OpenAI API Key (will be provided via GitHub Secrets or CLI)
# openai_api_key = "sk-..." # Don't put actual keys in files!