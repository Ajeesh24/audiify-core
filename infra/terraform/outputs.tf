# Frontend outputs
output "frontend_bucket_name" {
  description = "Name of the S3 bucket hosting the frontend"
  value       = aws_s3_bucket.frontend.bucket
}

output "frontend_bucket_domain" {
  description = "Domain name of the S3 bucket"
  value       = aws_s3_bucket.frontend.bucket_domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.frontend.id
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "frontend_url" {
  description = "Frontend application URL"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

# Backend outputs
output "api_gateway_url" {
  description = "API Gateway URL"
  value       = "https://${aws_api_gateway_rest_api.backend_api.id}.execute-api.${var.aws_region}.amazonaws.com/${var.environment}"
}

output "api_gateway_id" {
  description = "API Gateway REST API ID"
  value       = aws_api_gateway_rest_api.backend_api.id
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.backend.function_name
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.backend.arn
}

# NEW: Function URL for streaming endpoints
output "lambda_function_url" {
  description = "Lambda Function URL for streaming endpoints"
  value       = aws_lambda_function_url.streaming_endpoint.function_url
}

output "ecr_repository_url" {
  description = "ECR repository URL for Lambda container images"
  value       = data.aws_ecr_repository.lambda_backend.repository_url
}

output "backend_api_url" {
  description = "Backend API URL (alias_gateway_url)"
  value       = "https://${aws_api_gateway_rest_api.backend_api.id}.execute-api.${var.aws_region}.amazonaws.com/${var.environment}"
}

# Storage outputs
output "audio_bucket_name" {
  description = "Name of the S3 bucket for audio storage"
  value       = aws_s3_bucket.audio_storage.bucket
}

output "audio_bucket_arn" {
  description = "ARN of the S3 bucket for audio storage"
  value       = aws_s3_bucket.audio_storage.arn
}

# IAM outputs
output "lambda_execution_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_execution_role.arn
}

# Environment information
output "aws_region" {
  description = "AWS region"
  value       = data.aws_region.current.name
}

output "aws_account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

# Logs bucket (if enabled)
output "logs_bucket_name" {
  description = "Name of the S3 bucket for CloudFront logs"
  value       = var.enable_cloudfront_logs ? aws_s3_bucket.logs[0].bucket : null
}

# Authentication outputs
output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = aws_cognito_user_pool.main.id
}

output "cognito_client_id" {
  description = "Cognito User Pool Client ID"
  value       = aws_cognito_user_pool_client.main.id
}

output "cognito_identity_pool_id" {
  description = "Cognito Identity Pool ID"
  value       = aws_cognito_identity_pool.main.id
}

output "cognito_region" {
  description = "AWS region for Cognito"
  value       = data.aws_region.current.name
}

# Summary output for easy reference
output "deployment_summary" {
  description = "Summary of deployed resources"
  value = {
    frontend_url       = var.domain_name != "" ? "https://${var.domain_name}" : "https://${aws_cloudfront_distribution.frontend.domain_name}"
    backend_api_url    = "https://${aws_api_gateway_rest_api.backend_api.id}.execute-api.${var.aws_region}.amazonaws.com/${var.environment}"
    streaming_api_url  = aws_lambda_function_url.streaming_endpoint.function_url  # NEW!
    environment        = var.environment
    region             = data.aws_region.current.name
    cognito = {
      user_pool_id     = aws_cognito_user_pool.main.id
      client_id        = aws_cognito_user_pool_client.main.id
      identity_pool_id = aws_cognito_identity_pool.main.id
      region           = data.aws_region.current.name
    }
  }
}