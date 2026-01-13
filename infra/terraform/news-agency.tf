# News Agency Infrastructure
# DynamoDB tables, Lambda functions, S3 buckets, and EventBridge rules

# ===============================
# DynamoDB Tables for News Agency
# ===============================

# Articles table for storing raw and processed articles
resource "aws_dynamodb_table" "articles" {
  name           = "${local.project_name}-articles-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "article_id"
  range_key      = "date"

  attribute {
    name = "article_id"
    type = "S"
  }

  attribute {
    name = "date"
    type = "S"
  }

  attribute {
    name = "category"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name     = "DateCategoryIndex"
    hash_key = "date"
    range_key = "category"
  }

  global_secondary_index {
    name     = "StatusIndex"
    hash_key = "status"
    range_key = "date"
  }

  tags = local.common_tags
}

# Briefs table for storing generated daily briefs
resource "aws_dynamodb_table" "briefs" {
  name           = "${local.project_name}-briefs-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "brief_id"
  range_key      = "date"

  attribute {
    name = "brief_id"
    type = "S"
  }

  attribute {
    name = "date"
    type = "S"
  }

  attribute {
    name = "category"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name     = "DateCategoryIndex"
    hash_key = "date"
    range_key = "category"
  }

  global_secondary_index {
    name     = "StatusIndex"
    hash_key = "status"
    range_key = "date"
  }

  tags = local.common_tags
}

# Jobs table for pipeline orchestration and job tracking
resource "aws_dynamodb_table" "jobs" {
  name           = "${local.project_name}-jobs-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "job_id"
  range_key      = "timestamp"

  attribute {
    name = "job_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "job_type"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name     = "JobTypeIndex"
    hash_key = "job_type"
    range_key = "timestamp"
  }

  global_secondary_index {
    name     = "StatusIndex"
    hash_key = "status"
    range_key = "timestamp"
  }

  tags = local.common_tags
}

# ===============================
# S3 Bucket for Audio Files
# ===============================

resource "aws_s3_bucket" "audio_files" {
  bucket = "${local.project_name}-audio-${var.environment}-${random_string.suffix.result}"
  tags   = local.common_tags
}

resource "aws_s3_bucket_versioning" "audio_files_versioning" {
  bucket = aws_s3_bucket.audio_files.id
  versioning_configuration {
    status = "Disabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audio_files_encryption" {
  bucket = aws_s3_bucket.audio_files.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "audio_files_pab" {
  bucket = aws_s3_bucket.audio_files.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "audio_files_policy" {
  depends_on = [aws_s3_bucket_public_access_block.audio_files_pab]
  bucket     = aws_s3_bucket.audio_files.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowPublicRead"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.audio_files.arn}/*"
      }
    ]
  })
}

# ===============================
# ECR Repositories for Lambda Images
# ===============================

resource "aws_ecr_repository" "news_rss_engine" {
  name         = "${local.project_name}/news-rss-engine"
  force_delete = true

  image_scanning_configuration {
    scan_on_push = false
  }

  tags = local.common_tags
}

resource "aws_ecr_repository" "news_categorization_engine" {
  name         = "${local.project_name}/news-categorization-engine"
  force_delete = true

  image_scanning_configuration {
    scan_on_push = false
  }

  tags = local.common_tags
}

resource "aws_ecr_repository" "news_ranking_engine" {
  name         = "${local.project_name}/news-ranking-engine"
  force_delete = true

  image_scanning_configuration {
    scan_on_push = false
  }

  tags = local.common_tags
}

resource "aws_ecr_repository" "news_brief_engine" {
  name         = "${local.project_name}/news-brief-engine"
  force_delete = true

  image_scanning_configuration {
    scan_on_push = false
  }

  tags = local.common_tags
}

resource "aws_ecr_repository" "news_audio_engine" {
  name         = "${local.project_name}/news-audio-engine"
  force_delete = true

  image_scanning_configuration {
    scan_on_push = false
  }

  tags = local.common_tags
}

resource "aws_ecr_repository" "news_orchestrator" {
  name         = "${local.project_name}/news-orchestrator"
  force_delete = true

  image_scanning_configuration {
    scan_on_push = false
  }

  tags = local.common_tags
}

resource "aws_ecr_repository" "news_public_api" {
  name         = "${local.project_name}/news-public-api"
  force_delete = true

  image_scanning_configuration {
    scan_on_push = false
  }

  tags = local.common_tags
}

resource "aws_ecr_repository" "news_internal_api" {
  name         = "${local.project_name}/news-internal-api"
  force_delete = true

  image_scanning_configuration {
    scan_on_push = false
  }

  tags = local.common_tags
}

# ===============================
# IAM Role for Lambda Functions
# ===============================

resource "aws_iam_role" "news_lambda_role" {
  name = "${local.project_name}-news-lambda-role-${var.environment}"

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

resource "aws_iam_role_policy" "news_lambda_policy" {
  name = "${local.project_name}-news-lambda-policy-${var.environment}"
  role = aws_iam_role.news_lambda_role.id

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
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem"
        ]
        Resource = [
          aws_dynamodb_table.articles.arn,
          "${aws_dynamodb_table.articles.arn}/index/*",
          aws_dynamodb_table.briefs.arn,
          "${aws_dynamodb_table.briefs.arn}/index/*",
          aws_dynamodb_table.jobs.arn,
          "${aws_dynamodb_table.jobs.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.audio_files.arn,
          "${aws_s3_bucket.audio_files.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:${local.project_name}-news-*"
      }
    ]
  })
}

# ===============================
# Lambda Functions for News Agency
# ===============================

# RSS Collection Engine
resource "aws_lambda_function" "news_rss_engine" {
  function_name = "${local.project_name}-news-rss-engine-${var.environment}"
  role          = aws_iam_role.news_lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.news_rss_engine.repository_url}:${var.image_tag}"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory

  environment {
    variables = {
      ENVIRONMENT = var.environment
      ARTICLES_TABLE = aws_dynamodb_table.articles.name
      JOBS_TABLE = aws_dynamodb_table.jobs.name
      OPENAI_API_KEY = var.openai_api_key
      AUDIO_BUCKET = aws_s3_bucket.audio_files.bucket
    }
  }

  tags = local.common_tags

  depends_on = [aws_iam_role_policy.news_lambda_policy]
}

# Categorization Engine
resource "aws_lambda_function" "news_categorization_engine" {
  function_name = "${local.project_name}-news-categorization-engine-${var.environment}"
  role          = aws_iam_role.news_lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.news_categorization_engine.repository_url}:${var.image_tag}"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory

  environment {
    variables = {
      ENVIRONMENT = var.environment
      ARTICLES_TABLE = aws_dynamodb_table.articles.name
      JOBS_TABLE = aws_dynamodb_table.jobs.name
      OPENAI_API_KEY = var.openai_api_key
      AUDIO_BUCKET = aws_s3_bucket.audio_files.bucket
    }
  }

  tags = local.common_tags

  depends_on = [aws_iam_role_policy.news_lambda_policy]
}

# Ranking Engine
resource "aws_lambda_function" "news_ranking_engine" {
  function_name = "${local.project_name}-news-ranking-engine-${var.environment}"
  role          = aws_iam_role.news_lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.news_ranking_engine.repository_url}:${var.image_tag}"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory

  environment {
    variables = {
      ENVIRONMENT = var.environment
      ARTICLES_TABLE = aws_dynamodb_table.articles.name
      JOBS_TABLE = aws_dynamodb_table.jobs.name
      OPENAI_API_KEY = var.openai_api_key
      AUDIO_BUCKET = aws_s3_bucket.audio_files.bucket
    }
  }

  tags = local.common_tags

  depends_on = [aws_iam_role_policy.news_lambda_policy]
}

# Brief Generation Engine
resource "aws_lambda_function" "news_brief_engine" {
  function_name = "${local.project_name}-news-brief-engine-${var.environment}"
  role          = aws_iam_role.news_lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.news_brief_engine.repository_url}:${var.image_tag}"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory

  environment {
    variables = {
      ENVIRONMENT = var.environment
      ARTICLES_TABLE = aws_dynamodb_table.articles.name
      BRIEFS_TABLE = aws_dynamodb_table.briefs.name
      JOBS_TABLE = aws_dynamodb_table.jobs.name
      OPENAI_API_KEY = var.openai_api_key
      ELEVENLABS_API_KEY = var.elevenlabs_api_key
      AUDIO_BUCKET = aws_s3_bucket.audio_files.bucket
    }
  }

  tags = local.common_tags

  depends_on = [aws_iam_role_policy.news_lambda_policy]
}

# Audio Generation Engine
resource "aws_lambda_function" "news_audio_engine" {
  function_name = "${local.project_name}-news-audio-engine-${var.environment}"
  role          = aws_iam_role.news_lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.news_audio_engine.repository_url}:${var.image_tag}"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory

  environment {
    variables = {
      ENVIRONMENT = var.environment
      ARTICLES_TABLE = aws_dynamodb_table.articles.name
      BRIEFS_TABLE = aws_dynamodb_table.briefs.name
      JOBS_TABLE = aws_dynamodb_table.jobs.name
      OPENAI_API_KEY = var.openai_api_key
      ELEVENLABS_API_KEY = var.elevenlabs_api_key
      AUDIO_BUCKET = aws_s3_bucket.audio_files.bucket
    }
  }

  tags = local.common_tags

  depends_on = [aws_iam_role_policy.news_lambda_policy]
}

# Pipeline Orchestrator
resource "aws_lambda_function" "news_orchestrator" {
  function_name = "${local.project_name}-news-orchestrator-${var.environment}"
  role          = aws_iam_role.news_lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.news_orchestrator.repository_url}:${var.image_tag}"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory

  environment {
    variables = {
      ENVIRONMENT = var.environment
      ARTICLES_TABLE = aws_dynamodb_table.articles.name
      BRIEFS_TABLE = aws_dynamodb_table.briefs.name
      JOBS_TABLE = aws_dynamodb_table.jobs.name
      OPENAI_API_KEY = var.openai_api_key
      ELEVENLABS_API_KEY = var.elevenlabs_api_key
      AUDIO_BUCKET = aws_s3_bucket.audio_files.bucket
      RSS_ENGINE_FUNCTION = aws_lambda_function.news_rss_engine.function_name
      CATEGORIZATION_ENGINE_FUNCTION = aws_lambda_function.news_categorization_engine.function_name
      RANKING_ENGINE_FUNCTION = aws_lambda_function.news_ranking_engine.function_name
      BRIEF_ENGINE_FUNCTION = aws_lambda_function.news_brief_engine.function_name
      AUDIO_ENGINE_FUNCTION = aws_lambda_function.news_audio_engine.function_name
    }
  }

  tags = local.common_tags

  depends_on = [aws_iam_role_policy.news_lambda_policy]
}

# Public API
resource "aws_lambda_function" "news_public_api" {
  function_name = "${local.project_name}-news-public-api-${var.environment}"
  role          = aws_iam_role.news_lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.news_public_api.repository_url}:${var.image_tag}"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory

  environment {
    variables = {
      ENVIRONMENT = var.environment
      ARTICLES_TABLE = aws_dynamodb_table.articles.name
      BRIEFS_TABLE = aws_dynamodb_table.briefs.name
      JOBS_TABLE = aws_dynamodb_table.jobs.name
      AUDIO_BUCKET = aws_s3_bucket.audio_files.bucket
    }
  }

  tags = local.common_tags

  depends_on = [aws_iam_role_policy.news_lambda_policy]
}

# Internal API
resource "aws_lambda_function" "news_internal_api" {
  function_name = "${local.project_name}-news-internal-api-${var.environment}"
  role          = aws_iam_role.news_lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.news_internal_api.repository_url}:${var.image_tag}"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory

  environment {
    variables = {
      ENVIRONMENT = var.environment
      ARTICLES_TABLE = aws_dynamodb_table.articles.name
      BRIEFS_TABLE = aws_dynamodb_table.briefs.name
      JOBS_TABLE = aws_dynamodb_table.jobs.name
      OPENAI_API_KEY = var.openai_api_key
      ELEVENLABS_API_KEY = var.elevenlabs_api_key
      AUDIO_BUCKET = aws_s3_bucket.audio_files.bucket
      RSS_ENGINE_FUNCTION = aws_lambda_function.news_rss_engine.function_name
      CATEGORIZATION_ENGINE_FUNCTION = aws_lambda_function.news_categorization_engine.function_name
      RANKING_ENGINE_FUNCTION = aws_lambda_function.news_ranking_engine.function_name
      BRIEF_ENGINE_FUNCTION = aws_lambda_function.news_brief_engine.function_name
      AUDIO_ENGINE_FUNCTION = aws_lambda_function.news_audio_engine.function_name
      ORCHESTRATOR_FUNCTION = aws_lambda_function.news_orchestrator.function_name
    }
  }

  tags = local.common_tags

  depends_on = [aws_iam_role_policy.news_lambda_policy]
}

# ===============================
# EventBridge for Daily Scheduling
# ===============================

resource "aws_cloudwatch_event_rule" "daily_news_pipeline" {
  name                = "${local.project_name}-daily-news-pipeline-${var.environment}"
  description         = "Trigger daily news pipeline at 6 AM UTC"
  schedule_expression = "cron(0 6 * * ? *)"  # 6 AM UTC daily
  state               = "ENABLED"

  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "news_pipeline_target" {
  rule      = aws_cloudwatch_event_rule.daily_news_pipeline.name
  target_id = "NewsInternalAPITarget"
  arn       = aws_lambda_function.news_internal_api.arn

  input = jsonencode({
    source = "aws.events"
    detail = {
      action = "trigger_pipeline"
    }
  })
}

resource "aws_lambda_permission" "allow_eventbridge_news" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.news_internal_api.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_news_pipeline.arn
}

# ===============================
# API Gateway for Public Access
# ===============================

resource "aws_api_gateway_rest_api" "news_public_api" {
  name        = "${local.project_name}-news-public-api-${var.environment}"
  description = "Public API for Audifyy News Agency"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = local.common_tags
}

resource "aws_api_gateway_resource" "news_proxy" {
  rest_api_id = aws_api_gateway_rest_api.news_public_api.id
  parent_id   = aws_api_gateway_rest_api.news_public_api.root_resource_id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "news_proxy_method" {
  rest_api_id   = aws_api_gateway_rest_api.news_public_api.id
  resource_id   = aws_api_gateway_resource.news_proxy.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "news_lambda_integration" {
  rest_api_id = aws_api_gateway_rest_api.news_public_api.id
  resource_id = aws_api_gateway_resource.news_proxy.id
  http_method = aws_api_gateway_method.news_proxy_method.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.news_public_api.invoke_arn
}

resource "aws_api_gateway_deployment" "news_api_deployment" {
  depends_on = [
    aws_api_gateway_integration.news_lambda_integration
  ]

  rest_api_id = aws_api_gateway_rest_api.news_public_api.id
  stage_name  = var.environment
}

resource "aws_lambda_permission" "allow_api_gateway_news" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.news_public_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.news_public_api.execution_arn}/*/*"
}