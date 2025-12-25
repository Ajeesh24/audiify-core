variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "ap-southeast-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "domain_name" {
  description = "Domain name for the frontend application (optional)"
  type        = string
  default     = ""
}

variable "api_domain_name" {
  description = "Domain name for the API Gateway (optional)"
  type        = string
  default     = ""
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS (optional)"
  type        = string
  default     = ""
}

variable "openai_api_key" {
  description = "OpenAI API key for TTS and LLM services"
  type        = string
  sensitive   = true
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds (max 900)"
  type        = number
  default     = 900
}

variable "lambda_memory" {
  description = "Lambda function memory in MB"
  type        = number
  default     = 2048
}

variable "github_repo_url" {
  description = "GitHub repository URL for source code connection"
  type        = string
  default     = "https://github.com/Ajeesh24/audiify-core"
}

variable "github_branch" {
  description = "GitHub branch to deploy from"
  type        = string
  default     = "main"
}

variable "enable_cloudfront_logs" {
  description = "Enable CloudFront access logs"
  type        = bool
  default     = false
}

variable "cors_origins" {
  description = "CORS allowed origins for the API"
  type        = list(string)
  default     = ["*"]
}