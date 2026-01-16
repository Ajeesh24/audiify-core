# Lambda execution role
resource "aws_iam_role" "lambda_execution_role" {
  name = "${local.project_name}-lambda-execution-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# Lambda execution policy
resource "aws_iam_role_policy" "lambda_execution_policy" {
  name = "${local.project_name}-lambda-execution-policy-${var.environment}"
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.audio_storage.arn}/*",
          "${aws_s3_bucket.news_audio_files.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.audio_storage.arn,
          aws_s3_bucket.news_audio_files.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = [
          aws_ssm_parameter.openai_api_key.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:SendMessage"
        ]
        Resource = [
          aws_sqs_queue.job_queue.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.job_status.arn,
          "${aws_dynamodb_table.job_status.arn}/*",
          aws_dynamodb_table.briefs.arn,
          "${aws_dynamodb_table.briefs.arn}/*"
        ]
      }
    ]
  })
}

# Attach basic Lambda execution role
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_execution_role.name
}

# S3 bucket for audio file storage
resource "aws_s3_bucket" "audio_storage" {
  bucket = "${local.project_name}-audio-${var.environment}-${random_string.suffix.result}"
  tags   = local.common_tags
}

resource "aws_s3_bucket_public_access_block" "audio_storage" {
  bucket = aws_s3_bucket.audio_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CORS configuration for audio storage to allow frontend access
resource "aws_s3_bucket_cors_configuration" "audio_storage" {
  bucket = aws_s3_bucket.audio_storage.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = [
      "http://localhost:5173",                                       # Local development
      "https://${aws_cloudfront_distribution.frontend.domain_name}", # CloudFront distribution
      var.domain_name != "" ? "https://${var.domain_name}" : ""      # Custom domain if configured
    ]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "audio_storage" {
  bucket = aws_s3_bucket.audio_storage.id

  rule {
    id     = "delete_old_audio"
    status = "Enabled"

    filter {} # Apply to all objects in the bucket

    expiration {
      days = 7 # Delete audio files after 7 days
    }

    noncurrent_version_expiration {
      noncurrent_days = 1
    }
  }
}

# Reference existing ECR repository (managed by GitHub workflow)
data "aws_ecr_repository" "lambda_backend" {
  name = "audifyy-lambda-backend"
}

# Lambda function
resource "aws_lambda_function" "backend" {
  function_name = "${local.project_name}-backend-${var.environment}"
  role          = aws_iam_role.lambda_execution_role.arn
  package_type  = "Image"

  # Image URI with semantic version tag
  image_uri = "${data.aws_ecr_repository.lambda_backend.repository_url}:${var.image_tag}"

  timeout     = 900  # 15 minutes (maximum for Lambda)
  memory_size = 2048 # 2GB (sufficient for our processing)

  environment {
    variables = {
      ENVIRONMENT              = var.environment
      CORS_ORIGINS             = jsonencode(var.cors_origins)
      AUDIO_BUCKET_NAME        = aws_s3_bucket.audio_storage.bucket
      AUDIO_BUCKET             = aws_s3_bucket.news_audio_files.bucket
      BRIEFS_TABLE             = aws_dynamodb_table.briefs.name
      TEMP_DIR                 = "/tmp"
      OPENAI_API_KEY_PARAMETER = aws_ssm_parameter.openai_api_key.name
      SQS_QUEUE_URL            = aws_sqs_queue.job_queue.url
      DYNAMODB_TABLE_NAME      = aws_dynamodb_table.job_status.name
      COGNITO_USER_POOL_ID     = aws_cognito_user_pool.main.id
      COGNITO_CLIENT_ID        = aws_cognito_user_pool_client.main.id
      COGNITO_REGION           = data.aws_region.current.name
      # Logging configuration
      LOG_LEVEL        = "INFO"
      PYTHONUNBUFFERED = "1"
    }
  }

  # Large /tmp directory for audio files
  ephemeral_storage {
    size = 10240 # 10GB
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_cloudwatch_log_group.lambda_logs
  ]

  tags = local.common_tags
}

# SQS Event Source Mapping for Lambda
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.job_queue.arn
  function_name    = aws_lambda_function.backend.arn
  batch_size       = 1
  enabled          = true

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_iam_role_policy.lambda_execution_policy,
  ]
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${local.project_name}-backend-${var.environment}"
  retention_in_days = 14
  tags              = local.common_tags
}

# API Gateway REST API
resource "aws_api_gateway_rest_api" "backend_api" {
  name        = "${local.project_name}-api-${var.environment}"
  description = "Audifyy Backend API Gateway"

  binary_media_types = [
    "audio/*",
    "application/octet-stream",
    "*/*"
  ]

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = local.common_tags
}

# API Gateway Resource (proxy for all paths)
resource "aws_api_gateway_resource" "proxy" {
  rest_api_id = aws_api_gateway_rest_api.backend_api.id
  parent_id   = aws_api_gateway_rest_api.backend_api.root_resource_id
  path_part   = "{proxy+}"
}

# API Gateway Method (ANY for all HTTP methods)
resource "aws_api_gateway_method" "proxy_method" {
  rest_api_id   = aws_api_gateway_rest_api.backend_api.id
  resource_id   = aws_api_gateway_resource.proxy.id
  http_method   = "ANY"
  authorization = "NONE"
}

# API Gateway Integration with Lambda
resource "aws_api_gateway_integration" "lambda_integration" {
  rest_api_id = aws_api_gateway_rest_api.backend_api.id
  resource_id = aws_api_gateway_method.proxy_method.resource_id
  http_method = aws_api_gateway_method.proxy_method.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.backend.invoke_arn
}

# API Gateway Method for root path
resource "aws_api_gateway_method" "proxy_root" {
  rest_api_id   = aws_api_gateway_rest_api.backend_api.id
  resource_id   = aws_api_gateway_rest_api.backend_api.root_resource_id
  http_method   = "ANY"
  authorization = "NONE"
}

# API Gateway Integration for root path
resource "aws_api_gateway_integration" "lambda_root" {
  rest_api_id = aws_api_gateway_rest_api.backend_api.id
  resource_id = aws_api_gateway_method.proxy_root.resource_id
  http_method = aws_api_gateway_method.proxy_root.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.backend.invoke_arn
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "backend_deployment" {
  depends_on = [
    aws_api_gateway_integration.lambda_integration,
    aws_api_gateway_integration.lambda_root,
  ]

  rest_api_id = aws_api_gateway_rest_api.backend_api.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.proxy.id,
      aws_api_gateway_method.proxy_method.id,
      aws_api_gateway_integration.lambda_integration.id,
      aws_api_gateway_method.proxy_root.id,
      aws_api_gateway_integration.lambda_root.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

# API Gateway Stage
resource "aws_api_gateway_stage" "backend_stage" {
  deployment_id = aws_api_gateway_deployment.backend_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.backend_api.id
  stage_name    = var.environment

  # Enable access logging with proper CloudWatch role
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway_logs.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      resourcePath   = "$context.resourcePath"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
    })
  }

  # Enable X-Ray tracing
  xray_tracing_enabled = true

  # Ensure the account-wide role is configured first
  depends_on = [aws_api_gateway_account.main]

  tags = local.common_tags
}

# IAM role for API Gateway CloudWatch logging
resource "aws_iam_role" "api_gateway_cloudwatch_role" {
  name = "${local.project_name}-api-gateway-cloudwatch-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# Attach policy for CloudWatch logging
resource "aws_iam_role_policy_attachment" "api_gateway_cloudwatch_logs" {
  role       = aws_iam_role.api_gateway_cloudwatch_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

# Configure API Gateway account-wide CloudWatch role
resource "aws_api_gateway_account" "main" {
  cloudwatch_role_arn = aws_iam_role.api_gateway_cloudwatch_role.arn
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_gateway_logs" {
  name              = "/aws/apigateway/${local.project_name}-${var.environment}"
  retention_in_days = 14
  tags              = local.common_tags
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.backend.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_api_gateway_rest_api.backend_api.execution_arn}/*/*"
}

# Custom domain (optional)
resource "aws_api_gateway_domain_name" "backend_domain" {
  count           = var.api_domain_name != "" ? 1 : 0
  domain_name     = var.api_domain_name
  certificate_arn = var.certificate_arn

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = local.common_tags
}

# Domain mapping (optional)
resource "aws_api_gateway_base_path_mapping" "backend_domain_mapping" {
  count       = var.api_domain_name != "" ? 1 : 0
  api_id      = aws_api_gateway_rest_api.backend_api.id
  stage_name  = aws_api_gateway_stage.backend_stage.stage_name
  domain_name = aws_api_gateway_domain_name.backend_domain[0].domain_name
}

# SSM Parameter for OpenAI API Key
resource "aws_ssm_parameter" "openai_api_key" {
  name  = "/${local.project_name}/${var.environment}/openai-api-key"
  type  = "SecureString"
  value = var.openai_api_key

  tags = local.common_tags
}

# SQS Queue for background job processing
resource "aws_sqs_queue" "job_queue" {
  name                       = "${local.project_name}-job-queue-${var.environment}"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 1209600 # 14 days
  receive_wait_time_seconds  = 0
  visibility_timeout_seconds = 900 # 15 minutes (Lambda max timeout)

  tags = local.common_tags
}

# Cognito User Pool
resource "aws_cognito_user_pool" "main" {
  name = "${local.project_name}-users-${var.environment}"

  # User attributes - users sign up directly with email as username
  auto_verified_attributes = ["email"]
  username_attributes      = ["email"] # Users can sign in with email

  # Password policy
  password_policy {
    minimum_length                   = 8
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Email configuration
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # User verification
  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_message        = "Your Audifyy verification code is {####}"
    email_subject        = "Verify your Audifyy account"
  }

  # User pool add-ons
  user_pool_add_ons {
    advanced_security_mode = "ENFORCED"
  }

  tags = local.common_tags
}

# Google Identity Provider (only if credentials provided)
resource "aws_cognito_identity_provider" "google" {
  count         = var.google_client_id != "" && var.google_client_secret != "" ? 1 : 0
  user_pool_id  = aws_cognito_user_pool.main.id
  provider_name = "Google"
  provider_type = "Google"

  provider_details = {
    authorize_scopes = "email openid profile"
    client_id        = var.google_client_id
    client_secret    = var.google_client_secret
  }

  attribute_mapping = {
    email    = "email"
    name     = "name"
    username = "sub"
  }
}

# Apple Identity Provider (only if credentials provided)
resource "aws_cognito_identity_provider" "apple" {
  count         = var.apple_client_id != "" && var.apple_team_id != "" && var.apple_key_id != "" && var.apple_private_key != "" ? 1 : 0
  user_pool_id  = aws_cognito_user_pool.main.id
  provider_name = "SignInWithApple"
  provider_type = "SignInWithApple"

  provider_details = {
    authorize_scopes = "email name"
    client_id        = var.apple_client_id
    team_id          = var.apple_team_id
    key_id           = var.apple_key_id
    private_key      = var.apple_private_key
  }

  attribute_mapping = {
    email    = "email"
    name     = "name"
    username = "sub"
  }
}

# Helper locals for dynamic identity providers
locals {
  identity_providers = concat(
    ["COGNITO"],
    var.google_client_id != "" && var.google_client_secret != "" ? ["Google"] : [],
    var.apple_client_id != "" && var.apple_team_id != "" && var.apple_key_id != "" && var.apple_private_key != "" ? ["SignInWithApple"] : []
  )
}

# Cognito User Pool Client
resource "aws_cognito_user_pool_client" "main" {
  name         = "${local.project_name}-client-${var.environment}"
  user_pool_id = aws_cognito_user_pool.main.id

  # Authentication flows (use newer ALLOW_ prefixed format)
  explicit_auth_flows = [
    "ALLOW_ADMIN_USER_PASSWORD_AUTH",
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]

  # Token validity (in minutes by default)
  access_token_validity  = 60 # 1 hour
  refresh_token_validity = 30 # 30 days
  id_token_validity      = 60 # 1 hour

  # Specify the units explicitly
  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }

  # Prevent user existence errors
  prevent_user_existence_errors = "ENABLED"

  # No client secret for public frontend clients
  generate_secret = false
}

# Cognito Identity Pool
resource "aws_cognito_identity_pool" "main" {
  identity_pool_name               = "${local.project_name}_identity_pool_${var.environment}"
  allow_unauthenticated_identities = false

  cognito_identity_providers {
    client_id               = aws_cognito_user_pool_client.main.id
    provider_name           = aws_cognito_user_pool.main.endpoint
    server_side_token_check = false
  }

  tags = local.common_tags
}

# IAM role for authenticated users
resource "aws_iam_role" "authenticated" {
  name = "${local.project_name}-cognito-authenticated-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "cognito-identity.amazonaws.com"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "cognito-identity.amazonaws.com:aud" = aws_cognito_identity_pool.main.id
          }
          "ForAnyValue:StringLike" = {
            "cognito-identity.amazonaws.com:amr" = "authenticated"
          }
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM policy for authenticated users (minimal S3 access to their own files)
resource "aws_iam_role_policy" "authenticated" {
  name = "${local.project_name}-cognito-authenticated-policy-${var.environment}"
  role = aws_iam_role.authenticated.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = [
          "${aws_s3_bucket.audio_storage.arn}/audio/user-$${cognito-identity.amazonaws.com:sub}/*"
        ]
      }
    ]
  })
}

# Cognito Identity Pool Role Attachment
resource "aws_cognito_identity_pool_roles_attachment" "main" {
  identity_pool_id = aws_cognito_identity_pool.main.id

  roles = {
    "authenticated" = aws_iam_role.authenticated.arn
  }
}

# DynamoDB table for job status storage (updated with user_id)
resource "aws_dynamodb_table" "job_status" {
  name         = "${local.project_name}-jobs-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "job_id"

  attribute {
    name = "job_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  # Global secondary index for querying by status
  global_secondary_index {
    name            = "status-created-index"
    hash_key        = "status"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  # Global secondary index for user-specific queries
  global_secondary_index {
    name            = "user-created-index"
    hash_key        = "user_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  # TTL for automatic cleanup of old jobs
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = local.common_tags
}