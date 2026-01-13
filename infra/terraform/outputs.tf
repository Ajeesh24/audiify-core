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

output "ecr_repository_url" {
  description = "ECR repository URL for Lambda container images"
  value       = data.aws_ecr_repository.lambda_backend.repository_url
}

output "backend_api_url" {
  description = "Backend API URL (alias for api_gateway_url)"
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

# News Agency outputs
output "news_public_api_url" {
  description = "News Agency Public API URL"
  value       = "https://${aws_api_gateway_rest_api.news_public_api.id}.execute-api.${var.aws_region}.amazonaws.com/${var.environment}"
}

output "news_audio_bucket_name" {
  description = "Name of the S3 bucket for news audio files"
  value       = aws_s3_bucket.news_audio_files.bucket
}

output "news_dynamodb_tables" {
  description = "News Agency DynamoDB table names"
  value = {
    articles = aws_dynamodb_table.articles.name
    briefs   = aws_dynamodb_table.briefs.name
    jobs     = aws_dynamodb_table.news_jobs.name
  }
}

output "news_lambda_functions" {
  description = "News Agency Lambda function names"
  value = {
    rss_engine            = aws_lambda_function.news_rss_engine.function_name
    categorization_engine = aws_lambda_function.news_categorization_engine.function_name
    ranking_engine        = aws_lambda_function.news_ranking_engine.function_name
    brief_engine          = aws_lambda_function.news_brief_engine.function_name
    audio_engine          = aws_lambda_function.news_audio_engine.function_name
    orchestrator          = aws_lambda_function.news_orchestrator.function_name
    public_api            = aws_lambda_function.news_public_api.function_name
    internal_api          = aws_lambda_function.news_internal_api.function_name
  }
}

output "news_ecr_repositories" {
  description = "News Agency ECR repository URLs"
  value = {
    rss_engine            = aws_ecr_repository.news_rss_engine.repository_url
    categorization_engine = aws_ecr_repository.news_categorization_engine.repository_url
    ranking_engine        = aws_ecr_repository.news_ranking_engine.repository_url
    brief_engine          = aws_ecr_repository.news_brief_engine.repository_url
    audio_engine          = aws_ecr_repository.news_audio_engine.repository_url
    orchestrator          = aws_ecr_repository.news_orchestrator.repository_url
    public_api            = aws_ecr_repository.news_public_api.repository_url
    internal_api          = aws_ecr_repository.news_internal_api.repository_url
  }
}

# Summary output for easy reference
output "deployment_summary" {
  description = "Summary of deployed resources"
  value = {
    frontend_url    = var.domain_name != "" ? "https://${var.domain_name}" : "https://${aws_cloudfront_distribution.frontend.domain_name}"
    backend_api_url = "https://${aws_api_gateway_rest_api.backend_api.id}.execute-api.${var.aws_region}.amazonaws.com/${var.environment}"
    news_api_url    = "https://${aws_api_gateway_rest_api.news_public_api.id}.execute-api.${var.aws_region}.amazonaws.com/${var.environment}"
    environment     = var.environment
    region          = data.aws_region.current.name
    cognito = {
      user_pool_id     = aws_cognito_user_pool.main.id
      client_id        = aws_cognito_user_pool_client.main.id
      identity_pool_id = aws_cognito_identity_pool.main.id
      region           = data.aws_region.current.name
    }
    news_agency = {
      audio_bucket      = aws_s3_bucket.news_audio_files.bucket
      public_api        = "https://${aws_api_gateway_rest_api.news_public_api.id}.execute-api.${var.aws_region}.amazonaws.com/${var.environment}"
      pipeline_schedule = aws_cloudwatch_event_rule.daily_news_pipeline.schedule_expression
    }
  }
}