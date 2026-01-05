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
          "${aws_s3_bucket.audio_storage.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.audio_storage.arn
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
      AWS_DEFAULT_REGION       = var.aws_region
      CORS_ORIGINS             = jsonencode(var.cors_origins)
      AUDIO_BUCKET_NAME        = aws_s3_bucket.audio_storage.bucket
      TEMP_DIR                 = "/tmp"
      OPENAI_API_KEY_PARAMETER = aws_ssm_parameter.openai_api_key.name
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

  # Enable access logging
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

  tags = local.common_tags
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